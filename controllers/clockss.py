from typing import cast
from app_modules.clockss import ClockssUpload
import os

from gluon.globals import Request
from gluon.html import DIV, FORM, H4, IFRAME, INPUT, PRE, URL
from gluon.http import redirect
from models.recommendation import Recommendation
from models.pdf import PDF
from pydal import DAL

from models.article import Article

is_admin = bool(auth.has_membership(role="administrator"))
db = cast(DAL, db)
request = cast(Request, request)


@auth.requires(is_admin)
def post_form():
    article_id = int(request.vars.article_id)
    if not article_id:
        return error("article_id: no such parameter")
    
    article = Article.get_by_id(article_id)
    if not article:
        return error("article: no such article")
    
    recommendation = Article.get_last_recommendation(article_id)
    if not recommendation :
        return error("article: no recommendation yet")
    if not recommendation.recommendation_title:
        return error("recommendation: no title (not recommended)")

    clockss = ClockssUpload(article)

    controller = "clockss"
    disabled: bool = False
    message = H4("This article is yet to be uploaded to Clockss, review the pdf to ensure details are correct, you can go back to edit metadata if any is missing.", 
                _class="alert alert-warning", cr2br="true")

    pdf = Recommendation.get_last_pdf(recommendation.id)
    if pdf:
        filename = pdf.pdf
        controller = "default"
        disabled = True
        message = H4("This article has been uploaded to Clockss", _class="alert alert-info", cr2br="true")
    else:
        filename = clockss.build_pdf()
    
    file_url = cast(str, URL(controller, "stream_pdf", args=filename))
    url = cast(str, URL(c="manager", f="recommendations", vars=dict(articleId=recommendation.article_id), user_signature=True))
    form = FORM(
                DIV(
                    message,                             
                    IFRAME(_src=file_url, _class="web2py_grid", _style="height:1000px;")
                ),
                DIV(INPUT(_type="button", _value=T("Go back"), _class="btn btn-default", 
                          _onclick=f'window.location.replace("{url}");'),
                    INPUT(_type="submit", _value=T("Send to clockss"), _name="accepted", _class="btn btn-success", _disabled=disabled),
                _style="text-align:center;",)
            )
        
    if form.process().accepted:
        if disabled:
            session.flash = 'Already uploaded to Clockss'
            redirect(url)
        else:
            try:
                attachments_dir= clockss.attachments_dir
                PDF.save_pdf_to_db(recommendation, attachments_dir, filename)
                clockss.compile_and_send()
                session.flash = T("Successfully uploaded to Clockss")
            except Exception as e:
                session.flash = f"Error to upload to Clockss: {e}"
                PDF.delete_pdf_to_db(recommendation.id)

            redirect(url)

    response.flash = None
    response.view = "default/myLayout.html"
    return dict(
        form=form,
        titleIcon="export",
        pageTitle="Clockss Upload",
    )


@auth.requires(is_admin)
def error(message: str):
    response.view = "default/myLayout.html"
    return dict(
        form=PRE(message),
        titleIcon="envelope",
        pageTitle="Clockss post error",
    )


def stream_pdf():
    filename = str(request.args[0])
    folder = filename[:-4]
    attachments_dir = os.path.join(str(request.folder), "clockss", folder)
    file_to_download = os.path.join(attachments_dir, filename)
    return response.stream(file_to_download)
