# -*- coding:utf-8 -*-
from datetime import datetime, timedelta


def db_is_alive(db_name):
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


def db_is_alive_with_cache(db_name, cache_seconds=0):
    from .context import context

    cache_td = timedelta(seconds=cache_seconds)

    if hasattr(context, 'dead_slaves'):
        death_time = context.dead_slaves.get(db_name)
        if death_time:
            if death_time + cache_td > datetime.now():
                return False
            else:
                del context.dead_slaves[db_name]
    else:
        context.dead_slaves = {}

    is_alive = db_is_alive(db_name)
    if not is_alive:
        context.dead_slaves[db_name] = datetime.now()

    return is_alive
