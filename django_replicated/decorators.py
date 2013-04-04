# -*- coding:utf-8 -*-
'''
Decorators for using specific routing state for particular requests.
Used in cases when automatic switching based on request method doesn't
work.

Usage:

    from django_replicated.decorators import use_master, use_slave

    @use_master
    def my_view(request, ...):
        # master database used for all db operations during
        # execution of the view (if not explicitly overriden).

    @use_slave
    def my_view(request, ...):
        # same with slave connection
'''
import utils
from functools import wraps
from utils import routers

def _use_state(state):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            current_state = utils.check_state_override(request, state)
            routers.use_state(current_state)
            try:
                response = func(request, *args, **kwargs)
            finally:
                routers.revert()
            utils.handle_updated_redirect(request, response)
            return response
        return wrapper
    return decorator

use_master = _use_state('master')
use_slave = _use_state('slave')
