from __future__ import absolute_import

# Database-related exceptions.
from django.db.utils import DatabaseError

DATABASE_ERRORS = (DatabaseError, )

try:
    import MySQLdb as mysql
    DATABASE_ERRORS += (mysql.DatabaseError, )
except ImportError:
    pass    # noqa

try:
    import psycopg2 as pg
    DATABASE_ERRORS += (pg.DatabaseError, )
except ImportError:
    pass      # noqa

try:
    import sqlite3
    DATABASE_ERRORS += (sqlite3.DatabaseError, )
except ImportError:
    pass    # noqa

try:
    import cx_Oracle as oracle
    DATABASE_ERRORS += (oracle.DatabaseError, )
except ImportError:
    pass  # noqa

