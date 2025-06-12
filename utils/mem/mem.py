import tracemalloc
import os
import re

def index():
    return mem_snapshot()

def mem_watch():
    tracemalloc.start()

def mem_snapshot():
    response.headers.update({"Content-Type":"text/plain"})

    try:
        snapshot = tracemalloc.take_snapshot()
    except:
        tracemalloc.start()
        return "Mem tracing started.\nPlease reload page to see stats."

    top_stats = snapshot.statistics('lineno')
    top_stats.sort(key=lambda x: x.count, reverse=True)

    mem_proc = float(mem_use())
    mem_glob = float(mem_free())

    return "\n".join(
            [ str(stat) for stat in top_stats[:20]
                # if "connection" in stat.traceback[0].filename
            ]
        +   [ "",
            f"pid={os.getpid()} mem={mem_proc}% global={mem_glob}%",
            ]
    )

def mem_use():
    return os.popen(f"ps -o %mem= {os.getpid()}").readline().strip()


def mem_free():
    mem = os.popen("free").readlines()[1].strip()
    mem = re.split(" +", mem)

    return "{:.1f}".format(int(mem[2]) / int(mem[1]) * 100)
