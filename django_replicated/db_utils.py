# -*- coding:utf-8 -*-
import logging
import socket
from datetime import datetime, timedelta
from functools import partial

from django.conf import settings
from django.core.cache import get_cache, DEFAULT_CACHE_ALIAS


logger = logging.getLogger('replicated.db_checker')

cache = get_cache(
    getattr(settings, 'REPLICATED_CACHE_BACKEND', DEFAULT_CACHE_ALIAS)
)
host_name = socket.gethostname()


def _db_is_alive(db_name):
    from django.db import connections

    db = connections[db_name]
    try:
        if db.connection is not None and hasattr(db.connection, 'ping'):
            logger.debug(u'Ping db %s.', db_name)
            db.connection.ping()
        else:
            logger.debug(u'Get cursor for db %s.', db_name)
            db.cursor()
        return True
    except Exception:
        logger.exception(u'Error verifying db %s.', db_name)
        return False


def _db_is_not_read_only(db_name):
    from django.db import connections

    db_engine = settings.DATABASES[db_name]['ENGINE']
    if '.' in db_engine:
        db_engine = db_engine.rsplit('.', 1)[1]

    try:
        cursor = connections[db_name].cursor()

        if db_engine == 'mysql':
            cursor.execute('SELECT @@read_only')
            return not int(cursor.fetchone()[0])

        elif db_engine == 'oracle':
            cursor.execute('SELECT open_mode FROM v$database')
            return cursor.fetchone()[0] != 'READ ONLY'

    except Exception:
        logger.exception(u'Error verifying db %s.', db_name)
        return False


def check_db(
    checker, db_name, cache_seconds=0, number_of_tries=1, force=False
):
    assert number_of_tries >= 1, u'Number of tries must be >= 1.'

    cache_td = timedelta(seconds=cache_seconds)

    checker_name = checker.__name__
    cache_key = host_name + checker_name

    check_cache = cache.get(cache_key, {})

    death_time = check_cache.get(db_name)
    if death_time:
        if death_time + cache_td > datetime.now():
            logger.debug(
                u'Last check "%s" %s was less than %d ago, no check needed.',
                checker_name, db_name, cache_seconds
            )
            if not force:
                return False
            logger.debug(u'Force check "%s" %s.', db_name, checker_name)

        else:
            del check_cache[db_name]
            logger.debug(
                u'Last check "%s" %s was more than %d ago, checking again.',
                db_name, checker_name, cache_seconds
            )
    else:
        logger.debug(
            u'%s cache for "%s" is empty.',
            checker_name, db_name
        )

    for count in range(1, number_of_tries + 1):
        result = checker(db_name)
        logger.debug(
            u'Trying to check "%s" %s: %d try.',
            db_name, checker_name, count
        )
        if result:
            logger.debug(
                u'After %d tries "%s" %s = True',
                count, db_name, checker_name
            )
            break

    if not result:
        msg = u'After %d tries "%s" %s = False.'
        logger.warning(msg, number_of_tries, db_name, checker_name)
        check_cache[db_name] = datetime.now()

    cache.set(cache_key, check_cache)

    return result


db_is_alive = partial(check_db, _db_is_alive)
db_is_not_read_only = partial(check_db, _db_is_not_read_only)
