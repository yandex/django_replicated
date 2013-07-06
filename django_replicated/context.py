# -*- coding:utf-8 -*-
import thread


class Context(object):

    def __init__(self):
        self._contexts = {}

    def __getattr__(self, name):
        thread_context = self._get_thread_context()
        try:
            return thread_context[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        thread_context = self._get_thread_context()
        thread_context[name] = value

    def _get_thread_context(self):
        return self._contexts.setdefault(thread.get_ident(), {})

context = Context()
