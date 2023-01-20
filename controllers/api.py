# -*- coding: utf-8 -*-

from app_modules.utils import run
from app_modules.utils import json

response.headers['Content-Type'] = 'application/json'


def index():
    response.headers['Content-Type'] = 'text/html'

    return menu([
        "pcis",
        "version",
        "issn",
    ])


def version():
    opt = "--decorate --decorate-refs='refs/tags/*'"
    fmt = "--pretty='%H/%D'"
    ver = run(f"git log {opt} {fmt} HEAD -1").strip().split('/')

    return json({
        "version": { "hash": ver[0], "tag": ver[1] }
    })


def pcis():
    host = read_confs("host", cleanup="s:[.].*::")
    desc = read_confs("description", cleanup="s:Peer Community [iI]n ::")

    return json({
        host[i]: desc[i] for i,_ in enumerate(host)
    })


def issn():
    return json({
        "issn": db.config[1].issn
    })


# internals

def read_confs(key, cleanup=""):
    return run(f"""sh -c "
        cd ..
        cat PCI*/private/appconfig.ini \\
        | egrep '^{key} = ' \\
        | sed  's:{key} = ::; {cleanup}'
        " """
        ).strip().split('\n')


def menu(items):
    return "<br>\n".join(map(str, [
        A(x, _href=URL(x)) for x in items
    ]))
