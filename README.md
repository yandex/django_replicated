## SUMMARY

Django_replicated is a Django [database router][1] designed to support more or
less automatic master-slave replication. It keeps an internal state that
depends on user intent to read or to write into a database. Depending on this
state it automatically uses the right database (master or slave) for all
SQL operations.

[1]: http://docs.djangoproject.com/en/dev/topics/db/multi-db/#topics-db-multi-db-routing


## INSTALLATION

1.  Install django_replicated distribution using "python setup.py install".

2.  In settings.py configure your master and slave databases in a standard way:

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

3.  Teach django_replicated which databases are slaves:

        DATABASE_SLAVES = ['slave1', 'slave2']

    The 'default' database is always treated as master.

4.  Configure a replication router:

        DATABASE_ROUTERS = ['django_replicated.ReplicationRouter']

5.  Configure timeout to exclude a database from the available list after an
    unsuccessful ping:

        DATABASE_DOWNTIME = 20

    The default downtime value is 60 seconds.


## USAGE

Django_replicated routes SQL queries into different databases based not only on
their type (insert/update/delete vs. select) but also on its own current state.
This is done to avoid situation when in a single logical operations you're
doing both writes and reads. If all writes would go into one database and reads
would be from another one then you won't have a consistent view of the world
because of two reasons:

- when using transactions the result of writes won't be replicated into a slave
  until commit
- even in a non-transactional environment there's always a certain lag between
  updates in a master and in slaves

Django_replicated expects you to define what these logical operations are
doing: writing/reading or only reading. Then it will try to use slave databases
only for purely reading operations.

To define this there are several methods.


### Middleware

If your project is built in accordance to principles of HTTP where GET requests
don't cause changes in the system (unless by side effects) then most of the
work is done by simply using a middleware :

    MIDDLEWARE_CLASSES = [
        ...
        'django_replicated.middleware.ReplicationMiddleware',
        ...
    ]

The middleware sets replication state to use slaves during handling of GET and
HEAD requests and to use a master otherwise.

While this is usually enough there are cases when DB access is not controlled
explicitly by your business logic. Good examples are implicit creation of
sessions on first access, writing some bookkeeping info, implicit registration
of a user account somewhere inside the system. These things can happen at
arbitrary moments of time, including during GET requests.

Generally django_replicated handles this by always providing a master databases
for write operations. If this is not enough (say you still want to read a
newly created session and want to make sure that it will be read from a master)
you can always instruct Django ORM to [use a certain database][2].

[2]: http://docs.djangoproject.com/en/dev/topics/db/multi-db/#manually-selecting-a-database


### Decorators

If your system doesn't depend on the method of HTTP request to do writes and
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
updates. In practice this mean that after submitting a POST form that redirects
to a page with updated data this page may be requested from a slave replica
that wasn't updated yet. And the user will have an impression that the submit
didn't work.

To overcome this problem both ReplicationMiddleware and decorators support
special technique where handling of a GET request resulting from a redirect
after a POST is explicitly routed to a master database.


### Global overrides

In some cases it might be necessary to override how the middleware chooses
a target database based on the HTTP request method. For example you might want to
route certain POST requests to a slave if you know that the request handler
doesn't do any writes. The settings variable `REPLICATED_VIEWS_OVERRIDES` holds
the mapping of view names (urlpatterns names) or view import paths to database
names:

    REPLICATED_VIEWS_OVERRIDES = {
        'api-store-event': 'slave',
        'app.views.do_smthg': 'master',
    }


### Disabling state switching

There are cases when you want to disable switching of replication modes
entirely. A most common example is testing your code with tests that use
non-commiting transactions to preserve data between testcases. Each test is
called with a default master database which it uses to load fixtures. Then if
any code that the test calls will switch replication to the slave mode, it
won't see any fixture data in a test slave database because the master never
commits.

You can disable mode switching for such cases:

    from django_replicated import utils
    utils.disable_state_change()

(There's also a similar `enalble_state_change()` function.)
