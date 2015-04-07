# django settings for tests

SECRET_KEY = '42'

DATABASES = {
    'default': {
        'NAME': 'master.sqlite',
        'ENGINE': 'django.db.backends.sqlite3',
        },
    'slave1': {
        'NAME': 'slave1.sqlite',
        'ENGINE': 'django.db.backends.sqlite3',
        },
    'slave2': {
        'NAME': 'slave2.sqlite',
        'ENGINE': 'django.db.backends.sqlite3',
        },

    }

DATABASE_SLAVES = ['slave1', 'slave2']
