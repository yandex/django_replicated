# coding: utf-8
from __future__ import unicode_literals

import logging
import socket
from functools import partial

import django
from django.conf import settings
from django.core.cache import DEFAULT_CACHE_ALIAS
from django.db import connections

if django.VERSION < (1, 7):
    # https://docs.djangoproject.com/en/1.7/topics/cache/#django.core.cache.get_cache
    from django.core.cache import get_cache
else:
    from django.core.cache import caches
    def get_cache(alias): return caches[alias]


from .utils import get_object_name


log = logging.getLogger(__name__)

cache = get_cache(settings.REPLICATED_CACHE_BACKEND or DEFAULT_CACHE_ALIAS)

hostname = socket.getfqdn()


def is_alive(connection):
    if connection.connection is not None and hasattr(connection.connection, 'ping'):
        log.debug('Ping db: %s', connection.alias)
        try:
            # Since MySQL-python 1.2.2 connection.ping()
            # takes an optional boolean argument to enable automatic reconnection.
            # https://github.com/farcepest/MySQLdb1/blob/d34fac681487541e4be07e6978e0db233faf8252/HISTORY#L103
            connection.connection.ping(True)
        except TypeError:
            connection.connection.ping()
    else:
        log.debug('Get cursor for db: %s', connection.alias)
        with connection.cursor():
            pass

    return True


def is_writable(connection):
    result = True
    with connection.cursor():
        if connection.vendor == 'mysql':
            cursor.execute('SELECT @@read_only')
            result = not int(cursor.fetchone()[0])

        elif connection.vendor in ('postgresql', 'postgresql_psycopg2', 'postgis'):
            cursor.execute('SELECT pg_is_in_recovery()')
            result = not cursor.fetchone()[0]

        elif connection.vendor == 'oracle':
            cursor.execute('SELECT open_mode FROM v$database')
            result = cursor.fetchone()[0] != 'READ ONLY'

    return result


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
                'Check "%s" %s was failed less than %d ago, no check needed',
                checker_name, db_name, cache_seconds
            )

            return False
        else:
            log.debug(
                'Last check "%s" %s succeeded or was more than %d ago, checking again',
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

        if result:
            break

    if not result and cache_seconds is not None:
        cache.set(cache_key, dead_mark, cache_seconds)

    return result


db_is_alive = partial(check_db, is_alive)
db_is_writable = partial(check_db, is_writable)
