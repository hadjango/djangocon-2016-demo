# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from glob import glob
import socket
import time
import os
import re

from fabric.api import task, local, env
from fabric.context_managers import cd, quiet
from fabric.utils import abort

from .build_port_convert import build_to_port, base26_encode
from .utils import docker_exec, build_venv, dealias_build
# from . import test  # noqa


ROOT_DIR = os.path.dirname(os.path.dirname(__file__))

NUM_ADDONS = NUM_THEMES = 10

env.docker_shell_env = {
    'NPM_CONFIG_PREFIX': '/code/deploy/deps/',
    'PIP_CACHE_DIR': '/code/deploy/deps/cache/',
    'LANG': 'en_US.UTF-8',
    'LC_ALL': 'en_US.UTF-8',
}


@task
def init():
    """to initialize a docker image"""
    build_wheels()
    docker_exec("mkdir -p /code/deploy/assets/{static,media}")
    create_build("a")
    create_build("b")
    docker_exec(
        "ln -sfvn a /code/deploy/builds/_live",
        "ln -sfvn b /code/deploy/builds/_stage")
    initialize_db()
    populate_data()
    activate("a")
    activate("b")
    nginx_reload()


@task
def build_wheels():
    """Build the wheels for all dependencies"""
    tmp_dir = docker_exec("mktemp -d", capture=True)
    with cd(tmp_dir):
        docker_exec(
            "cp /code/addons-server/requirements/*.txt .",
            "cp /code/src/requirements/hadjango.txt .",
            "mkdir -p /code/deploy/deps/wheelhouse",
            r"perl -pi -e 's/^ .+$//g;s/ \\//g;s/setuptools==23\.0\.0/setuptools==25\.1\.1/g;' *.txt",
            "pip wheel -f /code/deploy/deps/wheelhouse --wheel-dir=/code/deploy/deps/wheelhouse --no-deps -r dev.txt",
            "pip wheel -f /code/deploy/deps/wheelhouse --wheel-dir=/code/deploy/deps/wheelhouse --no-deps -r docs.txt",
            "pip wheel -f /code/deploy/deps/wheelhouse --wheel-dir=/code/deploy/deps/wheelhouse --no-deps -r hadjango.txt",
            ("pip wheel -f /code/deploy/deps/wheelhouse --wheel-dir=/code/deploy/deps/wheelhouse --no-deps -r"
             " <(perl -pe 's/^\-e //g;' prod_without_hash.txt)"))


@task
def create_build(name):
    """Creates a new build of the Mozilla addons-server"""
    symlink_static_dirs(name)
    copy_src(name)
    git_init(name)
    with build_venv(name):
        npm_install(name)
        pip_install(name)
        build_assets(name)
        port = build_to_port(name)
        docker_exec(
            'echo "upstream web { server web:%d; }" > live.conf' % port,
            'echo "upstream webstage { server web:%d; }" > stage.conf' % port,
            'date +%FT%T > .DEPLOY_TAG')
        docker_exec("ln -svfn /code/conf/uwsgi/vassal.skel vassal.ini")


def symlink_static_dirs(name):
    """
    Creates symlinks for the static and media directories of build ``name`` so
    that nginx static serving works correctly.

    The directory './deploy/assets/static/%(name)s' will be created, along with
    the following symlink

        - ./deploy/builds/%(name)s/assets/static -> ./deploy/assets/static/%(name)s
    """
    build_dir = "/code/deploy/builds/%s" % name
    static_dir = "/code/deploy/assets/static/%s" % name
    link_dir = "%s/assets/static" % build_dir
    docker_exec(
        "mkdir -p %s" % static_dir,
        "mkdir -p %s/assets" % build_dir,
        "ln -sfvn /code/deploy/assets/media %s/assets/media" % build_dir,
        "[ -L %(link_dir)s ] || ln -s %(static_dir)s %(link_dir)s" % {
            'link_dir': link_dir,
            'static_dir': static_dir,
        })

    for d in glob("%s/deploy/assets/static/*" % ROOT_DIR):
        link_dir = "/code/deploy/assets/static/%s/%s" % (os.path.basename(d), name)
        docker_exec("[ -L %(link_dir)s ] || ln -s %(static_dir)s %(link_dir)s" % {
            'link_dir': link_dir,
            'static_dir': static_dir,
        })


def copy_src(name):
    build_dir = "/code/deploy/builds/%s" % name
    docker_exec(
        "git ls-files"
        " | perl -pne 's/\"//g; s/e\\\\314\\\\201/é/g;'"  # Fix jétpack.xpi path
        " | rsync -a --info=progress2 --files-from=- . %s" % build_dir)
    docker_exec("cp /code/src/local_settings.py %s" % build_dir)
    with build_venv(name):
        docker_exec("cp -R /code/src/hadjango .")
        docker_exec("cp /code/src/requirements/*.txt requirements")
        docker_exec("cp /code/fabfile/build_port_convert.py hadjango")
        docker_exec(
            r"perl -pi -e "
            r"'s/^ .+$//g;s/ \\//g;"
            r"s/setuptools==23\.0\.0/setuptools==25\.1\.1/g;' "
            "requirements/*.txt")


def git_init(name):
    """Create fake git repo so that jingo minify can cache bust images"""
    if not os.path.exists("%s/deploy/builds/%s/.git" % (ROOT_DIR, name)):
        with build_venv(name):
            docker_exec(
                'git init',
                'cat /dev/urandom | head -c256 > .random',
                'git add .random',
                'git commit -m "Initial commit"')


