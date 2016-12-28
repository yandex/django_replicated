# coding: utf-8

import pytest

from django.conf import settings


pytestmark = pytest.mark.django_db


def pytest_configure():
    settings.configure(
        DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3'},
                   'slave1': {'ENGINE': 'django.db.backends.sqlite3'},
                   'slave2': {'ENGINE': 'django.db.backends.sqlite3'},},
        REPLICATED_DATABASE_SLAVES=['slave1', 'slave2'],
        DATABASE_ROUTERS=['django_replicated.router.ReplicationRouter'],
        MIDDLEWARE_CLASSES=['django_replicated.middleware.ReplicationMiddleware'],
        ROOT_URLCONF='tests._test_urls',
    )
