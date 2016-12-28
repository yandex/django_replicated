# coding: utf-8
from __future__ import unicode_literals

import pytest
import mock

from django import db
from django.db import models, router as django_router
from django.test.utils import override_settings


from django_replicated.router import ReplicationRouter


pytestmark = pytest.mark.django_db


@pytest.fixture
def router():
    return ReplicationRouter()


@pytest.fixture
def model():
    class _TestModel(models.Model):
        class Meta:
            app_label = 'django_replicated'

    return _TestModel


def test_router_db_for_write(router, model):
    assert router.db_for_write(model) == db.DEFAULT_DB_ALIAS


def test_router_db_for_write_illegal_state(router, model, settings):
    router.use_state('slave')

    with pytest.raises(RuntimeError):
        router.db_for_write(model)


def test_router_db_for_read(router, model):
    router.use_state('slave')

    assert router.db_for_read(model) in ('slave1', 'slave2')


def test_router_db_for_read_fallback(router, model):
    router.use_state('slave')

    with mock.patch.object(router, 'is_alive') as is_alive_mock:
        is_alive_mock.return_value = False

        assert router.db_for_read(model) == db.DEFAULT_DB_ALIAS


def test_router_allow_relation(model):
    obj1 = model()
    obj1._state.db = 'slave1'
    obj2 = model()
    obj2._state.db = 'slave2'

    assert django_router.allow_relation(obj1, obj2)


def test_router_multimaster(model):
    with override_settings(REPLICATED_DATABASE_MASTERS=['default', 'master2']):
        router = ReplicationRouter()

        assert router.db_for_write(model) == 'default'
        assert router.db_for_write(model) == 'default', 'Master should not be random on choices'
        assert router.db_for_write(model) == 'default', 'Master should not be random on choices'

        with mock.patch.object(router, 'is_alive') as is_alive_mock:

            def default_is_down(dbname):
                return False if dbname == 'default' else True

            def master2_is_down(dbname):
                return False if dbname == 'master2' else True

            def everything_is_up(dbname):
                return True

            is_alive_mock.side_effect = default_is_down
            assert router.db_for_write(model) == 'master2', 'Should switch to first working master on fail'

            is_alive_mock.side_effect = everything_is_up
            assert router.db_for_write(model) == 'master2', 'Chosen master should be kept unless failed'
            assert router.db_for_write(model) == 'master2', 'Chosen master should be kept unless failed'
            assert router.db_for_write(model) == 'master2', 'Chosen master should be kept unless failed'

            is_alive_mock.side_effect = master2_is_down
            assert router.db_for_write(model) == 'default', 'Should switch to first working master on fail'
