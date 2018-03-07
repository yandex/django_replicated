# coding: utf-8
from __future__ import unicode_literals

from django.conf.urls import url
from django.http import HttpResponseRedirect, HttpResponse
from django.views.generic import View
from django_replicated.utils import routers
from django.db import transaction


def view(request):
    response = HttpResponseRedirect('/')
    response['Router-Used'] = routers.state()
    response['DB-Used'] = routers.db_for_read()
    return response


def just_updated_view(request):
    return HttpResponse()


class TestView(View):
    def get(self, request):
        return view(request)


class TestCallable(object):
    def __call__(self, request):
        return view(request)


class TestInstanceMethod(object):
    def instancemethodview(self, request):
        return view(request)


instance_view = TestInstanceMethod()


@transaction.non_atomic_requests
def non_atomic_view(request):
    response = HttpResponse()
    response['DB-Used'] = routers.db_for_read()
    return response


urlpatterns = [
    url(r'^$', view),
    url(r'^admin/auth/$', TestView.as_view()),
    url(r'^just_updated$', just_updated_view),
    url(r'^with_name$', view, name='view-name'),
    url(r'^as_class$', TestView.as_view()),
    url(r'^as_callable$', TestCallable()),
    url(r'^as_instancemethod$', instance_view.instancemethodview),
    url(r'^non_atomic_view$', non_atomic_view),
]
