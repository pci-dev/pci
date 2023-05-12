from app_modules.hypothesis import Hypothesis
from gluon import current
from app_modules.common_tools import generate_recommendation_doi

is_admin = auth.has_membership(role="administrator")

def index():
    request.function = "post_form"
    return post_form()


@auth.requires(is_admin)
def post_form():

    article_id = request.vars.article_id
    article = db.t_articles[article_id]

    hypothesis_client = Hypothesis()
    annotation = hypothesis_client.get_annotation(article.doi)

    default_text = f"{current.T('No annotation found')}.\n\n***{current.T('Generated annotation')}***\n\n{hypothesis_client.generate_annotation_text(article)}"
    annotation_text = annotation['text'] if annotation else default_text

    form = FORM(
            TEXTAREA(annotation_text, _name='annotation_text', _class='form-control'),
            INPUT(_type='submit')
        )

    if form.process().accepted:
        if annotation:
            annotation['text'] = request.vars.annotation_text
            update_response = hypothesis_client.update_annotation(annotation)
            redirect(URL(c="manager", f="recommendations", vars=dict(articleId=article_id), user_signature=True))
        else:
            article_url = hypothesis_client.get_url_from_doi(article.doi)
            hypothesis_client.post_annotation_for_article(article_url, request.vars.annotation_text)
            redirect(URL(c="manager", f="recommendations", vars=dict(articleId=article_id), user_signature=True))
    else:
        response.view = "default/myLayout.html"

        return dict(
            form=form,
            titleIcon="book",
            pageTitle="Hypothes.is annotation",
        )