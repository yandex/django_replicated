# -*- coding:utf-8 -*-
import time
import logging
import random
from threading import Thread, RLock, Event

from django.conf import settings

from .router import ReplicationRouter
from .db_utils import db_is_alive


logger = logging.getLogger('replicated.failover_router')


class FailoverThread(Thread):
    def __init__(self, router, check_interval=None, check_master=False):
        self.router = router
        self.check_interval = check_interval
        self.do_check_master = check_master
        self._stop = Event()
        Thread.__init__(self)

    def join(self, timeout=None):
        self._stop.set()
        Thread.join(self, timeout=timeout)

    def run(self):
        while not self._stop.isSet():
            self.check()
            time.sleep(self.check_interval)

    def check(self):
        self.check_slaves()
        if self.do_check_master:
            self.check_master()

    def check_slaves(self):
        """
        Check if slaves alive.
        Deactivate dead slaves.
        Activate previously deactivated slaves.
        """
        just_dectivated = []

        for alias in self.router.SLAVES:
            logger.debug('[thread] Check database %s still alive', alias)
            if not self.db_is_alive(alias):
                just_dectivated.append(alias)
                self.router.deactivate_slave(alias)

        for alias in self.router.deactivated_slaves:
            if alias not in just_dectivated:
                logger.debug('[thread] Check database %s alive again', alias)
                if self.db_is_alive(alias):
                    self.router.activate_slave(alias)

    def check_master(self):
        """
        Check master and deactivate it.
        Deactivated master is a process time economy.
        """

        alias = self.router.DEFAULT_DB_ALIAS
        r = self.router
        if r.master:
            logger.debug('[thread] Check master %s still alive', alias)
            if not self.db_is_alive(alias):
                r.deactivate_master()
        else:
            logger.debug('[thread] Check master %s alive again', alias)
            if self.db_is_alive(alias):
                r.activate_master()

    def db_is_alive(self, alias, **kwargs):
        return db_is_alive(alias, **kwargs)


class FailoverReplicationRouter(ReplicationRouter):
    """
    ReplicationRouter by itself already checks database connection.
    But on some network failures check may take a long time to finish.

    FailoverReplicationRouter's approach is to check connections
    in a separate thread and deactivate non-available slaves.

    It reads django settings:

    DATABASE_ASYNC_CHECK bool
    When False, do not run thread.
    Default is True

    DATABASE_ASYNC_CHECK_INTERVAL int
    Seconds to sleep before next check.
    Default is 5

    DATABASE_CHECK_MASTER bool
    Experimental feature.
    If True, thread checks master (default) database connection.
    When master database connections is dead, db_for_write returns None.
    Default is False
    """

    checker_cls = FailoverThread

    def __init__(self, run_thread=None, checker_cls=None):
        super(FailoverReplicationRouter, self).__init__()
        self._master = self.DEFAULT_DB_ALIAS
        self.deactivated_slaves = []
        self.rlock = RLock()
        self.thread = None
        self.checker_cls = checker_cls or self.checker_cls

        if run_thread is None:
            run_thread = getattr(settings, 'DATABASE_ASYNC_CHECK', True)

        if run_thread:
            self.thread = self.get_thread()
            self.thread and self.thread.start()

    def get_thread(self, force=False, check_master=None):
        if check_master is None:
            check_master = getattr(settings, 'DATABASE_CHECK_MASTER', False)
        if force or self.SLAVES or check_master:
            return self.checker_cls(router=self,
                                    check_interval=getattr(settings, 'DATABASE_ASYNC_CHECK_INTERVAL', 5),
                                    check_master=check_master)

    def stop_thread(self):
        if self.thread:
            logger.debug("stopping checker thread")
            self.thread.join(timeout=self.thread.check_interval * 2)
            logger.debug("checker thread stopped")
            self.thread = None

    @property
    def master(self):
        return self._master

    @master.setter
    def master(self, alias):
        self._master = alias

    def deactivate_slave(self, alias):
        with self.rlock:
            if alias not in self.deactivated_slaves:
                self.deactivated_slaves.append(alias)
            if alias in self.SLAVES:
                logger.info("Deactivate slave '%s'", alias)
                self.SLAVES.remove(alias)

    def activate_slave(self, alias):
        with self.rlock:
            if alias not in self.SLAVES:
                logger.info("Activate slave '%s'", alias)
                self.SLAVES.append(alias)
            if alias in self.deactivated_slaves:
                self.deactivated_slaves.remove(alias)

    def deactivate_master(self):
        with self.rlock:
            m = self.master
            if m:
                logger.info("Deactivate master '%s'", m)
                self.master = None

    def activate_master(self):
        with self.rlock:
            if not self.master:
                logger.info("Activate master '%s'", self.DEFAULT_DB_ALIAS)
                self.master = self.DEFAULT_DB_ALIAS

    def db_for_write(self, *a, **kw):
        master = self.master
        self.context.chosen['master'] = master
        return master

    def db_for_read(self, model, **hints):
        if self.state() == 'master':
            return self.db_for_write(model, **hints)

        if self.state() in self.context.chosen:
            r = self.context.chosen[self.state()]
            if r in self.SLAVES:
                return r

        if self.SLAVES:
            chosen = random.choice(self.SLAVES)
        else:
            chosen = self.master

        self.context.chosen[self.state()] = chosen
        return chosen

    def __del__(self):
        self.stop_thread()
