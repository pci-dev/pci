# -*- coding: utf-8 -*-

import os
import tempfile
import shutil

from app_modules.helper import *

from controller_modules import admin_module
from app_modules import emailing
from app_modules import common_small_html

from gluon.contrib.appconfig import AppConfig

myconf = AppConfig(reload=True)



######################################################################################################################################################################
@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developer"))
def testMail():
    emailing.send_test_mail(auth.user_id)
    redirect(request.env.http_referer)


@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developer"))
def delete_trapped_emails():
    db(
        (db.mail_queue.sending_status == "in queue") &
        (db.mail_queue.sending_attempts > 20)
    ).delete()

    redirect(request.env.http_referer)


######################################################################################################################################################################
## (gab) note : Unused functions ?
######################################################################################################################################################################
@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developer"))
def resizeAllUserImages():
    for userId in db(db.auth_user.uploaded_picture != None).select(db.auth_user.id):
        common_small_html.makeUserThumbnail(userId, size=(150, 150))
    redirect(request.env.http_referer)


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developer"))
def resizeUserImages(ids):
    for userId in ids:
        common_small_html.makeUserThumbnail(userId, size=(150, 150))


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developer"))
def rec_as_pdf():
    if "articleId" in request.vars:
        articleId = request.vars["articleId"]
    elif "id" in request.vars:
        articleId = request.vars["id"]
    else:
        session.flash = T("Unavailable")
        redirect(URL('default','index'))
    if not articleId.isdigit():
        session.flash = T("Unavailable")
        redirect(URL('default','index'))

    tmpDir = tempfile.mkdtemp()
    cwd = os.getcwd()
    os.chdir(tmpDir)
    art = db.t_articles[articleId]
    withHistory = "withHistory" in request.vars
    latRec = admin_module.recommLatex(articleId, tmpDir, withHistory)
    texfile = "recomm.tex"
    with open(texfile, "w") as tmp:
        tmp.write(latRec)
        tmp.close()
    biber = myconf.take("latex.biber")
    pdflatex = myconf.take("latex.compiler")
    cmd = "%(pdflatex)s recomm ; %(biber)s recomm ; %(pdflatex)s recomm" % locals()
    os.system(cmd)
    pdffile = "recomm.pdf"
    if os.path.isfile(pdffile):
        with open(pdffile, "rb") as tmp:
            pdf = tmp.read()
            tmp.close()
        os.chdir(cwd)
        shutil.rmtree(tmpDir)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = 'inline; filename="{0}_recommendation.pdf"'.format(art.title)
        return pdf
    else:
        os.chdir(cwd)
        # shutil.rmtree(tmpDir) ## For further examination
        session.flash = T("Failed :-(")
        redirect(request.env.http_referer)


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developer"))
def fp_as_pdf():
    if "articleId" in request.vars:
        articleId = request.vars["articleId"]
    elif "id" in request.vars:
        articleId = request.vars["id"]
    else:
        session.flash = T("Unavailable")
        redirect(URL('default','index'))
    if not articleId.isdigit():
        session.flash = T("Unavailable")
        redirect(URL('default','index'))
    art = db.t_articles[articleId]
    latFP = admin_module.frontPageLatex(articleId)
    tmpDir = tempfile.mkdtemp()
    cwd = os.getcwd()
    os.chdir(tmpDir)
    texfile = "frontpage.tex"
    with open(texfile, "w") as tmp:
        tmp.write(latFP)
        tmp.close()
    biber = myconf.take("latex.biber")
    pdflatex = myconf.take("latex.compiler")
    cmd = "%(pdflatex)s frontpage ; %(biber)s frontpage ; %(pdflatex)s frontpage" % locals()
    os.system(cmd)
    pdffile = "frontpage.pdf"
    if os.path.isfile(pdffile):
        with open(pdffile, "rb") as tmp:
            pdf = tmp.read()
            tmp.close()
        os.chdir(cwd)
        shutil.rmtree(tmpDir)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = 'inline; filename="{0}_frontpage.pdf"'.format(art.title)
        return pdf
    else:
        os.chdir(cwd)
        shutil.rmtree(tmpDir)
        session.flash = T("Failed :-(")
        redirect(request.env.http_referer)

def toggle_shedule_mail_from_queue():
    if "emailId" in request.vars:
        emailId = request.vars["emailId"]
    else:
        session.flash = T("Unavailable")
        redirect(URL("admin", "mailing_queue", user_signature=True))

    email = db.mail_queue[emailId]
    email.removed_from_queue = not email.removed_from_queue
    email.update_record()
    redirect(request.env.http_referer)


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="manager"))
def edit_resend_auth():
    mailId = request.vars['mailId']
    articleId = request.vars['articleId']
    hashtag = request.vars['hashtag']
    urlFunction = request.vars['urlFunction']
    urlController = request.vars['urlController']
        
    if mailId is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)

    redirect(URL(c="admin", f="edit_and_resend_email", vars=dict(mailId=mailId, articleId=articleId, hashtag=hashtag, urlFunction=urlFunction, urlController=urlController)))
