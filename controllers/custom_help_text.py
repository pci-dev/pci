# -*- coding: utf-8 -*-

import re
from gluon.custom_import import track_changes

track_changes(True)  # reimport module if changed; disable in production
from gluon.contrib.markdown import WIKI

from app_modules.helper import *

csv = True  # export allowed
expClass = dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)


@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developper"))
def help_texts():
    response.view = "default/myLayout.html"

    if session.back:
        redirect_url = session.back
    else:
        redirect_url = URL()
    db.help_texts.lang.writable = False
    db.help_texts.hashtag.writable = auth.has_membership(role="developper")
    db.help_texts.contents.represent = lambda text, row: WIKI(text or "")
    db.help_texts._id.readable = False
    db.help_texts._id.writable = False
    grid = SQLFORM.grid(
        db.help_texts,
        create=auth.has_membership(role="developper"),
        deletable=False,
        paginate=100,
        maxtextlength=4096,
        csv=csv,
        exportclasses=expClass,
        orderby=db.help_texts.hashtag,
    )
    if grid.update_form and grid.update_form.process().accepted:
        if redirect_url:
            redirect(redirect_url)
        session.back = None
    else:
        session.back = request.env.http_referer
    return dict(
        grid=grid,
        pageTitle=getTitle(request, auth, db, "#HelpTextTitle"),
        customText=getText(request, auth, db, "#HelpTextText"),
        pageHelp=getHelp(request, auth, db, "#AdministrateHelpTexts"),
    )


@auth.requires(auth.has_membership(role="developper"))
def transfer_help():
    response.view = "default/myLayout.html"
    db.help_texts.truncate()
    texts = dbHelp((dbHelp.help_texts.language == "default") & (dbHelp.help_texts.contents != "") & (dbHelp.help_texts.contents != None)).select()
    for t in texts:
        db.help_texts.insert(lang="default", hashtag=t.hashtag, contents=t.contents)
    return None

