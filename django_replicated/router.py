# -*- coding:utf-8 -*-
import random
from datetime import datetime

from django.conf import settings


def is_alive(db):
    try:
        if db.connection is not None and hasattr(db.connection, 'ping'):
            db.connection.ping()
        else:
            db.cursor()
        return True
    except StandardError:
        return False


class ReplicationRouter(object):

    def __init__(self):
        from django.db import connections
        from django.db.utils import DEFAULT_DB_ALIAS
        self.connections = connections
        self.DEFAULT_DB_ALIAS = DEFAULT_DB_ALIAS
        self.state_stack = ['master']
        self._state_change_enabled = True
        self.db_status = {}

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
        downtime = datetime(seconds=getattr(settings, 'DATABASE_DOWNTIME', 60))
        random.shuffle(slaves)
        for slave in slaves:
            status = self.db_status.get(slave, None)
            if status:
                real_downtime = datetime.now() - status

                if real_downtime < downtime:
                    continue

            if is_alive(self.connections[slave]):
                self.db_status[slave] = None
                return slave
            else:
                self.db_status[slave] = datetime.now()

        else:
            return self.DEFAULT_DB_ALIAS
