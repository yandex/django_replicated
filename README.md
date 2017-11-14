## SUMMARY

Django_replicated is a Django [database router][1] designed to support more or
less automatic master-slave replication. It keeps an internal state that
depends on user intent to read or to write into a database. Depending on this
state it automatically uses the right database (master or slave) for all
SQL operations.

[1]: http://docs.djangoproject.com/en/dev/topics/db/multi-db/#topics-db-multi-db-routing


## INSTALLATION

1.  Install django_replicated distribution using "python setup.py install".

1.  Add import of the default django_replicated settings into your `settings.py`:

        from django_replicated.settings import *

1.  In settings.py configure your master and slave databases in a standard way:

        DATABASES {
            'default': {
                # ENGINE, HOST, etc.
            },
            'slave1': {
                # ENGINE, HOST, etc.
            },
            'slave2': {
                # ENGINE, HOST, etc.
            },
        }

1.  Teach django_replicated which databases are slaves:

        REPLICATED_DATABASE_SLAVES = ['slave1', 'slave2']

    The 'default' database is always treated as master.

1.  Configure a replication router:

        DATABASE_ROUTERS = ['django_replicated.router.ReplicationRouter']

1.  Configure timeout to exclude a database from the available list after an
    unsuccessful ping:

        REPLICATED_DATABASE_DOWNTIME = 20

    The default downtime value is 60 seconds.


## USAGE

Django_replicated routes SQL queries into different databases based not only on
their type (insert/update/delete vs. select) but also on its own current state.
This is done to support the situation in which there are both writes and reads
in a single logical operation. If the writes and reads used separate databases,
the result would be inconsistent because:

- when using transactions, the result of the writes will not be delivered to
  slaves until committed;
- even in a non-transactional environment, there is always a certain lag before
  the updates reach slaves.

Django_replicated expects you to define what these logical operations are
doing: writing/reading or only reading. Then it will try to use slave databases
only for purely reading operations.

There are several methods to define those.


### Middleware

If your project is built in accordance with principles of HTTP where GET requests
do not cause changes in the system (unless by side effects) then most of the
work is done by simply using a middleware:

    MIDDLEWARE_CLASSES = [
        ...
        'django_replicated.middleware.ReplicationMiddleware',
        ...
    ]

The middleware sets replication state to use slaves during handling of GET and
HEAD requests and to use a master otherwise.

While this is usually enough there are cases when DB access is not controlled
explicitly by your business logic. Good examples are implicit creation of
sessions on the first access, writing some bookkeeping info, implicit registration
of a user account somewhere inside the system. These things can happen at
arbitrary moments of time, including during GET requests.

Generally, django_replicated handles this by always using the master database
for write operations. If this is not enough (e.g., if you want to make sure a
newly created session is read from the master), you can always instruct
Django ORM to [use a certain database][2].

[2]: http://docs.djangoproject.com/en/dev/topics/db/multi-db/#manually-selecting-a-database


### Decorators

If your system does not depend on the method of HTTP request to do writes and
reads you can use decorators to wrap individual views into master or slave
replication modes:

    from django_replicated.decorators import use_master, use_slave

    @use_master
    def my_view(request, ...):
        # master database used for all db operations during
        # execution of the view (if not explicitly overridden).

    @use_slave
    def my_view(request, ...):
        # same with slave connection


### GET after POST

There is a special case that needs addressing when working with asynchronous
replication scheme. Replicas can lag behind a master database on receiving
updates. In practice, this means that after submitting a POST form that redirects
to a page with updated data this page may be requested from a slave replica
that was not updated yet. And the user will have an impression that the submit
did not work.

To overcome this problem both `ReplicationMiddleware` and decorators support
special technique where handling of a GET request resulting from a redirect
after a POST is explicitly routed to a master database.


### Global overrides

In some cases, it might be necessary to override how the middleware chooses
a target database based on the HTTP request method. For example, you might want to
route certain POST requests to a slave if you know that the request handler
does not do any writes. The settings variable `REPLICATED_VIEWS_OVERRIDES` holds
the mapping of view names (urlpatterns names) or view import paths or url path 
to database names:

    REPLICATED_VIEWS_OVERRIDES = {
        'api-store-event': 'slave',
        'app.views.do_smthg': 'master',
        '/admin/*': 'master',
        '/users/': 'slave',
    }


## CHANGELOG

### 2.0 Backward incompatible changes
* Default `django_replicated.settings` file was added.
* Some settings variables were renamed:

        DATABASE_SLAVES -> REPLICATED_DATABASE_SLAVES
        DATABASE_DOWNTIME -> REPLICATED_DATABASE_DOWNTIME
* Another setting variable was deleted:

        REPLICATED_SELECT_READ_ONLY
* Router import path changed to `django_replicated.router.ReplicationRouter`.
* Ability to disable state switching with `utils.disable_state_change()` was removed.
* Database checkers moved to `dbchecker.py` module.
* `db_is_not_read_only` check renamed to `db_is_writable`.
* Added state checking before writes. Enabled by default.
* Now allows relations between objects in same master-slave db set


## SIMILAR LIBRARIES

* [django-multidb-router](https://github.com/jbalogh/django-multidb-router)
