# -*- coding:utf-8 -*-
import random
from datetime import datetime, timedelta

from django.conf import settings


class ReplicationRouter(object):

    def __init__(self):
        from django.db import connections
        from django.db.utils import DEFAULT_DB_ALIAS
        self.connections = connections
        self.DEFAULT_DB_ALIAS = DEFAULT_DB_ALIAS
        self.state_stack = ['master']
        self._state_change_enabled = True
        self.downtime = timedelta(seconds=getattr(settings, 'DATABASE_DOWNTIME', 60))
        self.dead_slaves = {}

    def is_alive(self, slave):
        death_time = self.dead_slaves.get(slave)
        if death_time:
            if death_time + self.downtime > datetime.now():
                return False
            else:
                del self.dead_slaves[slave]
        db = self.connections[slave]
        try:
            if db.connection is not None and hasattr(db.connection, 'ping'):
                db.connection.ping()
            else:
                db.cursor()
            return True
        except StandardError:
            self.dead_slaves[slave] = datetime.now()
            return False

    def set_state_change(self, enabled):
        self._state_change_enabled = enabled

    def state(self):
        '''
        Current state of routing: 'master' or 'slave'.
        '''
        return self.state_stack[-1]

    def use_state(self, state):
        '''
        Switches router into a new state. Requires a paired call
        to 'revert' for reverting to previous state.
        '''
        if not self._state_change_enabled:
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
        return self.DEFAULT_DB_ALIAS

    def db_for_read(self, model, **hints):
        if self.state() == 'master':
            return self.db_for_write(model, **hints)
        slaves = getattr(settings, 'DATABASE_SLAVES', [self.DEFAULT_DB_ALIAS])
        random.shuffle(slaves)
        for slave in slaves:
            if self.is_alive(slave):
                return slave
        else:
            return self.DEFAULT_DB_ALIAS
