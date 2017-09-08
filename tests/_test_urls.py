# coding: utf-8
from __future__ import unicode_literals

from django.conf.urls import url
from django.http import HttpResponseRedirect, HttpResponse
from django.views.generic import View
from django_replicated.utils import routers


def view(request):
    response = HttpResponseRedirect('/')
    response['Router-Used'] = routers.state()
    return response


def just_updated_view(request):
    return HttpResponse()


class TestView(View):
    def get(self, request):
        return HttpResponseRedirect('/')


class TestCallable(object):
    def __call__(self, request):
        return HttpResponseRedirect('/')


urlpatterns = [
    url(r'^$', view),
    url(r'^admin/auth/$', TestView.as_view()),
    url(r'^just_updated$', just_updated_view),
    url(r'^with_name$', view, name='view-name'),
    url(r'^as_class$', TestView.as_view()),
    url(r'^as_callable$', TestCallable()),
]
