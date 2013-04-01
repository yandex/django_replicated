# -*- coding:utf-8 -*-
import random
from datetime import datetime, timedelta
import thread

from django.conf import settings


class odict(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value


class ReplicationRouter(object):

    def __init__(self):
        from django.db import connections
        from django.db.utils import DEFAULT_DB_ALIAS

        self.connections = connections

        self.DEFAULT_DB_ALIAS = DEFAULT_DB_ALIAS
        self.DOWNTIME = timedelta(seconds=getattr(settings, 'DATABASE_DOWNTIME', 60))
        self.SLAVES = getattr(settings, 'DATABASE_SLAVES', [self.DEFAULT_DB_ALIAS])

        self._context = {}

    @property
    def context(self):
        id_ = thread.get_ident()

        if id_ not in self._context:
            self._context[id_] = odict(dead_slaves={})
            self._clear_context(self._context[id_])

        return self._context[id_]

    def _clear_context(self, context):
        context.state_stack = []
        context.chosen={}
        context.state_change_enabled = True

    def init(self, state):
        self._clear_context(self.context)
        self.use_state(state)


    def is_alive(self, db_name):
        death_time = self.context.dead_slaves.get(db_name)
        if death_time:
            if death_time + self.DOWNTIME > datetime.now():
                return False
            else:
                del self.context.dead_slaves[db_name]
        db = self.connections[db_name]
        try:
            if db.connection is not None and hasattr(db.connection, 'ping'):
                db.connection.ping()
            else:
                db.cursor()
            return True
        except StandardError:
            self.context.dead_slaves[db_name] = datetime.now()
            return False

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
        self.context.chosen['master'] = self.DEFAULT_DB_ALIAS

        return self.DEFAULT_DB_ALIAS

    def db_for_read(self, model, **hints):
        if self.state() == 'master':
            return self.db_for_write(model, **hints)

        if self.state() in self.context.chosen:
            return self.context.chosen[self.state()]

        slaves = self.SLAVES[:]
        random.shuffle(slaves)

        for slave in slaves:
            if self.is_alive(slave):
                chosen = slave
                break
        else:
            chosen = self.DEFAULT_DB_ALIAS

        self.context.chosen[self.state()] = chosen

        return chosen
