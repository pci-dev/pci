from typing import Any, Dict, List, Union
from gluon import current
from gluon.contrib.appconfig import AppConfig # type: ignore
from gluon.html import DIV, FORM, IMG, INPUT, P, TAG, TEXTAREA
from gluon.http import HTTP, redirect # type: ignore
from models.article import Article

from app_modules.bluesky import Bluesky
from app_modules.common_tools import URL

db = current.db
response = current.response
request = current.request
session = current.session
auth = current.auth
config = AppConfig()

is_admin = auth.has_membership(role="administrator")

NB_TEXTAREA = 3

def index() -> Union[Dict[str, Any], None]:
    request.function = 'post_form'
    return post_form()


@auth.requires(is_admin)
def post_form():

    article_id = int(request.vars.article_id)
    article = Article.get_by_id(article_id)
    if not article:
        raise HTTP(404, f"Article with id {article_id} not found")

    recommendation = Article.get_last_recommendation(article_id)
    if not recommendation:
        raise HTTP(404, f"Recommendation for article {article_id} not found")

    bluesky_client = Bluesky()

    posts_text: List[str] = []
    bluesky_posts_in_db = bluesky_client.get_posts_from_db(article_id, recommendation.id)
    already_send = len(bluesky_posts_in_db) > 0

    if not already_send:
        posts_text = bluesky_client.generate_post(article, recommendation)
    else:
        for bluesky_post in bluesky_posts_in_db:
            posts_text.append(bluesky_post.text_content)

    form = generate_form(posts_text, not already_send, bluesky_client.POST_MAX_LENGTH)

    if not already_send and form.process().accepted: # type: ignore
        post_texts = get_bluesky_text_from_form()

        try:
            bluesky_client.send_post(article_id, recommendation.id, post_texts)
        except Exception as e:
            session.flash = current.T(f'Error sending post to Bluesky: {e}')
            redirect(URL("blueksy", f"post_form?article_id={article_id}"))

        session.flash = current.T('Post send to Bluesky')
        redirect(URL(c='manager', f='recommendations', vars=dict(articleId=article_id), user_signature=True))
    else:
        response.view = 'default/myLayout.html'

        data = dict(
            form=form,
            pageTitle=get_bluesky_icon(),
        )

        if not already_send:
            data['prevContent'] = get_before_send_information_message(bluesky_client)
        else:
            data['prevContent'] = get_after_send_information_message(bluesky_client)

        return data


def get_bluesky_text_from_form() -> List[str]:
    posts_text: List[str] = []
    i = 0
    for i in range(NB_TEXTAREA):
        text = str(request.vars[f'bluesky_post_{i}'])
        if len(text.strip()) > 0:
            posts_text.append(text)
    return posts_text


def generate_form(bluesky_posts_text: List[str], show_submit: bool, max_length: int):
    inputs: List[TEXTAREA] = []
    style = 'width: 600px; height: 120px; margin-bottom: 10px; margin-left: auto; margin-right: auto'

    i = 0
    for i in range(len(bluesky_posts_text)):
        inputs.append(TEXTAREA(bluesky_posts_text[i], _name=f'bluesky_post_{i}', _class='form-control', _maxlength=max_length, _style=style))
        i = i + 1

    if show_submit:
        while i <= NB_TEXTAREA - 1:
            inputs.append(TEXTAREA('', _name=f'bluesky_post_{i}', _class='form-control', _maxlength=max_length, _style=style))
            i = i + 1

    form = None
    if show_submit:
        form = FORM(
            *inputs,
            INPUT(_value=current.T('Send to Bluesky'), _type='submit', _style='margin-left: auto; margin-right: auto; display: inherit'))
    else:
        for textarea in inputs:
            textarea['_readonly'] = 'true'

        form = FORM(*inputs)

    return form


def get_after_send_information_message(bluesky_client: Bluesky):
    message: str = current.T(f"The following post has already been sent and is online on Bluesky")
    message = add_account_names_at_end(bluesky_client, message)
    return P(TAG(message), _class="alert alert-info")


def get_before_send_information_message(bluesky_client: Bluesky):
    message: str = current.T("There are no posts sent for this recommendation yet. The following posts have been automatically generated.<br/>Edit posts and click 'Send to Bluesky'")
    message = add_account_names_at_end(bluesky_client, message)
    return P(TAG(message), _class="alert alert-warning")


def get_bluesky_icon():
    return DIV(IMG(_src=URL(c='static', f='images/bluesky.png'), _alt='Bluesky logo', _style='height: 50px; width: 50px; margin-right: 10px'), TAG("Bluesky"))


def add_account_names_at_end(bluesky_client: Bluesky, message: str):
    general_bluesky_pseudo: str = current.T('@peercomjournal.bsky.social')
    specific_bluesky_pseudo: Union[str, None] = config.get('social.bluesky')

    if bluesky_client.has_general_bluesky_config():
        message += f' with {general_bluesky_pseudo}'
    if bluesky_client.has_specific_bluesky_config() and specific_bluesky_pseudo:
        if bluesky_client.has_general_bluesky_config():
            message += f' and @{specific_bluesky_pseudo}'
        else:
            message += f' with @{specific_bluesky_pseudo}'

    return message
