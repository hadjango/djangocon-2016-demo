# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from fabric.api import task

from .utils import docker_exec, build_venv


__all__ = ('run_all', 'es', 'failed', 'force_db', 'no_es', 'tdd')


def run_tests(name="live", flags='', args=''):
    with build_venv(name):
        docker_exec("py.test %s src/olympia %s" % (flags, args))


@task
def tdd(name="live", args=''):
    """to run the entire test suite, but stop on the first error"""
    run_tests(name, "-x --pdb", args)


@task
def run_all(name="live", args=''):
    """to run the entire test suite"""
    run_tests(name, args=args)


@task
def es(name="live", args=''):
    """to run the ES tests"""
    run_tests(name, "-m es_tests", args)


@task
def failed(name="live", args=''):
    """to rerun the failed tests from the previous run"""
    run_tests(name, "--lf", args)


@task
def force_db(name="live", args=''):
    """to run the entire test suite with a new database"""
    run_tests(name, "--create-db", args)


@task
def no_es(name="live", args=''):
    """to run all but the ES tests"""
    run_tests(name, "-m 'no es_tests'", args)
