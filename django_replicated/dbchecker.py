# coding: utf-8
from __future__ import unicode_literals

import logging
import socket
from functools import partial

from django.conf import settings
from django.core.cache import DEFAULT_CACHE_ALIAS
from django.utils import timezone
from django.db import connections

try:
    from django.core.cache import get_cache
except ImportError: # Django >= 1.7
    from django.core.cache import caches

    get_cache = lambda alias: caches[alias]


from .utils import get_object_name


log = logging.getLogger(__name__)

cache = get_cache(settings.REPLICATED_CACHE_BACKEND or DEFAULT_CACHE_ALIAS)

hostname = socket.getfqdn()


def is_alive(connection):
    if connection.connection is not None and hasattr(connection.connection, 'ping'):
        log.debug('Ping db: %s', connection.alias)
        connection.connection.ping()
    else:
        log.debug('Get cursor for db: %s', connection.alias)
        connection.cursor()

    return True


def is_writable(connection):
    cursor = connection.cursor()

    if connection.vendor == 'mysql':
        cursor.execute('SELECT @@read_only')
        return not int(cursor.fetchone()[0])

    elif connection.vendor == 'oracle':
        cursor.execute('SELECT open_mode FROM v$database')
        return cursor.fetchone()[0] != 'READ ONLY'

    return True


def check_db(checker, db_name, cache_seconds=None, number_of_tries=1, force=False):
    assert number_of_tries >= 1, 'Number of tries must be >= 1.'

    connection = connections[db_name]

    checker_name = get_object_name(checker)
    cache_key = ':'.join((hostname, checker_name, db_name))
    dead_mark = 'dead'

    if not force and cache_seconds is not None:
        is_dead = cache.get(cache_key) == dead_mark

        if is_dead:
            log.debug(
                'Last check "%s" %s was less than %d ago, no check needed',
                checker_name, db_name, cache_seconds
            )

            return False
        else:
            log.debug(
                'Last check "%s" %s was more than %d ago, checking again',
                db_name, checker_name, cache_seconds
            )
    else:
        log.debug('Force check %s: %s', checker_name, db_name)

    for count in range(1, number_of_tries + 1):
        log.debug(
            'Trying to check "%s" %s: %d try',
            db_name, checker_name, count
        )

        try:
            result = checker(connection)
        except Exception:
            if count == number_of_tries:
                log.exception('Error verifying %s: %s', checker_name, db_name)

            result = False

        log.debug(
            'After %d tries "%s" %s = %s',
            count, db_name, checker_name, result
        )

    if not result and cache_seconds is not None:
        cache.set(cache_key, dead_mark, cache_seconds)

    return result


db_is_alive = partial(check_db, is_alive)
db_is_writable = partial(check_db, is_writable)
