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
        id_ = thread.get_ident()

        thread_context = self._contexts.get(id_)

        if thread_context is None:
            thread_context = {'dead_slaves': {}}
            self._init_context(thread_context)
            self._contexts[id_] = thread_context

        return thread_context

    def _init_thread_context(self, thread_context):
        thread_context.update({
            'state_stack': [],
            'chosen': {},
            'state_change_enabled': True,
        })

    def init(self):
        thread_context = self._get_thread_context()
        self._init_context(thread_context)


context = Context()
