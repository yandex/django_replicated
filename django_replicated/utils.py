# coding: utf-8
from __future__ import unicode_literals

from django import db


def get_object_name(obj):
    try:
        return obj.__name__
    except AttributeError:
        return obj.__class__.__name__


def import_string(dotted_path):
    try:
        from django.utils.module_loading import import_string
    except ImportError:
        pass
    else:
        return import_string(dotted_path)
    # Support django1.6 too.
    # Copypaste of django1.6's django.db.utils.ConnectionRouter.__init__
    # But without most of error handling.
    from django.utils.importlib import import_module
    module_name, klass_name = dotted_path.rsplit('.', 1)
    module = import_module(module_name)
    return getattr(module, klass_name)


class DefaultDatabaseRouter(object):
    """ A simple router class that always returns the default database """
    def __init__(self):
        from django.db import DEFAULT_DB_ALIAS
        self.DEFAULT_DB_ALIAS = DEFAULT_DB_ALIAS

    def db_for_write(self, model, **hints):
        return self.DEFAULT_DB_ALIAS

    def db_for_read(self, model, **hints):
        return self.DEFAULT_DB_ALIAS


class OverridesDatabaseRouter(object):
    """
    An alternative / example router that looks for database override on a model
    attribute.
    """

    _override_attr = '_route_database'

    def __init__(self, *args, **kwargs):
        from django.db import DEFAULT_DB_ALIAS
        self.DEFAULT_DB_ALIAS = DEFAULT_DB_ALIAS

    def db_for_write(self, model, **hints):
        override = getattr(model, self._override_attr, None)
        if override:
            return override
        return self.DEFAULT_DB_ALIAS

    def db_for_read(self, model, **hints):
        return self.db_for_write(model, **hints)


class Routers(object):

    def __getattr__(self, name):
        for r in db.router.routers:
            if hasattr(r, name):
                return getattr(r, name)
        msg = 'Not found the router with the method "%s".' % name
        raise AttributeError(msg)


routers = Routers()
