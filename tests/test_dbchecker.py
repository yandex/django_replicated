# coding: utf-8
from __future__ import unicode_literals

from mock import MagicMock, patch, call

from django.db import connections

from django_replicated.dbchecker import cache, check_db, hostname


def test_check_success():
    assert check_db(MagicMock(return_value=True), 'default') is True


def test_check_fail():
    assert check_db(MagicMock(return_value=False), 'default') is False


def test_check_retry():
    checker = MagicMock(return_value=False)

    check_db(checker, 'default', number_of_tries=3)

    checker.assert_has_calls([call(connections['default']) for _ in range(3)])


def test_check_success_no_cache():
    checker = MagicMock(return_value=True)

    with patch.object(cache, 'set') as cache_set_mock:
        check_db(checker, 'default', 10)

        checker.assert_called_once_with(connections['default'])
        cache_set_mock.assert_not_called()


def test_check_fail_set_cache():
    checker = MagicMock(return_value=False)

    with patch.object(cache, 'set') as cache_set_mock:
        check_db(checker, 'default', 10)

        checker.assert_called_once_with(connections['default'])
        cache_set_mock.assert_called_once_with('%s:MagicMock:default' % hostname, 'dead', 10)


def test_check_fail_get_cache():
    checker = MagicMock(return_value=False)

    with patch.object(cache, 'get') as cache_get_mock:
        cache_get_mock.return_value = 'dead'

        check_db(checker, 'default', 10)

        cache_get_mock.assert_called_once_with('%s:MagicMock:default' % hostname)
        checker.assert_not_called()


def test_check_fail_get_cache_force():
    checker = MagicMock(return_value=False)

    with patch.object(cache, 'get') as cache_get_mock:
        cache_get_mock.return_value = 'dead'

        check_db(checker, 'default', 10, force=True)

        cache_get_mock.assert_not_called()
        checker.assert_called_once_with(connections['default'])
