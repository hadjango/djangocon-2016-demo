#!/usr/bin/env python

import sys
import re
import errno
import glob
import socket
import json
import logging

import psutil


logging.basicConfig()
logger = logging.getLogger()

re_procname = re.compile(r"(?i)"
    r"uwsgi (?P<type>(?:worker|master))"
    r"(?: (?P<worker_num>\d+))? "
    r"<(?P<build>[^\.]+)>"
    r"(?: \[(?P<deploy_tag>[^\]]+)\])?")


class UwsgiProcess(object):

    def __init__(self, pinfo):
        self.pid = pinfo['pid']
        self.status = pinfo['status']
        self.name = pinfo['cmdline'][0]
        self.create_time = pinfo['create_time']
        m = re_procname.match(self.name)
        if not m:
            raise Exception("Bad uwsgi process name")
        matches = m.groupdict()
        self.is_master = matches['type'] == 'master'
        if self.is_master:
            self.workers = []
        else:
            self.worker_num = int(matches['worker_num'])
            self.ppid = pinfo['ppid']
            self.deploy_tag = matches['deploy_tag']
        self.build = matches['build']


def get_uwsgi_procs():
    procs = {}
    for proc in psutil.process_iter():
        try:
            pinfo = proc.as_dict(
                attrs=['pid', 'ppid', 'name', 'cmdline', 'create_time', 'status'])
        except psutil.NoSuchProcess:
            pass
        else:
            if not len(pinfo['cmdline']):
                continue
            if pinfo['cmdline'][0].startswith('u') and pinfo['ppid'] != 1:
                if re_procname.match(pinfo['cmdline'][0]):
                    procs[pinfo['pid']] = UwsgiProcess(pinfo)

    stat_sock_files = glob.glob('/code/deploy/run/*.stats')
    for stat_sock_file in stat_sock_files:
        js = ''
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(stat_sock_file)

            while True:
                d = s.recv(4096)
                if len(d) < 1:
                    break
                js += d.decode('utf-8')
        except IOError as e:
            if e.errno == errno.ECONNREFUSED:
                logger.error("Connection refused to socket %s" % stat_sock_file)
            elif e.errno != errno.EINTR:
                raise
            continue
        except:
            raise Exception("Unable to get uwsgi statistics for socket %s"
                % stat_sock_file)

        raw_stats = json.loads(js)
        if raw_stats['pid'] not in procs:
            continue

        workers = raw_stats.pop('workers')

        master_proc = procs[raw_stats['pid']]
        master_proc.status = 'active'
        master_proc.__dict__.update(raw_stats)

        for worker in workers:
            pid = worker['pid']
            if pid in procs:
                uwsgi_worker = procs.pop(pid)
                uwsgi_worker.__dict__.update(worker)
                master_proc.workers.append(uwsgi_worker.__dict__)
                master_proc.deploy_tag = uwsgi_worker.deploy_tag

    for pid in reversed(sorted(procs.keys())):
        proc = procs[pid]
        if not proc.is_master and proc.ppid in procs:
            procs[proc.ppid].workers.append(procs.pop(pid).__dict__)

    build_data = {}
    for pid in reversed(sorted(procs.keys())):
        proc = procs[pid]
        build = proc.build
        if build not in build_data:
            build_data[build] = []

        build_data[build].append(proc.__dict__)

    data = []
    for build in sorted(build_data.keys()):
        data.append({
            "name": build,
            "processes": build_data[build],
        })

    return {
        "configs": data
    }


def application(environ, start_response):
    status = '200 OK'
    output = json.dumps(get_uwsgi_procs())
    headers = [
        ('Content-Type', 'application/json'),
        ('Content-Length', str(len(output)))
    ]
    start_response(status, headers)
    return [output]


if __name__ == '__main__':
    sys.stdout.write(json.dumps(get_uwsgi_procs()))
