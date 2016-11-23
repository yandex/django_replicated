# coding: utf-8
from __future__ import unicode_literals

import inspect
from functools import partial

from django import db
from django.conf import settings
from django.core import urlresolvers
from django.utils import six, functional

from . import dbchecker
from .utils import routers, get_object_name


class ReplicationMiddleware(object):
    '''
    Middleware for automatically switching routing state to
    master or slave depending on request method.

    In a properly designed web applications GET and HEAD request should
    not require writing to a database (except by side effects). This
    middleware switches database wrapper to slave mode for such requests.

    One special case is handling redirect responses after POST requests
    doing writes to database. They are most commonly used to show updated
    pages to a user. However in this case slave replicas may not yet be
    updated to match master. Thus first redirect after POST is pointed to
    master connection even if it only GETs data.
    '''
    def __init__(self, forced_state=None):
        self.forced_state = forced_state

    def process_request(self, request):
        if self.forced_state is not None:
            state = self.forced_state
        elif request.META.get(settings.REPLICATED_FORCE_STATE_HEADER) in ('master', 'slave'):
            state = request.META[settings.REPLICATED_FORCE_STATE_HEADER]
        else:
            state = 'slave' if request.method in ['GET', 'HEAD'] else 'master'
            state = self.check_state_override(request, state)

        routers.init(state)

    def process_response(self, request, response):
        self.handle_redirect_after_write(request, response)
        return response

    def check_state_override(self, request, state):
        '''
        Used to check if a web request should use a master or slave
        database besides default choice.
        '''
        if request.COOKIES.get(settings.REPLICATED_FORCE_MASTER_COOKIE_NAME) == 'true':
            return 'master'

        overrides = settings.REPLICATED_VIEWS_OVERRIDES

        if overrides:
            match = urlresolvers.resolve(request.path_info)

            import_path = '%s.%s' % (get_object_name(inspect.getmodule(match.func)),
                                     get_object_name(match.func))

            for lookup_view, forced_state in six.iteritems(overrides):
                if match.url_name == lookup_view or import_path == lookup_view:
                    state = forced_state
                    break

        return state

    def handle_redirect_after_write(self, request, response):
        '''
        Sets a flag using cookies to redirect requests happening after
        successful write operations to ensure that corresponding read
        request will use master database. This avoids situation when
        replicas lagging behind on updates a little.
        '''
        force_master_codes = settings.REPLICATED_FORCE_MASTER_COOKIE_STATUS_CODES
        if response.status_code in force_master_codes and routers.state() == 'master':
            self.set_force_master_cookie(response)
        else:
            if settings.REPLICATED_FORCE_MASTER_COOKIE_NAME in request.COOKIES:
                response.delete_cookie(settings.REPLICATED_FORCE_MASTER_COOKIE_NAME)

    def set_force_master_cookie(self, response):
        '''
        Use it to explicitly use master on next request to your app.
        '''
        response.set_cookie(settings.REPLICATED_FORCE_MASTER_COOKIE_NAME, 'true',
                            max_age=settings.REPLICATED_FORCE_MASTER_COOKIE_MAX_AGE)


class ReadOnlyMiddleware(object):
    def process_request(self, request):
        request.service_is_readonly = functional.SimpleLazyObject(self.is_service_read_only)

    def is_service_read_only(self):
        do_check = partial(dbchecker.check_db,
                           db_name=db.DEFAULT_DB_ALIAS,
                           cache_seconds=settings.REPLICATED_READ_ONLY_DOWNTIME,
                           number_of_tries=settings.REPLICATED_READ_ONLY_TRIES)

        if not do_check(dbchecker.is_alive):
            return True

        return not do_check(dbchecker.is_writable)
