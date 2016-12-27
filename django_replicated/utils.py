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


class SettingsContainer(object):
    def __init__(self):
        from django.conf import settings as django_settings
        from . import settings as default_settings

        default_settings_names = dir(default_settings)
        django_settings_names = dir(django_settings)

        for k in default_settings_names:
            if k in django_settings_names:
                new_value = getattr(django_settings, k)
            else:
                new_value = getattr(default_settings, k)
            setattr(self, k, new_value)
