from django import db
from django.conf import settings
from django.core import urlresolvers


def _get_func_import_path(func):
    '''
    Taken from django.core.urlsolvers
    '''
    if not hasattr(func, '__name__'):
        # An instance of a callable class
        return '.'.join([func.__class__.__module__, func.__class__.__name__])
    else:
        # A function
        return '.'.join([func.__module__, func.__name__])


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
    if response.status_code in [302, 303] and _state() == 'master':
        response.set_cookie('just_updated', 'true', max_age=5)
    else:
        if 'just_updated' in request.COOKIES:
            response.delete_cookie('just_updated')


# Internal helper function used to access a ReplicationRouter instance(s)
# that Django creates inside its db module.

def _apply(name, *args, **kwargs):
    for r in db.router.routers:
        if hasattr(r, name):
            return getattr(r, name)(*args, **kwargs)

_use_state = lambda state: _apply('use_state', state)
_revert = lambda: _apply('revert')
_state = lambda: _apply('state')

enable_state_change = lambda: _apply('set_state_change', True)
disable_state_change = lambda: _apply('set_state_change', False)
