# coding: utf-8

from django.test import RequestFactory
from django.http import HttpResponse

from django_replicated.decorators import use_state
from django_replicated.utils import routers


def test_user_state_decorator():
    factory = RequestFactory()
    request = factory.get('/')

    def _view(request):
        return HttpResponse()

    use_state('master')(_view)(request)

    assert routers.state() == 'master'
