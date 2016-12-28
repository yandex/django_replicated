# coding: utf-8
from __future__ import unicode_literals

import random
from threading import local


class ReplicationRouter(object):

    def __init__(self):
        from django.db import DEFAULT_DB_ALIAS
        from django.conf import settings

        self._context = local()

        self.DEFAULT_DB_ALIAS = DEFAULT_DB_ALIAS
        self.DOWNTIME = settings.REPLICATED_DATABASE_DOWNTIME
        self.MASTERS = settings.REPLICATED_DATABASE_MASTERS or [DEFAULT_DB_ALIAS]
        self.SLAVES = settings.REPLICATED_DATABASE_SLAVES or [DEFAULT_DB_ALIAS]
        self.CHECK_STATE_ON_WRITE = settings.REPLICATED_CHECK_STATE_ON_WRITE

        self.all_allowed_aliases = self.MASTERS + self.SLAVES

    def _init_context(self):
        self._context.state_stack = []
        self._context.chosen = {}
        self._context.state_change_enabled = True
        self._context.inited = True

    def _get_actual_master(self):
        try:
            chosen = self._context.actual_master
            if not self.is_alive(chosen):
                raise RuntimeError()
        except (AttributeError, RuntimeError):
            # Be predictable here. No shuffle for master
            for db in self.MASTERS:
                if self.is_alive(db):
                    chosen = db
                    break
            else:
                chosen = self.DEFAULT_DB_ALIAS

            self.context.actual_master = chosen
        return chosen

    @property
    def context(self):
        if not getattr(self._context, 'inited', False):
            self._init_context()
        return self._context

    def init(self, state):
        self._init_context()
        self.use_state(state)

    def is_alive(self, db_name):
        from .dbchecker import db_is_alive

        return db_is_alive(db_name, self.DOWNTIME)

    def set_state_change(self, enabled):
        self.context.state_change_enabled = enabled

    def state(self):
        '''
        Current state of routing: 'master' or 'slave'.
        '''
        if self.context.state_stack:
            return self.context.state_stack[-1]
        else:
            return 'master'

    def use_state(self, state):
        '''
        Switches router into a new state. Requires a paired call
        to 'revert' for reverting to previous state.
        '''
        if not self.context.state_change_enabled:
            state = self.state()
        self.context.state_stack.append(state)
        return self

    def revert(self):
        '''
        Reverts wrapper state to a previous value after calling
        'use_state'.
        '''
        self.context.state_stack.pop()

    def db_for_write(self, model, **hints):
        if self.CHECK_STATE_ON_WRITE and self.state() != 'master':
            raise RuntimeError('Trying to access master database in slave state')

        actual_master = self._get_actual_master()
        self.context.chosen['master'] = actual_master

        return actual_master

    def db_for_read(self, model, **hints):
        if self.state() == 'master':
            return self.db_for_write(model, **hints)

        if self.state() in self.context.chosen:
            return self.context.chosen[self.state()]

        slaves = self.SLAVES[:]
        random.shuffle(slaves)
        masters = self.MASTERS[:]
        random.shuffle(masters)

        # Try masters if slaves cannot be used
        for db in slaves + masters:
            if self.is_alive(db):
                chosen = db
                break
        else:
            chosen = self.DEFAULT_DB_ALIAS

        self.context.chosen[self.state()] = chosen

        return chosen

    def allow_relation(self, obj1, obj2, **hints):
        for db in (obj1._state.db, obj2._state.db):
            if db is not None and db not in self.all_allowed_aliases:
                return False

        return True
