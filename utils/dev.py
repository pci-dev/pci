# -*- coding: utf-8 -*-

from subprocess import Popen, PIPE, STDOUT
import shlex
import json

from gluon.custom_import import track_changes
track_changes(True)  # reimport module if changed; disable in production


_items = [
    "log",
    "status",
    "update",
    "force",
    "reload_w2p",
    "uploads",
    "pcis",
    "db",
]


def log():
    return _shell("git log --decorate --graph --oneline -50")


def log_():
    opt = "--merges --decorate --decorate-refs=refs/tags/*"
    fmt = "--pretty='%s\t%d'"
    return _shell(f"git log {opt} {fmt} --since 'one year'") + "[...]"


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


def reload_w2p():
    _run("touch ../../wsgihandler.py")
    return index()


def db():
    scripts = _run("sh -c 'cd updates; ls *.sql 2>/dev/null'").strip().split()
    if scripts:
        return "<br>\n" .join([
            '<a href="db_exec?script='+f+'">'+f+'</a>'
                for f in scripts ])
    else:
        return "updates: no sql files"


def db_exec():
    db = DAL(AppConfig().get("db.uri"))
    script = request.vars.script.split("/")[-1]
    sql = _run("cat updates/" + script)
    out = ["executing: " + script]
    try:
        res = db.executesql(sql)
    except Exception as e:
        res = [ e ]
    out += [str(_) for _ in res] if res else ["no output"]

    return "<pre>\n" + "\n".join(out) + "\n</pre>"


def version():
    opt = "--decorate --decorate-refs-exclude remotes/origin/*"
    return _shell(f"git log {opt} --oneline HEAD -1")


def _curr_branch():
    return _run("git rev-parse --abbrev-ref HEAD").strip()


def uploads():
    cmd = """sh -c "cd ..; du -hs PCI*/uploads | sed 's:/uploads::'" """
    return _shell(cmd)


def pcis():
    host = read_confs("host", cleanup="s:[.].*::")
    desc = read_confs("description", cleanup="s:Peer Community [iI]n ::")

    response.headers['Content-Type'] = 'application/json'
    return _json({
        host[i]: desc[i] for i,_ in enumerate(host)
    })


def read_confs(key, cleanup=""):
    return _run(f"""sh -c "
        cd ..
        cat PCI*/private/appconfig.ini \\
        | egrep '^{key} = ' \\
        | sed  's:{key} = ::; {cleanup}'
        " """
        ).strip().split('\n')


def _json(arg):
    return json.dumps(arg, indent=4)


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