def pip_install(name):
    build_wheels()
    args = "-f /code/deploy/deps/wheelhouse --no-index --no-deps"
    with build_venv(name):
        olympia_egg_link = (
            "/code/deploy/builds/%s/lib/python2.7/site-packages/olympia.egg-link" % name)
        docker_exec((
            '[ -f %(egg_link)s ]'
            ' || pip install %(args)s -e .') % {'egg_link': olympia_egg_link, 'args': args})
        docker_exec(
            "pip install %s -r requirements/dev.txt" % args,
            "pip install %s -r requirements/docs.txt" % args,
            "pip install %s -r requirements/prod_without_hash.txt" % args,
            "pip install %s -r requirements/hadjango.txt" % args)


def npm_install(name="_live"):
    if os.path.exists(os.path.join(ROOT_DIR, 'deploy', 'builds', name, 'node_modules')):
        return
    with build_venv(name):
        # npm install has a bug when run inside docker on a mounted volume
        # (see <https://github.com/npm/npm/issues/9863>). So we run npm
        # install in a temp directory, then move it back.
        tmp_dir = docker_exec("mktemp -d", capture=True)
        docker_exec("cp package.json %s" % tmp_dir)
        with cd(tmp_dir):
            docker_exec("npm install")
        docker_exec("mv %s/node_modules ." % tmp_dir)


def initialize_db():
    """to create a new database"""
    with build_venv("_live"):
        docker_exec(
            "python manage.py reset_db",
            "python manage.py syncdb --noinput",
            "python manage.py loaddata initial.json",
            "python manage.py import_prod_versions",
            "schematic --fake src/olympia/migrations/",
            "python manage.py createsuperuser",
            "python manage.py loaddata zadmin/users")


def populate_data():
    """to populate a new database"""
    with build_venv("_live"):
        docker_exec(
            # reindex --wipe will force the ES mapping to be re-installed. Useful to
            # make sure the mapping is correct before adding a bunch of add-ons.
            "python manage.py reindex --wipe --force --noinput",
            "python manage.py generate_addons --app firefox %s" % NUM_ADDONS,
            "python manage.py generate_addons --app thunderbird %s" % NUM_ADDONS,
            "python manage.py generate_addons --app android %s" % NUM_ADDONS,
            "python manage.py generate_addons --app seamonkey %s" % NUM_ADDONS,
            "python manage.py generate_themes %s" % NUM_THEMES,
            # Now that addons have been generated, reindex.
            "python manage.py reindex --force --noinput",
            # Also update category counts (denormalized field)
            "python manage.py cron category_totals")


def build_assets(name):
    with build_venv(name):
        docker_exec(
            "python manage.py compress_assets",
            "python manage.py collectstatic --noinput")


@task
def swap_live(name=None):
    """Swap the specified build (default: _stage) with _live"""
    if name is None:
        name = dealias_build("_stage")
    live = dealias_build("_live")
    with cd("/code/deploy/builds"):
        docker_exec(
            "ln -snvf %s _stage" % live,
            "ln -snvf %s _live" % name)
    nginx_reload()


@task
def stage(name):
    live = dealias_build("_live")
    stage = dealias_build("_stage")
    if name == live:
        abort("Cannot stage the live build; use 'fab swap_live' instead")
    if name == stage:
        abort("Build %s is already staged" % name)
    if not os.path.islink("%s/deploy/builds/%s/zerg.ini" % (ROOT_DIR, name)):
        activate(name)
        time.sleep(10)
        warmup(name)
    with cd("/code/deploy/builds"):
        docker_exec("ln -snvf %s _stage" % name)


@task
def activate(name):
    """Start a uWSGI instance for the given build"""
    with build_venv(name):
        # Wait for the emperor to poll again
        docker_exec("ln -svfn /code/conf/uwsgi/zerg.skel zerg.ini")
        time.sleep(3)


@task
def deactivate(name):
    """Stop the uWSGI instance for the given build"""
    with build_venv(name):
        docker_exec("rm -f zerg.ini")
        time.sleep(3)


@task
def warmup(name="_stage"):
    """Warm up a build, to be used before swapping to live"""
    with build_venv(name):
        docker_exec("python manage.py warmup")


@task
def nginx_reload():
    """Reload nginx config"""
    docker_exec("nginx -s reload", server="nginx")


@task
def ip():
    """The ip where the addons site can be accessed"""
    docker_host = os.environ.get("DOCKER_HOST") or ""
    if not docker_host:
        with quiet():
            docker_env = local("docker-machine env addons", capture=True)
        if docker_env:
            match = re.search(r'DOCKER_HOST="(tcp://[^"]+?)"', docker_env)
            if match:
                docker_host = match.group(1)

    match = re.search(r'tcp://([^:]+):', docker_host)
    if match:
        print(match.group(1))
    else:
        try:
            # host used by dlite
            _, _, ips = socket.gethostbyname_ex("local.docker")
        except:
            abort("Could not determine docker-machine host; perhaps localhost?")
        else:
            print(ips[0])


@task
def find_free_build():
    """Find what the next free build directory name is."""
    current_builds = set([os.path.basename(p) for p in glob("%s/deploy/builds/[a-z]*" % ROOT_DIR)])
    i = 0
    while True:
        build = base26_encode(i)
        if build not in current_builds:
            print(build)
            return
        i += 1


@task
def djshell(name="_live"):
    """Connect to a running addons-server django shell"""
    with build_venv(name):
        docker_exec("python manage.py shell")


@task
def shell(server='web'):
    """Connect to a running addons-server docker shell"""
    cwd = '/code' if server == 'web' else '/'
    with cd(cwd):
        docker_exec("bash", root=True, server=server)
