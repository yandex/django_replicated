# -*- coding:utf-8 -*-
from threading import local


class Context(local):

    def get(self, attr, default=None):

        if not hasattr(self, attr):
            setattr(self, attr, default)
            return default
        else:
            return getattr(self, attr)


context = Context()
