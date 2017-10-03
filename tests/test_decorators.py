# coding: utf-8

from django.test import RequestFactory
from django.http import HttpResponse

from django_replicated.decorators import use_state, use_slave_simple, use_master_simple
from django_replicated.utils import routers


def test_user_state_decorator():
    factory = RequestFactory()
    request = factory.get('/')

    def _view(request):
        return HttpResponse()

    use_state('master')(_view)(request)

    assert routers.state() == 'master'


def test_decorators():
    assert use_slave_simple_decorator() == 'slave'
    assert use_master_simple_decorator() == 'master'


def test_context_managers():
    assert use_slave_simple_context_manager() == 'slave'
    assert use_master_simple_context_manager() == 'master'


@use_slave_simple
def use_slave_simple_decorator():
    return routers.state()


@use_master_simple
def use_master_simple_decorator():
    return routers.state()


def use_slave_simple_context_manager():
    with use_slave_simple:
        return routers.state()


def use_master_simple_context_manager():
    with use_master_simple:
        return routers.state()
