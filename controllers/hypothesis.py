from typing import Any, Dict, cast
from app_modules.hypothesis import Hypothesis
from gluon import current
from gluon.globals import Request, Response, Session
from gluon.html import DIV, FORM, INPUT, TAG, TEXTAREA, URL
from gluon.http import redirect
from gluon.tools import Auth
from models.article import Article
from pydal.base import DAL

db = cast(DAL, current.db)
response = cast(Response, current.response)
request = cast(Request, current.request)
session = cast(Session, current.session)
auth = cast(Auth, current.auth)

is_admin = auth.has_membership(role="administrator")

def index():
    request.function = "post_form"
    return post_form()


@auth.requires(is_admin)
def post_form():

    article_id = cast(int, request.vars.article_id)
    article = Article.get_by_id(article_id)

    if not article:
        session.flash = current.T(f'No article found.')
        redirect(URL("hypothesis", f"post_form?article_id={article_id}"))
        return

    hypothesis_client = Hypothesis(article)
    annotation = hypothesis_client.get_annotation()

    default_text = hypothesis_client.generate_annotation_text()
    annotation_text = annotation['text'] if annotation else default_text

    form = FORM(
            TEXTAREA(annotation_text, _name='annotation_text', _class='form-control'),
            INPUT(_type='submit')
        )

    if form.process().accepted:
        if annotation:
            annotation['text'] = request.vars.annotation_text
            hypothesis_client.update_annotation(annotation)
            session.flash = current.T('Annotation updated')
            redirect(URL(c="manager", f="recommendations", vars=dict(articleId=article_id), user_signature=True))
        else:
            article_url = hypothesis_client.get_url_from_doi()
            hypothesis_client.post_annotation_for_article(article_url, request.vars.annotation_text)
            session.flash = current.T('Annotation created')
            redirect(URL(c="manager", f="recommendations", vars=dict(articleId=article_id), user_signature=True))
    else:
        response.view = "default/myLayout.html"

        data: Dict[str, Any] = dict(
            form=form,
            titleIcon="book",
            pageTitle="Hypothes.is annotation",
        )

        if annotation:
            data['prevContent'] = get_anotation_already_send_information_message()
        else:
            data['prevContent'] = get_no_annotation_found_warning()

        return data


def get_anotation_already_send_information_message():
    return DIV(TAG(current.T('The annotation has already been sent. You can modify it directly from the following form.')), _class="alert alert-info")


def get_no_annotation_found_warning():
    return DIV(TAG(f"{current.T('No annotation found')}.<br/>{current.T('There is no Hypotes.is annotation for this article yet. The content below was automatically generated. You can edit it and send the annotation.')}"), _class="alert alert-warning")
