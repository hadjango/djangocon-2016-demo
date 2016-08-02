Contains the uwsgi configuration files (`*.ini`) and wsgi files `*.py` for
simple wsgi applications that start on load.

<dl>
    <dt>stub.ini / stub.py</dt>
    <dd>
        A “hello world” wsgi application that is the initial upstream for
        nginx before `fab init` has been run.
    </dd>
    <dt>uwsgi_status.ini / uwsgi_status.py</dt>
    <dd>
        A very simple app, bound on port `:9999`, that merges the output of
        the various uwsgi stat sockets at `/var/run/uwsgi/*.stats` and combines
        that with information pulled from the process table (see
        `src/hadjango/uwsgi/wsgi.py`), outputing the result as json.
        This script returns the data that powers the uwsgi dashboard
        (at http://live.addons/uwsgi/).
    </dd>
</dl>
