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

from django.utils.decorators import decorator_from_middleware_with_args

from .middleware import ReplicationMiddleware


use_state = decorator_from_middleware_with_args(ReplicationMiddleware)
use_master = use_state('master')
use_slave = use_state('slave')
