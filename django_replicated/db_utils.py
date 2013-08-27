# -*- coding:utf-8 -*-

import logging
import socket
from datetime import datetime, timedelta
from django.conf import settings
from django.db import connections
from django.core.cache import get_cache, DEFAULT_CACHE_ALIAS


logger = logging.getLogger('replicated.db_checker')

cache = get_cache(
    getattr(settings, 'REPLICATED_CACHE_BACKEND', DEFAULT_CACHE_ALIAS)
)
cache_key = 'dead_databases_' + socket.gethostname()


def _db_is_alive(db_name):

    db = connections[db_name]
    try:
        if db.connection is not None and hasattr(db.connection, 'ping'):
            logger.debug(u'Ping db %s.', db_name)
            db.connection.ping()
        else:
            logger.debug(u'Get cursor for db %s.', db_name)
            db.cursor()
        return True
    except StandardError:
        logger.exception(u'Error verifying db %s.', db_name)
        return False


def db_is_alive(db_name, cache_seconds=0, number_of_tries=1, force=False):
    assert number_of_tries >= 1, u'Number of tries must be >= 1. RTFM.'

    cache_td = timedelta(seconds=cache_seconds)

    dead_databases = cache.get(cache_key, {})

    death_time = dead_databases.get(db_name)
    if death_time:
        if death_time + cache_td > datetime.now():
            msg = u'Last check db %s was less than %d ago, no check needed.'
            logger.debug(msg, db_name, cache_seconds)
            if not force:
                return False
            logger.debug(u'Force check db %s.', db_name)

        else:
            del dead_databases[db_name]
            msg = u'Last check db %s was more than %d ago, checking again.'
            logger.debug(msg, db_name, cache_seconds)
    else:
        logger.debug(u'is_alive cache for db %s is empty.', db_name)

    for count in range(1, number_of_tries + 1):
        is_alive = _db_is_alive(db_name)
        logger.debug(u'Trying to check db %s: %d try.', db_name, count)
        if is_alive:
            msg = u'Successfully connected to db %s in %d tries.'
            logger.debug(msg, db_name, count)
            break

    if not is_alive:
        msg = u'Error connecting to db %s in %d tries.'
        logger.error(msg, db_name, number_of_tries)
        dead_databases[db_name] = datetime.now()

    cache.set(cache_key, dead_databases)

    return is_alive
