# -*- coding:utf-8 -*-
import random

from django.conf import settings
from django.db.utils import DEFAULT_DB_ALIAS

from .db_utils import db_is_alive


class ReplicationRouter(object):

    def __init__(self):
        from .context import context
        self.context = context
        self.DEFAULT_DB_ALIAS = DEFAULT_DB_ALIAS
        self.DOWNTIME = getattr(settings, 'DATABASE_DOWNTIME', 60)
        self.SLAVES = getattr(settings, 'DATABASE_SLAVES', [DEFAULT_DB_ALIAS])

    def state_stack():
        def fget(self):
            return self.context.get('state_stack', [])

        def fset(self, value):
            self.context.state_stack = value
        return locals()
    state_stack = property(**state_stack())

    def chosen():
        def fget(self):
            return self.context.get('chosen', {})

        def fset(self, value):
            self.context.chosen = value
        return locals()
    chosen = property(**chosen())

    def state_change_enabled():
        def fget(self):
            return self.context.get('state_change_enabled', True)

        def fset(self, value):
            self.context.state_change_enabled = value
        return locals()
    state_change_enabled = property(**state_change_enabled())

    def init(self, state):
        self.state_stack = []
        self.chosen = {}
        self.state_change_enabled = True

        self.use_state(state)

    def is_alive(self, db_name):
        return db_is_alive(db_name, self.DOWNTIME)

    def set_state_change(self, enabled):
        self.state_change_enabled = enabled

    def state(self):
        '''
        Current state of routing: 'master' or 'slave'.
        '''
        if self.state_stack:
            return self.state_stack[-1]
        else:
            return 'master'

    def use_state(self, state):
        '''
        Switches router into a new state. Requires a paired call
        to 'revert' for reverting to previous state.
        '''
        if not self.state_change_enabled:
            state = self.state()
        self.state_stack.append(state)
        return self

    def revert(self):
        '''
        Reverts wrapper state to a previous value after calling
        'use_state'.
        '''
        self.state_stack.pop()

    def db_for_write(self, model, **hints):
        self.chosen['master'] = self.DEFAULT_DB_ALIAS

        return self.DEFAULT_DB_ALIAS

    def db_for_read(self, model, **hints):
        if self.state() == 'master':
            return self.db_for_write(model, **hints)

        if self.state() in self.chosen:
            return self.chosen[self.state()]

        slaves = self.SLAVES[:]
        random.shuffle(slaves)

        for slave in slaves:
            if self.is_alive(slave):
                chosen = slave
                break
        else:
            chosen = self.DEFAULT_DB_ALIAS

        self.chosen[self.state()] = chosen

        return chosen
