# -*- coding:utf-8 -*-
from datetime import datetime, timedelta


def _db_is_alive(db_name):
    from django.db import connections

    db = connections[db_name]
    try:
        if db.connection is not None and hasattr(db.connection, 'ping'):
            db.connection.ping()
        else:
            db.cursor()
        return True
    except StandardError:
        return False


def db_is_alive(db_name, cache_seconds=0, force=False):
    from .context import context

    cache_td = timedelta(seconds=cache_seconds)

    dead_slaves = context.get('dead_slaves', {})

    death_time = dead_slaves.get(db_name)
    if death_time:
        if death_time + cache_td > datetime.now():
            if not force:
                return False
        else:
            del dead_slaves[db_name]

    is_alive = _db_is_alive(db_name)
    if not is_alive:
        dead_slaves[db_name] = datetime.now()

    return is_alive
