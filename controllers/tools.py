# -*- coding: utf-8 -*-

import re
import copy
import tempfile
from datetime import datetime, timedelta
import glob
import os

# sudo pip install tweepy
# import tweepy

import codecs
from gluon.contrib.markdown import WIKI

from app_modules.helper import *
from imported_modules.html2text import *

from gluon.contrib.appconfig import AppConfig

myconf = AppConfig(reload=True)
pdf_max_size = int(myconf.take("config.pdf_max_size")) or 5

@auth.requires(auth.has_membership(role="manager") or auth.has_membership(role="administrator") or auth.has_membership(role="developper"))
def convert_pdf_to_markdown():
    response.view = "default/myLayout.html"

    form = SQLFORM.factory(Field("up_file", label=T("PDF File:"), type="upload", uploadfolder="uploads", requires=[IS_LENGTH(pdf_max_size * 1048576, error_message='The file size is over ' + str(pdf_max_size) + 'MB.'), IS_UPLOAD_FILENAME(extension="pdf")]), upload=URL("download"))
    customText = None
    if form.accepts(request.vars, formname="form"):
        f = request.vars["up_file"]
        # create temp file from in-memory file contents
        ff = tempfile.NamedTemporaryFile(delete=False, suffix=f.filename)
        # print("ff.name:"), ff.name
        ff.write(f.value)
        ff.close()  # file is not immediately deleted because we used delete=False
        cmd = 'pdftohtml -enc UTF-8 -noframes "%s"' % (ff.name)
        print(cmd)
        os.system(cmd)
        hf_name = ff.name.replace(".pdf", ".html")
        # Cleans output a bit
        cmd = "sed -i -e 's/&#160;/ /g' \"%s\"" % (hf_name)
        print(cmd)
        os.system(cmd)  # remove stupid whitechars
        cmd = "sed -i -e 's#<hr/># #g' \"%s\"" % (hf_name)
        print(cmd)
        os.system(cmd)  # remove page breaks
        cmd = "sed -i -re 's#<br/>([A-Za-z0-9])# \\1#g' \"%s\"" % (hf_name)
        print(cmd)
        os.system(cmd)  # remove line breaks
        # Try to convert html -> Markdown using Python library html2text
        try:
            with codecs.open(hf_name, "r", encoding="utf-8") as myHtmlFile:
                myHtml = myHtmlFile.read()
                customText = html2text.html2text(myHtml)
                print('html2text successed on file "%s"' % (hf_name))
        # if fails fallback to pandoc
        except Exception as e:
            print(str(e))
            print('html2text failed on file "%s", switch to pandoc' % (hf_name))
            cmd = 'pandoc --smart --normalize --columns=9999 -t markdown "%s"' % (hf_name)
            with os.popen(cmd) as messages:
                customText = []
                for m in messages:
                    customText.append(m)
                customText = "\n".join(customText)
        # Keep tmp tidy!
        map(os.unlink, glob.glob(ff.name.replace(".pdf", "*")))
    # If any text to be displayed, add it as an editable field in the form
    if customText:
        # form[0][0][0].append(HR())
        form[0].append(DIV(TEXTAREA(value=XML(customText), _class="pci-converted-pdf-area"), _class="form-group"))

    return dict(form=form, pageTitle=getTitle(request, auth, db, "#ConvertPDFTitle"), pageHelp=getHelp(request, auth, db, "#ConvertPDFComments"),)
