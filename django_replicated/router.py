# -*- coding:utf-8 -*-
import random

from django.db.utils import DEFAULT_DB_ALIAS, load_backend
from django.conf import settings
from django.db import connections


class ReplicationRouter(object):
    def __init__(self):
        self.state_stack = ['master']
        self._state_change_enabled = True

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
        return DEFAULT_DB_ALIAS

    def db_for_read(self, model, **hints):
        if self.state() == 'master':
            return self.db_for_write(model, **hints)
        slaves = getattr(settings, 'DATABASE_SLAVES', [DEFAULT_DB_ALIAS])

        check_slaves = getattr(settings, 'DATABASE_CHECK_SLAVES', True)
        use_master = getattr(settings, 'DATABASE_USE_MASTER', False)

        if check_slaves:
            random.shuffle(slaves)
            for slave in slaves:
                connection = connections[slave]
                backend = load_backend(connection.settings_dict['ENGINE'])
                try:
                    cur = connection.cursor()
                    return slave
                except backend.DatabaseError, e:
                    continue
            else:
                if use_master:
                    return self.db_for_write(model, **hints)
                else:
                    return DEFAULT_DB_ALIAS
        else:
            return random.choice(slaves)
