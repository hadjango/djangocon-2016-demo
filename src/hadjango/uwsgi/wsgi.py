import re
import os
import sys
import site
import uwsgi


project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

sys.path.insert(0, project_root)
site.addsitedir(os.path.join(
        project_root,
        "lib",
        "python" + sys.version[0:3],
        "site-packages"))


def get_site_name():
    settings_module = os.environ.get('DJANGO_SETTINGS_MODULE') or ''
    matches = re.match(r'settings\.(\w+)\.live', settings_module)
    if matches:
        site_name = matches.group(1)
    else:
        site_name = 'unknown'
    return site_name


site_name = get_site_name()


def set_uwsgi_proc_name():
    build_dir = os.path.basename(project_root)
    try:
        deploy_tag = open(os.path.join(project_root, '.DEPLOY_TAG')).read().strip()
    except IOError:
        deploy_tag = '?'

    os.environ['DEPLOY_TAG'] = deploy_tag

    uwsgi.setprocname("uwsgi worker %(worker_id)d <%(build)s> [%(tag)s]" % {
        'worker_id': uwsgi.worker_id(),
        'build': build_dir,
        'tag': deploy_tag,
    })


set_uwsgi_proc_name()

execfile(os.path.join(os.path.dirname(__file__), 'bootstrap.py'))

_application = None


def application(environ, start_response):
    global _application

    uwsgi.set_logvar('worker_id', str(uwsgi.worker_id()))

    if not os.environ.get('DJANGO_SETTINGS_MODULE'):
        os.environ['DJANGO_SETTINGS_MODULE'] = environ.get('DJANGO_SETTINGS_MODULE', 'settings')

    if _application is None:
        try:
            from django.core.wsgi import get_wsgi_application
        except ImportError:
            import django.core.handlers.wsgi
            _application = django.core.handlers.wsgi.WSGIHandler()
        else:
            _application = get_wsgi_application()

    return _application(environ, start_response)
