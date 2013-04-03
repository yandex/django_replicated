from django import db
from django.conf import settings
from django.core import urlresolvers
from functools import partial
import warnings


def _get_func_import_path(func):
    '''
    Returns import path of a class method or a module-level funtion.
    '''
    base = func.__class__ if hasattr(func, '__class__') else func
    return '%s.%s' % (base.__module__, base.__name__)


def check_state_override(request, state):
    '''
    Used to check if a web request should use a master or slave
    database besides default choice.
    '''
    if request.COOKIES.get('just_updated') == 'true':
        return 'master'

    overrides = getattr(settings, 'REPLICATED_VIEWS_OVERRIDES', [])

    if overrides:
        match = urlresolvers.resolve(request.path_info)
        import_path = _get_func_import_path(match.func)

        for lookup_view, forced_state in overrides.iteritems():
            if match.url_name == lookup_view or import_path == lookup_view:
                state = forced_state
                break

    return state


def handle_updated_redirect(request, response):
    '''
    Sets a flag using cookies to redirect requests happening after
    successful write operations to ensure that corresponding read
    request will use master database. This avoids situation when
    replicas lagging behind on updates a little.
    '''
    if response.status_code in [302, 303] and routers.state() == 'master':
        response.set_cookie('just_updated', 'true', max_age=5)
    else:
        if 'just_updated' in request.COOKIES:
            response.delete_cookie('just_updated')


# Internal helper function used to access a ReplicationRouter instance(s)
# that Django creates inside its db module.

class Routers(object):
    def __getattr__(self, name):
        for r in db.router.routers:
            if hasattr(r, name):
                return getattr(r, name)
            msg = u'Not found the router with the method "%s".' % name
            raise AttributeError(msg)

routers = Routers()

enable_state_change = partial(routers.set_state_change, True)
disable_state_change = partial(routers.set_state_change, False)


def _use_state(*args, **kwargs):
    warnings.warn('You use a private method _use_state and he is outdated',
                    DeprecationWarning)
