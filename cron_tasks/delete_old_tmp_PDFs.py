import os
import time

current_time = time.time()

from gluon.contrib.appconfig import AppConfig

myconf = AppConfig(reload=True)
DELETE_PDF_DELAY = float(myconf.get("config.delete_tmp_pdf", default=24))  # in hours;

current_time = time.time()

# this code is based on : https://stackoverflow.com/a/65007150
for dirpath, _, filenames in os.walk(os.path.join(os.path.dirname(__file__), "../tmp/attachments")):
    for f in filenames:
        fileWithPath = os.path.abspath(os.path.join(dirpath, f))
        creation_time = os.path.getctime(fileWithPath)
        # Check if file is a pdf file
        if fileWithPath.endswith(".pdf"):
            # Check if date is older than delay
            if (current_time - creation_time) // (DELETE_PDF_DELAY * 3600) >= 1:
                os.unlink(fileWithPath)
                print("{} removed".format(fileWithPath))
                print("\n")

