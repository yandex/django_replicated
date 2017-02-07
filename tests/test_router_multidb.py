# coding: utf-8

from __future__ import unicode_literals

import pytest
import mock

from django import db
from django.db import models

from .test_router import model, django_router as django_router_base

pytestmark = pytest.mark.django_db


@pytest.fixture
def multidb_settings(settings):
    settings.REPLICATED_WRAPPED_ROUTER = 'django_replicated.utils.OverridesDatabaseRouter'
    base_config = settings.DATABASES['default']
    extra_databases = dict(
        db2=dict(
            base_config,
            # Many slaves to increase chances that the stochastic behavior is tested.
            SLAVES=["db2_slave{}".format(idx) for idx in range(20)],
        ),
    )
    extra_databases.update(
        (name, dict(base_config))
        for name in extra_databases['db2']['SLAVES'])
    settings.DATABASES.update(extra_databases)  # XX: does the pytest-django's mockup handle this?


@pytest.fixture
def router(multidb_settings):
    from django_replicated.router import ReplicationRouter
    return ReplicationRouter()


@pytest.yield_fixture
def django_router(multidb_settings):
    res = db.ConnectionRouter()
    # Mock needed for the `django_replicated.utils.routers` code.
    with mock.patch.object(db, 'router', new=res):
        yield res


@pytest.fixture
def mdb_model():
    class _TestModelMdb(models.Model):
        _route_database = 'db2'
        class Meta:
            app_label = 'django_replicated'

    return _TestModelMdb


@pytest.fixture
def mdb_model_2():
    class _TestModelMdb2(models.Model):
        _route_database = 'db2'
        class Meta:
            app_label = 'django_replicated'

    return _TestModelMdb2


def test_router_db_for_write(router, mdb_model):
    assert router.db_for_write(mdb_model) == 'db2'


def test_router_db_for_read(router, mdb_model, model):
    router.use_state('slave')

    res1 = router.db_for_read(mdb_model)
    assert res1.startswith('db2_slave'), "supposed to select an overridden slave"
    res2 = router.db_for_read(mdb_model)
    assert res1 == res2, "supposed to select the same slave again"
    # Use the same router on another model to ensure its state does not screw up:
    # `test_router.test_router_db_for_read(router, model)`
    assert router.db_for_read(model) in ('slave1', 'slave2')


def test_django_router_db_for_read(django_router, mdb_model, model):
    # Same code as middleware:
    from django_replicated.utils import routers
    routers.init('slave')

    router = django_router

    # `test_router_db_for_read`
    res1 = router.db_for_read(mdb_model)
    assert res1.startswith('db2_slave'), "supposed to select an overridden slave"
    res2 = router.db_for_read(mdb_model)
    assert res1 == res2, "supposed to select the same slave again"
    # Use the same router on another model to ensure its state does not screw up:
    # `test_router.test_router_db_for_read(router, model)`
    assert router.db_for_read(model) in ('slave1', 'slave2')


def test_router_allow_relation(django_router, model, mdb_model, mdb_model_2):
    from django_replicated.utils import routers

    models = [model, mdb_model, mdb_model_2]
    objs = [mdl() for mdl in models]

    for state in ('slave', 'master'):

        routers.init('slave')

        for obj in objs:
            obj._state.db = django_router.db_for_read(obj.__class__)

        obj1, obj2, obj3 = objs
        assert django_router.allow_relation(obj2, obj3)
        assert not django_router.allow_relation(obj1, obj2)
        assert not django_router.allow_relation(obj1, obj3)
