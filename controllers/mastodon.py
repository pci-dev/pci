from typing import Any, Dict, List, Union, cast
from gluon import current
from gluon.globals import Response, Request, Session
from gluon.html import DIV, FORM, IMG, INPUT, TAG, TEXTAREA, URL
from gluon.http import redirect
from gluon.tools import Auth
from pydal.objects import Row
from pydal.base import DAL

from app_modules.mastodon import Mastodon

db = cast(DAL, current.db)
response = cast(Response, current.response)
request = cast(Request, current.request)
session = cast(Session, current.session)
auth = cast(Auth, current.auth)

is_admin = auth.has_membership(role="administrator")

NB_TEXTAREA = 3

def index() -> Union[Dict[str, Any], None]: 
    request.function = 'post_form'
    return post_form()


@auth.requires(is_admin)
def post_form():

    article_id = cast(int, request.vars.article_id)
    article = cast(Row, db.t_articles[article_id])
    recommendation = cast(Row, db.get_last_recomm(article))

    mastodon_client = Mastodon(db)
    mastodon_instance_name = mastodon_client.get_instance_name()

    toots_text: List[str] = []
    toots_in_db = mastodon_client.get_posts_from_db(article_id, recommendation.id)
    already_send = len(toots_in_db) > 0

    if not already_send:
        toots_text = mastodon_client.generate_post(article, recommendation)
    else:
        for toot in toots_in_db:
            toots_text.append(toot.text_content)

    form = generate_form(toots_text, not already_send, mastodon_instance_name, mastodon_client.POST_MAX_LENGTH)

    if not already_send and form.process().accepted:
        toot_texts = get_toots_text_from_form()
        error = mastodon_client.send_post(article_id, recommendation.id, toot_texts)
        if error:
            session.flash = current.T(f'Error sending post to {mastodon_instance_name}: {error}')
            redirect(URL("mastodon", f"post_form?article_id={article_id}"))
        else:
            session.flash = current.T(f'Post send to {mastodon_instance_name}')
            redirect(URL(c='manager', f='recommendations', vars=dict(articleId=article_id), user_signature=True))
    else:
        response.view = 'default/myLayout.html'

        data = dict(
            form=form,
            pageTitle=get_mastodon_icon(mastodon_instance_name),
        )

        if not already_send:
            data['prevContent'] = get_before_send_information_message(mastodon_instance_name)
        else:
            data['prevContent'] = get_after_send_information_message(mastodon_instance_name)
 
        return data


def get_toots_text_from_form() -> List[str]:
    toots_text: List[str] = []
    i = 0
    for i in range(NB_TEXTAREA):
        text = cast(str, request.vars[f'toot_{i}'])
        if len(text.strip()) > 0:
            toots_text.append(text)
    return toots_text


def generate_form(toots_text: List[str], show_submit: bool, mastodon_instance_name: str, max_length: int):
    inputs: List[TEXTAREA] = []
    style = 'width: 600px; height: 170px; margin-bottom: 10px; margin-left: auto; margin-right: auto'

    i = 0
    for i in range(len(toots_text)):
        inputs.append(TEXTAREA(toots_text[i], _name=f'toot_{i}', _class='form-control', _maxlength=max_length, _style=style))
        i = i + 1

    if show_submit:
        while i <= NB_TEXTAREA - 1:
            inputs.append(TEXTAREA('', _name=f'toot_{i}', _class='form-control', _maxlength=max_length, _style=style))
            i = i + 1

    form = None
    if show_submit:
        form = FORM(
            *inputs,
            INPUT(_value=current.T(f'Send to {mastodon_instance_name}'), _type='submit', _style='margin-left: auto; margin-right: auto; display: inherit'))
    else:
        for textarea in inputs:
            textarea['_readonly'] = 'true'

        form = FORM(*inputs)

    return form
    

def get_after_send_information_message(mastodon_instance_name: str):
    return DIV(TAG(current.T(f"The following post has already been sent and is online on {mastodon_instance_name}")), _class="alert alert-info")


def get_before_send_information_message(mastodon_instance_name: str):
    return DIV(TAG(current.T(f"There are no toots sent for this recommendation yet. The following toots have been automatically generated.<br/>Edit toots and click 'Send to {mastodon_instance_name}'")), _class="alert alert-warning")


def get_mastodon_icon(mastodon_instance_name: str):
    return DIV(IMG(_src=URL(c='static', f='images/mastodon-logo.svg'), _alt='Mastodon logo', _style='height: 50px; width: 50px; margin-right: 10px'), TAG(mastodon_instance_name))
