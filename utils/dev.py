# -*- coding: utf-8 -*-

from subprocess import Popen, PIPE, STDOUT

from gluon.custom_import import track_changes
track_changes(True)  # reimport module if changed; disable in production


def index():
    if not request.env.path_info.endswith("/"): # menu needs a trailing /
        redirect(URL(' '))

    return "\n".join([
        _menu(),
        log(),
    ])


def log():
    return _shell("git log --decorate --graph --oneline -50")


def status():
    return _shell("git status")


def update():
    fetch = _shell("git fetch --prune")
    status = _shell("git status")
    merge = _shell("git merge")

    return fetch + status + merge


def force():
    fetch = _shell("git fetch")
    reset = _shell("git reset --hard origin/" + _curr_branch())

    return fetch + reset


def version():
    return _shell("git log --decorate --oneline HEAD -1")


def _curr_branch():
    return _run("git rev-parse --abbrev-ref HEAD").strip()


_items = [
    "log",
    "status",
    "update",
    "force",
]

def _menu(items=_items):
    return " ".join(['<a href="%s">[%s]</a>' % (x,x) for x in items])


def _shell(command):
    return "<pre>\n%s</pre>" % _run(command)

def _run(command):
    return "".join(
        Popen(
            command.split(" "),
            cwd=request.folder,
            stdout=PIPE,
            stderr=STDOUT,
            encoding="utf-8",
        )
        .stdout
        .readlines()
    )
