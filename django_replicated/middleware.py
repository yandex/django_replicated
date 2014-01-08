# -*- coding:utf-8 -*-

from .utils import (
    check_state_override,
    handle_updated_redirect,
    is_service_read_only,
    routers,
)


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
    def process_request(self, request):
        state = 'slave' if request.method in ['GET', 'HEAD'] else 'master'
        state = check_state_override(request, state)
        routers.init(state)

    def process_response(self, request, response):
        handle_updated_redirect(request, response)
        return response


class ReadOnlyMiddleware(object):
    def process_request(self, request):
        request.service_is_readonly = is_service_read_only()
