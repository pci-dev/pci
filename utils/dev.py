# -*- coding: utf-8 -*-

from subprocess import Popen, PIPE, STDOUT
import shlex

from gluon.custom_import import track_changes
track_changes(True)  # reimport module if changed; disable in production


_items = [
    "log",
    "status",
    "update",
    "force",
    "uploads",
    "db",
]


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


def db():
    scripts = _run("sh -c 'ls updates/*.sql 2>/dev/null'").strip().split()
    if scripts:
        return "<br>\n" .join([
            '<a href="db_exec?script='+f+'">'+f+'</a>'
                for f in scripts ])
    else:
        return "updates: no sql files"


def db_exec():
    db = DAL(AppConfig().get("db.uri"))
    script = request.vars.script
    sql = _run("cat " + script)
    out = ["executing: " + script]
    try:
        res = db.executesql(sql)
    except Exception as e:
        res = [ e ]
    out += [str(_) for _ in res] if res else ["no output"]

    return "<pre>\n" + "\n".join(out) + "\n</pre>"


def sh():
    scripts = _run("sh -c 'ls updates/*.sh 2>/dev/null'").strip().split()
    if scripts:
        return "<br>\n" .join([
            '<a href="sh_exec?script='+f+'">'+f+'</a>'
                for f in scripts ])
    else:
        return "updates: no sh files"


def sh_exec():
    script = request.vars.script
    return _shell("sh " + script)


def version():
    opt = "--decorate --decorate-refs-exclude remotes/origin/*"
    return _shell(f"git log {opt} --oneline HEAD -1")


def _curr_branch():
    return _run("git rev-parse --abbrev-ref HEAD").strip()


def uploads():
    cmd = """sh -c "cd ..; du -hs PCI*/uploads | sed 's:/uploads::'" """
    return _shell(cmd)


def index():
    if not request.env.path_info.endswith("/"): # menu needs a trailing /
        redirect(URL(' '))

    return "\n".join([
        _menu(_items),
        log(),
    ])


def _menu(items):
    return " ".join(['<a href="%s">[%s]</a>' % (x,x) for x in items])


def _shell(command):
    return "<pre>\n%s</pre>" % _run(command)


def _run(command):
  try:
    return "".join(
        Popen(
            shlex.split(command),
            cwd=request.folder,
            stdout=PIPE,
            stderr=STDOUT,
            encoding="utf-8",
        )
        .stdout
        .readlines()
    )
  except FileNotFoundError as error:
      return str(error)
  except Exception as error:
      return error.output
