"""
A script which preloads most modules in Django.

This file is executed via execfile() from other files in this directory.

It is assumed that the original file which is executing this file has set
os.environ['DJANGO_SETTINGS_MODULE'] prior to calling execfile().
"""
import os
from importlib import import_module


os.environ["CELERY_LOADER"] = "django"


def run_mgmt_validate():
    import django.core.management
    utility = django.core.management.ManagementUtility()
    command = utility.fetch_command('runserver')
    command.validate(display_num_errors=True)


def load_templatetags():
    import_module('django.template.base').get_templatetags_modules()


def load_admin():
    import_module('django.contrib.admin').autodiscover()


def load_i18n(lang_code):
    import_module('django.utils.translation').activate(lang_code)


def load_urls():
    import_module('django.core.urlresolvers').resolve('/')


def setup():
    import django

    django.setup()

    from django.conf import settings

    load_templatetags()
    if 'django.contrib.admin' in settings.INSTALLED_APPS:
        load_admin()
    load_i18n(settings.LANGUAGE_CODE)

    load_urls()

    run_mgmt_validate()


setup()
