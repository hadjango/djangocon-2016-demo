import random

from django.conf import settings
from django.core.management.base import BaseCommand

import requests
from requests_futures.sessions import FuturesSession

from hadjango.build_port_convert import build_to_port


class Command(BaseCommand):
    """
    Command that primes processes/cache for a given build
    """

    help = 'Warms up processes/cache for a given host/port'

    def add_arguments(self, parser):
        parser.add_argument('--build', '-b', dest='build',
            default=settings.BUILD_NAME, help='Build to warm up: (a|b|c|...)')
        parser.add_argument('--concurrents', '-c', dest='concurrents',
            default='20', help='Number of concurrent requests to make')

    def handle(self, **options):
        server = "web"
        build = options['build']
        port = build_to_port(build)
        max_workers = int(options['concurrents'])

        session = FuturesSession(max_workers=max_workers)

        futures = []
        random_version = random.randint(0, 65535)
        for i in range(0, max_workers):
            version = '' if i == 0 else '?v=%d%d' % (i, random_version)
            futures.append(session.get('http://%(server)s:%(port)d/en-US/firefox/%(version)s' % {
                'server': server,
                'port': port,
                'version': version,
            }))

        for i, future in enumerate(futures):
            # wait for the response to complete
            try:
                response = future.result()
            except requests.ConnectionError:
                status = 'XXX'
                time = 0
            else:
                status = response.status_code
                time = int(round(response.elapsed.total_seconds() * 1000.0))
            self.stdout.write("%(server)s: (%(status)s) %(time)6d ms: worker %(i)s\n" % {
                'server': server,
                'status': status,
                'time': time,
                'i': i + 1,
            })

        self.stdout.write("Successfully warmed up.")
