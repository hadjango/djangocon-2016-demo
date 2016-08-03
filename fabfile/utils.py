# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contextlib import contextmanager
import os
import re

import six

from fabric.api import env, local
from fabric.context_managers import cd, path, quiet
from fabric.state import win32


ROOT_DIR = os.path.dirname(os.path.dirname(__file__))

IN_DOCKER = os.path.exists('/addons-server-centos7-container')

if IN_DOCKER:
    DOCKER_NAME = ""
else:
    COMPOSE_PROJECT_NAME = os.path.basename(ROOT_DIR.replace('-', '').replace('_', ''))
    DOCKER_NAME = "%s_%%(server)s_1" % COMPOSE_PROJECT_NAME


def docker_exec(*cmd, **kwargs):
    server = kwargs.pop('server', 'web')
    root = kwargs.pop('root', False if server == 'web' else True)
    default_cwd = "addons-server" if server == "web" else "/"
    cwd = env['cwd'] if env['cwd'] else default_cwd
    if not cmd[0].startswith('cd '):
        cmd = ("cd %s" % cwd, ) + cmd
    cmd = " && ".join(cmd)
    if server == "web":
        cmd = _prefix_env_vars(cmd)
    cmd = cmd.replace("'", "'\"'\"'")
    if root:
        full_cmd = "bash -c '%s'" % cmd
    else:
        full_cmd = """su olympia -c 'bash -c '"'"'%s'"'"''""" % cmd.replace("'", "'\"'\"'")
    if not IN_DOCKER:
        container_name = DOCKER_NAME % {'server': server}
        full_cmd = "docker exec -t -i %s %s" % (container_name, full_cmd)
    if (six.PY2 and isinstance(full_cmd, unicode)):
        full_cmd = full_cmd.encode('utf-8')
    return local(full_cmd, **kwargs)


@contextmanager
def build_venv(name):
    old_build_name = env.get('build_name')
    env['build_name'] = name
    build_dir = "/code/deploy/builds/%s" % name
    with cd("%s" % build_dir):
        docker_exec("[ -f bin/pip ] || virtualenv . --never-download")
        with path(os.path.join(build_dir, 'bin'), behavior='prepend'):
            yield
    env['build_name'] = old_build_name


_find_unsafe = re.compile(r'[a-zA-Z0-9_^@%+=:,./-]').search


def quote(s):
    """Return a shell-escaped version of the string *s*."""
    if not s:
        return "''"

    if _find_unsafe(s) is None:
        return s

    # use single quotes, and put single quotes into double quotes
    # the string $'b is then quoted as '$'"'"'b'

    return "'" + s.replace("'", "'\"'\"'") + "'"


def _shell_escape(string):
    """
    Escape double quotes, backticks and dollar signs in given ``string``.

    For example::

        >>> _shell_escape('abc$')
        'abc\\\\$'
        >>> _shell_escape('"')
        '\\\\"'
    """
    for char in ('"', '$', '`'):
        string = string.replace(char, '\%s' % char)
    return string


def _prefix_env_vars(command, local=False):
    """
    Prefixes ``command`` with any shell environment vars, e.g. ``PATH=foo ``.

    Currently, this only applies the PATH updating implemented in
    `~fabric.context_managers.path` and environment variables from
    `~fabric.context_managers.shell_env`.

    Will switch to using Windows style 'SET' commands when invoked by
    ``local()`` and on a Windows localhost.
    """
    env_vars = {}

    # path(): local shell env var update, appending/prepending/replacing $PATH
    path = env.path
    if path:
        if env.path_behavior == 'append':
            path = '$PATH:\"%s\"' % path
        elif env.path_behavior == 'prepend':
            path = '\"%s\":$PATH' % path
        elif env.path_behavior == 'replace':
            path = '\"%s\"' % path

        env_vars['PATH'] = path

    # shell_env()
    env_vars.update(env.get('docker_shell_env'))

    if env_vars:
        set_cmd, exp_cmd = '', ''
        if win32 and local:
            set_cmd = 'SET '
        else:
            exp_cmd = 'export '

        exports = ' '.join(
            '%s%s="%s"' % (set_cmd, k, v if k == 'PATH' else _shell_escape(v))
            for k, v in env_vars.iteritems()
        )
        shell_env_str = '%s%s && ' % (exp_cmd, exports)
    else:
        shell_env_str = ''

    return "%s%s" % (shell_env_str, command)


def dealias_build(name):
    if name in ("live", "stage"):
        name = "_%s" % name
    path = "%s/deploy/builds/%s" % (ROOT_DIR, name)
    with quiet():
        return os.path.basename(
            docker_exec("cd %s && pwd -P" % path, capture=True))
