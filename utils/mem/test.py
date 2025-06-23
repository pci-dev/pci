def index():
    return "test"

def mem():
    sep = "\n---\n"

    return PRE(
        cat("monitor-ram.sh.log"),
        sep,
        tac("wsgi-watch+reset.sh.log"),
        sep,
        tac("mem-watch+reset.sh.log"),
    )
    # files above are expected to be updated by *.sh helper scripts,
    # which all log in *.sh.log, and symlinked into uploads/

def cat(filename):
    return open(request.folder+"/uploads/"+filename).read()

def tac(filename):
    return "".join(list(reversed(
                open(request.folder+"/uploads/"+filename).readlines()
    )))
