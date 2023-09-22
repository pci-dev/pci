# -*- coding: utf-8 -*-

import re
from gluon.custom_import import track_changes

track_changes(True)  # reimport module if changed; disable in production
from gluon.contrib.markdown import WIKI

from app_modules.helper import *
from controller_modules import adjust_grid

csv = True  # export allowed
expClass = dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)


@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developer"))
def help_texts():
    response.view = "default/myLayout.html"

    if session.back:
        redirect_url = session.back
    else:
        redirect_url = URL()
    db.help_texts.lang.writable = False
    db.help_texts.hashtag.writable = auth.has_membership(role="developer")
    db.help_texts.contents.represent = lambda text, row: DIV(WIKI(text or "", safe_mode=False), _class="fade-transparent-text-300")
    db.help_texts._id.readable = False
    db.help_texts._id.writable = False
    db.help_texts.lang.readable = False

    original_grid = SQLFORM.grid(
        db.help_texts,
        create=auth.has_membership(role="developer"),
        deletable=False,
        paginate=100,
        maxtextlength=4096,
        csv=csv,
        exportclasses=expClass,
        orderby=db.help_texts.hashtag,
    )

    remove_options = ['help_texts.lang']
    grid = adjust_grid.adjust_grid_basic(original_grid, 'help_texts', remove_options) \
            if len(request.args) == 1 else original_grid

    if grid.update_form and grid.update_form.process().accepted:
        if redirect_url:
            redirect(redirect_url)
        session.back = None
    else:
        session.back = request.env.http_referer
    return dict(
        titleIcon="question-sign",
        pageTitle=getTitle(request, auth, db, "#HelpTextTitle"),
        pageHelp=getHelp(request, auth, db, "#AdministrateHelpTexts"),
        customText=getText(request, auth, db, "#HelpTextText"),
        grid=grid,
    )


@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developer"))
def mail_templates():
    response.view = "default/myLayout.html"

    if session.back:
        redirect_url = session.back
    else:
        redirect_url = URL()

    db.mail_templates.lang.writable = False
    db.mail_templates.hashtag.writable = auth.has_membership(role="developer") or auth.has_membership(role="administrator")

    db.mail_templates.subject.readable = False
    db.mail_templates.subject.writable = True

    db.mail_templates.contents.represent = lambda text, row: DIV(P(B(row.subject or "")), DIV(WIKI(text or "", safe_mode=False), _class="fade-transparent-text-300"))

    db.mail_templates._id.readable = False
    db.mail_templates._id.writable = False


    original_grid = SQLFORM.grid(
            db.mail_templates,
            details=False,
            editable=True,
            create=True,
            deletable=auth.has_membership(role="developer"),
            paginate=100,
            maxtextlength=4096,
            csv=False,
            exportclasses=expClass,
            orderby=~db.mail_templates.id,
    )

    # options to be removed from the search dropdown:
    remove_options = ['mail_templates.lang']

    # the grid is adjusted after creation to adhere to our requirements
    grid = adjust_grid.adjust_grid_basic(original_grid, 'templates', remove_options) \
            if len(request.args) == 1 else original_grid

    if grid.update_form and grid.update_form.process().accepted:
        if redirect_url:
            redirect(redirect_url)
        session.back = None
    else:
        session.back = request.env.http_referer

    return dict(titleIcon="envelope", pageTitle=getTitle(request, auth, db, "#MailTemplatesTitle"), customText=getText(request, auth, db, "#MailTemplatesText"), grid=grid,)


@auth.requires(auth.has_membership(role="developer"))
def transfer_help():
    response.view = "default/myLayout.html"
    db.help_texts.truncate()
    texts = dbHelp((dbHelp.help_texts.language == "default") & (dbHelp.help_texts.contents != "") & (dbHelp.help_texts.contents != None)).select()
    for t in texts:
        db.help_texts.insert(lang="default", hashtag=t.hashtag, contents=t.contents)
    return None

