import os

from olympia.lib.settings_base import INSTALLED_APPS


INSTALLED_APPS = ('hadjango', ) + INSTALLED_APPS + ('olympia.landfill', )

BROKER_URL = 'amqp://olympia:olympia@rabbitmq/olympia'
CELERY_RESULT_BACKEND = 'redis://redis:6379/1'
REDIS_LOCATION = 'redis://redis:6379/0?socket_timeout=0.5'
ES_HOSTS = ['elasticsearch:9200']
ES_URLS = ['http://%s' % h for h in ES_HOSTS]
SITE_DIR = 'http://olympia.dev'

CACHES = {
    'default': {
        'BACKEND': 'caching.backends.memcached.MemcachedCache',
        'LOCATION': 'memcached:11211',
    }
}


ROOT = os.path.realpath(os.path.dirname(__file__))

BUILD_NAME = os.path.basename(ROOT)
STATIC_ROOT = os.path.join(ROOT, "assets", "static")
MEDIA_ROOT = os.path.join(ROOT, "assets", "media")
STATIC_URL = "/static/%s/" % BUILD_NAME

CELERY_ALWAYS_EAGER = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'olympia',
        'USER': 'root',
        'PASSWORD': '',
        'HOST': 'mysqld',
        'PORT': '',
        'OPTIONS': {'sql_mode': 'STRICT_ALL_TABLES'},
        'TEST_CHARSET': 'utf8',
        'TEST_COLLATION': 'utf8_general_ci',
        # Run all views in a transaction unless they are decorated not to.
        'ATOMIC_REQUESTS': True,
        # Pool our database connections up for 300 seconds
        'CONN_MAX_AGE': 300,
    },
}

# A database to be used by the services scripts, which does not use Django.
# The settings can be copied from DATABASES, but since its not a full Django
# database connection, only some values are supported.
SERVICES_DATABASE = {
    'NAME': DATABASES['default']['NAME'],
    'USER': DATABASES['default']['USER'],
    'PASSWORD': DATABASES['default']['PASSWORD'],
    'HOST': DATABASES['default']['HOST'],
    'PORT': DATABASES['default']['PORT'],
}
