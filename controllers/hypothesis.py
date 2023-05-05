from app_modules.hypothesis import Hypothesis
from gluon import current

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

    annotation_text = annotation['text'] if annotation else current.T('No annotation found')

    form = FORM(
            TEXTAREA(annotation_text, _name='annotation_text', _class='form-control'),
            INPUT(_type='submit')
        )

    if form.process().accepted:
        annotation['text'] = request.vars.annotation_text
        update_response = hypothesis_client.update_annotation(annotation)
        redirect(URL(c="manager", f="recommendations", vars=dict(articleId=article_id), user_signature=True))
    else:
        response.view = "default/myLayout.html"

        return dict(
            form=form,
            titleIcon="book",
            pageTitle="Hypothes.is annotation",
        )