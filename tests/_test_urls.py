# coding: utf-8
from __future__ import unicode_literals

from django.conf.urls import url, include
from django.http import HttpResponseRedirect, HttpResponse
from django.views.generic import View
from django_replicated.utils import routers
from django.db import transaction


def set_non_atomic_attributes(response, view):
    response['Default-Non-Atomic'] = ','.join(sorted(getattr(view, '_replicated_view_default_non_atomic_dbs', [])))
    response['Non-Atomic'] = ','.join(sorted(getattr(view, '_non_atomic_requests', [])))


def get_response():
    response = HttpResponseRedirect('/')
    response['Router-Used'] = routers.state()
    response['DB-Used'] = routers.db_for_read()
    return response


def view(request):
    response = get_response()
    set_non_atomic_attributes(response, view)
    return response


def just_updated_view(request):
    return HttpResponse()


class TestView(View):
    def get(self, request):
        response = get_response()
        return response


class TestCallable(object):
    def __call__(self, request):
        response = get_response()
        set_non_atomic_attributes(response, self)
        return response


class TestInstanceMethod(object):
    def instancemethodview(self, request):
        response = get_response()
        set_non_atomic_attributes(response, self.instancemethodview)
        return response


instance_view = TestInstanceMethod()


@transaction.non_atomic_requests
def non_atomic_view(request):
    response = HttpResponse()
    response['DB-Used'] = routers.db_for_read()
    return response


included_patterns = [
    url(r'^with-namespace$', view, name='with-namespace'),
]

urlpatterns = [
    url(r'^$', view),
    url(r'^admin/auth/$', TestView.as_view()),
    url(r'^just_updated$', just_updated_view),
    url(r'^with_name$', view, name='view-name'),
    url(r'^as_class$', TestView.as_view()),
    url(r'^as_callable$', TestCallable()),
    url(r'^as_instancemethod$', instance_view.instancemethodview),
    url(r'^non_atomic_view$', non_atomic_view),
    url(r'^namespace/', include(included_patterns, 'namespace')),
]

