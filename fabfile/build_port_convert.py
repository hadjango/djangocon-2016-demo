#!/usr/bin/env python
"""Convert a build name (e.g. 'a', 'b', etc.) to a port number, or vice-versa"""
from __future__ import print_function

import os
import sys


START_PORT = 2000
PORT_INCREMENT = 10
MAX_PORT = 65535
MAX_PORT_NUMS = (MAX_PORT - START_PORT) // PORT_INCREMENT

NUM_TO_CHAR = dict([((i), chr(i + ord('a'))) for i in range(0, 26)])
CHAR_TO_NUM = dict(map(reversed, NUM_TO_CHAR.items()))


def base26_decode(string):
    num = 0
    i = 0
    while i < len(string):
        char = string[i]
        offset = 0
        if i == 0:
            offset = 1
        power = len(string) - i - 1
        num += (26 ** power) * (CHAR_TO_NUM[char] + offset)
        if offset:
            while power > 1:
                power -= 1
                num += 26 ** power
        i += 1
    return num - 1


def base26_encode(num):
    string = ''
    num += 1
    while num:
        num, val = divmod((num - 1), 26)
        string = "%s%s" % (NUM_TO_CHAR[val], string)
    return string


def port_to_build(port):
    if port < START_PORT:
        usage("Port number must be greater than or equal to %d" % START_PORT)
    if port > MAX_PORT:
        usage("Port number must be less than %d" % MAX_PORT)
    num, index = divmod((port - START_PORT), PORT_INCREMENT)
    return (base26_encode(num), index)


def build_to_port(name):
    if name[-1].isdigit():
        index = int(name[-1])
        name = name[:-1]
    else:
        index = 0

    num = base26_decode(name)
    port = START_PORT + (num * PORT_INCREMENT) + index
    return port


USAGE = """%(error)s
Usage: %(script_name)s [port|build_name [index]]

build_name  A string composed of lowercase letters, as part of the sequence
            a, b, c, ..., z, aa, ab, ac, ..., zz, aaa, ..., %(max_build_name)s
index       Optional (defaults to 0), an integer between 0 and %(max_index)s
            which is added to the port number for the build_name
port        An integer, greater than %(start)s, which is converted into a
            build_name and index.
""".strip()


def usage(error=""):
    if error:
        error = "ERROR: %s\n" % error
    script_name = os.path.basename(sys.argv[0])
    print(USAGE % {
        "script_name": script_name,
        "max_build_name": base26_encode(MAX_PORT_NUMS),
        "max_index": PORT_INCREMENT,
        "start": START_PORT,
        "error": error,
    })
    sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        usage()
    arg = sys.argv[-1]
    if arg.isdigit():
        print("%s %d" % port_to_build(int(arg)))
    elif len(arg) > 3:
        usage()
    else:
        print(build_to_port(arg))
