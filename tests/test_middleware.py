# coding: utf-8

import pytest
from mock import patch

from django.test import RequestFactory
from django.test.utils import override_settings
from django.conf import settings as django_settings

from django_replicated.middleware import ReadOnlyMiddleware
from django_replicated.utils import routers, SettingsProxy
settings = SettingsProxy()


pytestmark = pytest.mark.django_db


@pytest.fixture
def _request():
    factory = RequestFactory()
    return factory.get('/')


@pytest.mark.parametrize('method', ['get', 'head'])
def test_replicated_middleware_slave_state(client, method):
    client.generic(method, '/')

    assert routers.state() == 'slave'


def test_replicated_middleware_master_state(client):
    client.post('/')

    assert routers.state() == 'master'

    assert client.cookies[settings.REPLICATED_FORCE_MASTER_COOKIE_NAME].value == 'true'


@pytest.mark.parametrize('url,view_id', [('/', 'tests._test_urls.view'),
                                         ('/with_name', 'view-name'),
                                         ('/as_class', 'tests._test_urls.TestView'),
                                         ('/as_callable', 'tests._test_urls.TestCallable')])
def test_replicated_middleware_view_overrides(client, settings, url, view_id):
    routers.init('slave')

    django_settings.REPLICATED_VIEWS_OVERRIDES = {view_id: 'master'}

    response = client.get(url)

    assert response.status_code == 302
    assert routers.state() == 'master'


def test_replicated_middleware_force_state_by_header(client):
    response = client.get('/', **{settings.REPLICATED_FORCE_STATE_HEADER: 'master'})

    assert response.status_code == 302
    assert routers.state() == 'master'

    response = client.post('/', **{settings.REPLICATED_FORCE_STATE_HEADER: 'slave'})

    assert response.status_code == 302
    assert routers.state() == 'slave'


def test_replicated_force_master_cookie(client):
    with override_settings(REPLICATED_FORCE_MASTER_COOKIE_STATUS_CODES=[200]):
        response = client.post('/')

        assert response.status_code == 302
        assert settings.REPLICATED_FORCE_MASTER_COOKIE_NAME not in response.cookies

        response = client.post('/just_updated')

        assert response.status_code == 200
        assert settings.REPLICATED_FORCE_MASTER_COOKIE_NAME in response.cookies
        assert response.cookies.get(settings.REPLICATED_FORCE_MASTER_COOKIE_NAME).value == 'true'


def test_readonly_middleware_check_db(_request):
    with patch('django_replicated.dbchecker.check_db') as check_db_mock:
        check_db_mock.return_value = True

        ReadOnlyMiddleware().process_request(_request)

        check_db_mock.assert_not_called()
        assert not _request.service_is_readonly
        assert check_db_mock.call_count == 2


def test_readonly_middleware_is_alive(_request):
    with patch('django_replicated.dbchecker.is_alive') as is_alive_mock:
        is_alive_mock.return_value = False

        ReadOnlyMiddleware().process_request(_request)

        assert _request.service_is_readonly


def test_readonly_middleware_is_writable(_request):
    with patch('django_replicated.dbchecker.is_writable') as is_writable_mock:
        is_writable_mock.return_value = False

        ReadOnlyMiddleware().process_request(_request)

        assert _request.service_is_readonly

