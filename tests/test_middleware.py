# coding: utf-8

import contextlib

import pytest
from mock import patch

from django.test import RequestFactory
from django.test.utils import override_settings
from django.conf import settings

from django_replicated.dbchecker import is_writable, is_alive
from django_replicated.middleware import ReadOnlyMiddleware
from django_replicated.utils import routers


pytestmark = pytest.mark.django_db


@pytest.fixture
def _request():
    factory = RequestFactory()
    return factory.get('/')


@pytest.mark.parametrize('method', ['get', 'head'])
def test_replicated_middleware_slave_state(client, method):
    response = client.generic(method, '/')
    assert response['Router-Used'] == 'slave'

    # Router state is reset to 'master' after request is processed
    assert routers.state() == 'master'


def test_replicated_middleware_master_state(client):
    response = client.post('/')
    assert response['Router-Used'] == 'master'

    assert routers.state() == 'master'

    assert client.cookies[settings.REPLICATED_FORCE_MASTER_COOKIE_NAME].value == 'true'


def test_does_not_set_force_master_cookie_on_get(client):
    client.get('/')
    assert client.cookies == {}


@pytest.mark.parametrize('url,view_id', [('/', 'tests._test_urls.view'),
                                         ('/admin/auth/', '/admin/auth/'),
                                         ('/admin/auth/', '/admin/*'),
                                         ('/with_name', 'view-name'),
                                         ('/namespace/with-namespace', 'namespace:with-namespace'),
                                         ('/as_class', 'tests._test_urls.TestView'),
                                         ('/as_callable', 'tests._test_urls.TestCallable'),
                                         ('/as_instancemethod', 'tests._test_urls.instancemethodview')])
def test_replicated_middleware_view_overrides(client, settings, url, view_id):
    routers.init('slave')

    settings.REPLICATED_VIEWS_OVERRIDES = {view_id: 'master'}

    response = client.get(url)

    assert response.status_code == 302
    assert response['Router-Used'] == 'master'
    assert routers.state() == 'master'


def test_replicated_middleware_force_state_by_header(client):
    response = client.get('/', **{settings.REPLICATED_FORCE_STATE_HEADER: 'master'})

    assert response.status_code == 302
    assert response['Router-Used'] == 'master'
    assert routers.state() == 'master'

    response = client.post('/', **{settings.REPLICATED_FORCE_STATE_HEADER: 'slave'})

    assert response.status_code == 302
    assert response['Router-Used'] == 'slave'
    assert routers.state() == 'master'


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


class CursorMock(object):
    def __init__(self):
        self.is_closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_cls, exc, tb):
        self.close()
        return False

    def close(self):
        self.is_closed = True

    def execute(self, command):
        pass

    def fetchone(self):
        return [True]


class ConnectionMock(object):
    vendor = 'postgresql'
    connection = None
    alias = ''

    def __init__(self):
        self.cursor_mocks = []

    def cursor(self):
        cursor_mock = CursorMock()

        self.cursor_mocks.append(cursor_mock)

        return cursor_mock

    def cursors_is_closed(self):
        return all(cursor.is_closed for cursor in self.cursor_mocks)


class ConnectionHandlerMock(object):
    def __init__(self):
        self.connection_mocks = None

    def __getitem__(self, item):
        assert item == 'default'

        self.connection_mock = ConnectionMock()
        return self.connection_mock


class CacheMock(object):
    def get(self, key):
        return None

    def set(self, *args):
        pass


@contextlib.contextmanager
def mock_connections():
    with patch('django_replicated.dbchecker.cache', CacheMock()):
        with patch('django_replicated.dbchecker.connections', ConnectionHandlerMock()) as connections_mock:
            yield

        assert connections_mock.connection_mock.cursors_is_closed()


def test_readonly_middleware_is_alive(_request):
    with patch('django_replicated.dbchecker.is_alive') as is_alive_mock:
        is_alive_mock.side_effect = is_alive

        with mock_connections():
            ReadOnlyMiddleware().process_request(_request)
            assert _request.service_is_readonly

        assert is_alive_mock.call_count == 1


def test_readonly_middleware_is_writable(_request, settings):
    settings.REPLICATED_READ_ONLY_DOWNTIME = 1
    settings.REPLICATED_READ_ONLY_TRIES = 1

    with patch('django_replicated.dbchecker.is_alive') as is_alive_mock:
        is_alive_mock.return_value = True

        with patch('django_replicated.dbchecker.is_writable') as is_writable_mock:
            is_writable_mock.side_effect = is_writable

            with mock_connections():
                ReadOnlyMiddleware().process_request(_request)
                assert _request.service_is_readonly

            assert is_writable_mock.call_count == 1

        assert is_alive_mock.call_count == 1


def test_disable_manage_atomic_requests(_request):
    with override_settings(REPLICATED_MANAGE_ATOMIC_REQUESTS=False):
        with patch('django_replicated.middleware.ReplicationMiddleware.set_non_atomic_dbs') as set_non_atomic_dbs:
            from django_replicated.middleware import ReplicationMiddleware

            view = lambda: None
            ReplicationMiddleware().process_view(_request, view)
            set_non_atomic_dbs.assert_not_called()


def test_non_atomic_view(client):
    from ._test_urls import non_atomic_view as view

    with override_settings(REPLICATED_MANAGE_ATOMIC_REQUESTS=True):
        assert not hasattr(view, '_replicated_view_default_non_atomic_dbs')

        with patch('django.db.transaction.atomic') as atomic:
            atomic.return_value = lambda view: view

            client.post('/non_atomic_view')
            atomic.assert_not_called()
            assert view._replicated_view_default_non_atomic_dbs == {'default'}
            assert view._non_atomic_requests == {'default', 'slave1', 'slave2'}

        with patch('django.db.transaction.atomic') as atomic:
            atomic.return_value = lambda view: view

            response = client.get('/non_atomic_view')
            atomic.assert_not_called()
            assert view._replicated_view_default_non_atomic_dbs == {'default'}
            assert view._non_atomic_requests == {'default', 'slave1', 'slave2'} - {response['DB-Used']}


@pytest.mark.parametrize('url', ['/', '/with_name', '/as_callable', '/as_instancemethod'])
def test_atomic_view(client, url):
    with override_settings(REPLICATED_MANAGE_ATOMIC_REQUESTS=True):
        with patch('django.db.transaction.atomic') as atomic:
            atomic.return_value = lambda view: view

            response = client.get(url)
            atomic.assert_not_called()
            assert response['Default-Non-Atomic'] == ''
            assert response['Non-Atomic'] == ','.join(sorted({'default', 'slave1', 'slave2'} - {response['DB-Used']}))

        with patch('django.db.transaction.atomic') as atomic:
            atomic.return_value = lambda view: view

            response = client.post(url)
            atomic.assert_called_once_with(using='default')
            assert response['Default-Non-Atomic'] == ''
            assert response['Non-Atomic'] == 'slave1,slave2'

        with patch('django.db.transaction.atomic') as atomic:
            atomic.return_value = lambda view: view

            response = client.get(url)
            atomic.assert_called_once_with(using='default')
            assert response['Default-Non-Atomic'] == ''
            assert response['Non-Atomic'] == ','.join(sorted({'default', 'slave1', 'slave2'} - {response['DB-Used']}))
