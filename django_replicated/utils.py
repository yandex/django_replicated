# coding: utf-8
from __future__ import unicode_literals

from django import db


def get_object_name(obj):
    try:
        return obj.__name__
    except AttributeError:
        return obj.__class__.__name__


class Routers(object):
    def __getattr__(self, name):
        for r in db.router.routers:
            if hasattr(r, name):
                return getattr(r, name)
        msg = 'Not found the router with the method "%s".' % name
        raise AttributeError(msg)


routers = Routers()


class SettingsProxy(object):
    def __init__(self):
        from django.conf import settings as django_settings
        from . import settings as default_settings

        self.django_settings = django_settings
        self.default_settings = default_settings

    def __getattr__(self, k):
        try:
            return getattr(self.django_settings, k)
        except AttributeError:
            return getattr(self.default_settings, k)
