# encoding: utf-8
import time

from django_replicated import FailoverReplicationRouter as Router
from django_replicated.failover_router import FailoverThread

import logging
logging.basicConfig(level=logging.DEBUG)

def test_thread_cycle():
    """
    Check slave selection
    """

    from django.conf import settings

    settings.DATABASE_SLAVES = ['slave1', 'slave2']

    r = Router(run_thread=False)
    assert len(r.SLAVES) == 2

    t = r.get_thread(check_master=False)

    # Only slave1 is alive:

    t.db_is_alive = lambda alias: alias == 'slave1'
    t.check()

    assert r.SLAVES == ['slave1']
    assert r.deactivated_slaves == ['slave2']
    assert r.master == r.DEFAULT_DB_ALIAS

    assert r.db_for_write('a') == r.DEFAULT_DB_ALIAS
    r.use_state('slave')
    assert r.db_for_read('a') == 'slave1'
    r.revert()

    # Now only slave2 is alive:

    t.db_is_alive = lambda alias: alias == 'slave2'
    t.check()
    assert r.SLAVES == ['slave2']
    assert r.deactivated_slaves == ['slave1']
    assert r.master == r.DEFAULT_DB_ALIAS
    assert r.db_for_write('a') == r.DEFAULT_DB_ALIAS
    r.use_state('slave')
    assert r.db_for_read('a') == 'slave2'
    r.revert()

    # Now only slaves are alive:
    t.db_is_alive = lambda alias: True
    t.check()
    assert sorted(r.SLAVES) == ['slave1', 'slave2']
    assert r.master == r.DEFAULT_DB_ALIAS
    assert r.db_for_write('a') == r.DEFAULT_DB_ALIAS
    r.use_state('slave')
    assert r.db_for_read('a') in ['slave1', 'slave2']
    r.revert()


def test_thread_cycle_with_master_check():
    """
    Check master alive check
    """

    from django.conf import settings

    settings.DATABASE_SLAVES = ['slave1', 'slave2']

    r = Router(run_thread=False)
    assert len(r.SLAVES) == 2

    t = FailoverThread(router=r, check_master=True)
    t.db_is_alive = lambda alias: alias == 'slave1'

    t.check()
    assert r.master is None
    assert r.SLAVES == ['slave1']
    assert r.db_for_write('a') is None
    r.use_state('slave')
    assert r.db_for_read('a') == 'slave1'
    r.revert()

    t.db_is_alive = lambda alias: alias == 'slave2'
    t.check()
    assert r.master is None
    assert r.SLAVES == ['slave2']
    r.use_state('slave')
    assert r.db_for_read('a') == 'slave2'
    r.revert()
    assert r.db_for_write('a') is None

    t.db_is_alive = lambda alias: alias == r.DEFAULT_DB_ALIAS
    t.check()
    assert r.master == r.DEFAULT_DB_ALIAS
    assert r.SLAVES == []
    r.use_state('slave')
    assert r.db_for_read('a') == r.DEFAULT_DB_ALIAS
    r.revert()
    assert r.db_for_write('a') == r.DEFAULT_DB_ALIAS


def test_thread_run():
    """
    Check thread starts and exit
    """
    from django.conf import settings

    settings.DATABASE_ASYNC_CHECK = True
    settings.DATABASE_CHECK_MASTER = True
    settings.DATABASE_ASYNC_CHECK_INTERVAL = 0.1
    settings.DATABASE_SLAVES = ['slave1', 'slave2']

    class TestCheckThread(FailoverThread):
        def db_is_alive(self, alias, **kwargs):
            return alias == 'slave1'

    class TestRouter(Router):
        checker_cls = TestCheckThread

    r = TestRouter()
    time.sleep(r.thread.check_interval * 3)
    assert r.SLAVES == ['slave1']
    assert r.deactivated_slaves == ['slave2']
    assert r.master is None

    r.stop_thread()
