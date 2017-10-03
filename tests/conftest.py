# coding: utf-8
from __future__ import unicode_literals

import pytest
from django.conf import settings

from django_replicated import settings as replicated_settings

pytestmark = pytest.mark.django_db


def pytest_configure():
    test_settings = replicated_settings.__dict__.copy()
    test_settings.update({
        'DATABASES': {
            'default': {'ENGINE': 'django.db.backends.sqlite3', 'ATOMIC_REQUESTS': True},
            'slave1': {'ENGINE': 'django.db.backends.sqlite3'},
            'slave2': {'ENGINE': 'django.db.backends.sqlite3'},
        },
        'REPLICATED_DATABASE_SLAVES': ['slave1', 'slave2'],
        'DATABASE_ROUTERS': ['django_replicated.router.ReplicationRouter'],
        'MIDDLEWARE_CLASSES': [
            'django_replicated.middleware.ReplicationMiddleware'],
        'MIDDLEWARE': [
            'django_replicated.middleware.ReplicationMiddleware'],
        'ROOT_URLCONF': 'tests._test_urls',
    })

    settings.configure(**test_settings)
