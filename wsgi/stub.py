#!/usr/bin/env python
"""
A very simple wsgi application, used for the initial upstream before the
environments have been initialized.
"""

html = """<!DOCTYPE html>
<html>
<head>
<title>High Availability Django Demo</title>
<style type="text/css">
html {
    font-family: -apple-system, BlinkMacSystemFont, Roboto, "Helvetica Neue", Helvetica, sans-serif;
}
body {
    font-size: 18px;
    background: #fff;
    margin: 3em 5em;
}
pre {
    display: inline-block;
    padding: 1em;
}
pre, code {
    font-family: SFMono, Consolas, Menlo, Monaco, monospace;
    background: #eaeaea;
}
h1 {
    font-size: 1.5em;
    color: #333;
    margin-bottom: 2em;
}
</style>
</head>
<body>
<h1>Welcome to the High Availability Django Demo!</h1>
<p>To continue, run:</p>
<pre><code>fab init</code></pre>
<p>from the root of the checked out repository.
</body>
</html>"""


def application(environ, start_response):
    status = '200 OK'
    headers = [
        ('Content-Type', 'text/html'),
        ('Content-Length', str(len(html))),
    ]
    start_response(status, headers)
    return [html]
