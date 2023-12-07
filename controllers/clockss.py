from app_modules.clockss import CLOCKSS_UPLOAD
import os

is_admin = auth.has_membership(role="administrator")


@auth.requires(is_admin)
def post_form():
    article_id = request.vars.article_id
    article = db.t_articles[article_id]
    recomm = db.get_last_recomm(article)

    clockss = CLOCKSS_UPLOAD(db, request, article)
    if not article_id:   return error("article_id: no such parameter")
    if not article:      return error("article: no such article")
    if not recomm :      return error("article: no recommendation yet")
    if not recomm.recommendation_title:
        return error("recommendation: no title (not recommended)")
    controller = "clockss"
    disabled = False
    message = H4("This article is yet to be uploaded to Clockss, review the pdf to ensure details are correct, you can go back to edit metadata if any is missing.", 
                _class="alert alert-warning", cr2br="true")

    pdf_exists = db(db.t_pdf.recommendation_id == recomm.id).select(db.t_pdf.pdf).last() 
    if pdf_exists:
        filename = pdf_exists.pdf
        controller = "default"
        disabled = True
        message = H4("This article has been uploaded to Clockss", _class="alert alert-info", cr2br="true")
    else:
        filename = clockss.build_pdf()
    
    file_url = (URL(controller, "stream_pdf", args=filename))
    url = URL(c="manager", f="recommendations", vars=dict(articleId=recomm.article_id), user_signature=True)
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
        attachments_dir, _ = clockss.init_dir()
        save_pdf_to_db(recomm, attachments_dir, f"{_}.pdf")
        clockss.build_xml()
        # # clockss.send_to_clockss()
        session.flash = T("Successfully Uploaded to Clockss")
        redirect(url)

    response.flash = None
    response.view = "default/myLayout.html"
    return dict(
        form=form,
        titleIcon="export",
        pageTitle="Clockss Upload",
    )


@auth.requires(is_admin)
def error(message):
    response.view = "default/myLayout.html"
    return dict(
        form=PRE(message),
        titleIcon="envelope",
        pageTitle="Clockss post error",
    )


def stream_pdf():
    filename = request.args[0]
    folder = filename[:-4]
    attachments_dir = os.path.join(request.folder, "clockss", folder)
    file_to_download = os.path.join(attachments_dir, filename)
    return response.stream(file_to_download)

def save_pdf_to_db(recomm, directory, filename):
    pdf_id = db.t_pdf.insert(recommendation_id=recomm.id, pdf=filename)
    pdf = db.t_pdf[pdf_id]
    file_to_upload = os.path.join(directory, filename)
    data = open(file_to_upload, 'rb')
    data = data.read()
    filename = current.db.t_pdf.pdf.store(data, filename)
    pdf.update_record(pdf=filename, pdf_data=data)
