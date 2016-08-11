# coding: utf-8
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
from __future__ import unicode_literals

from functools import wraps

from django.utils.decorators import decorator_from_middleware_with_args

from .middleware import ReplicationMiddleware
from .utils import routers

try:
    from django.utils.decorators import ContextDecorator
except ImportError:
    class ContextDecorator(object):
        """
        A base class that enables a context manager to also be used as a decorator.
        """
        def __call__(self, func):
            @wraps(func)
            def inner(*args, **kwargs):
                with self:
                    return func(*args, **kwargs)
            return inner

use_state = decorator_from_middleware_with_args(ReplicationMiddleware)
use_master = use_state('master')
use_slave = use_state('slave')


class use_state_simple(ContextDecorator):
    def __init__(self, state):
        self.state = state

    def __enter__(self):
        routers.use_state(self.state)

    def __exit__(self, exc_type, exc_val, exc_tb):
        routers.revert()


use_master_simple = use_state_simple('master')
use_slave_simple = use_state_simple('slave')
