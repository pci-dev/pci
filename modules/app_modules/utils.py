from subprocess import Popen, SubprocessError
from subprocess import PIPE, STDOUT
import shlex

import json as _json

from gluon import current


def json(arg):
    return _json.dumps(arg, indent=4)


def run(command):
    try:
        with Popen(
                shlex.split(command),
                cwd=current.request.folder,
                stdout=PIPE,
                stderr=STDOUT,
                encoding="utf-8",
            ) \
        as p: return "".join(p
            .stdout
            .readlines()
        )
    except FileNotFoundError as error:
        return str(error)
    except SubprocessError as error:
        return str(error.output)


def auto_reload():
    from gluon.custom_import import track_changes
    track_changes(True)


def all_pci_db_uris():
    return map(str.strip,
    run("""sh -c '
        cat ../PCI*/private/appconfig.ini \
        | grep psyco \
        | sed "s/^[^=]*=//"
    '"""
    ).strip().split('\n'))
