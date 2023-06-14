from typing import Any, Dict, List, Union, cast
from gluon import current
from gluon.contrib.appconfig import AppConfig
from gluon.globals import Response, Request, Session
from gluon.html import DIV, FORM, IMG, INPUT, P, TAG, TEXTAREA, URL
from gluon.http import redirect
from gluon.tools import Auth
from models.article import Article
from models.recommendation import Recommendation
from pydal.base import DAL

from app_modules.mastodon import Mastodon

db = cast(DAL, current.db)
response = cast(Response, current.response)
request = cast(Request, current.request)
session = cast(Session, current.session)
auth = cast(Auth, current.auth)
config = AppConfig()

is_admin = auth.has_membership(role="administrator")

NB_TEXTAREA = 3

def index() -> Union[Dict[str, Any], None]: 
    request.function = 'post_form'
    return post_form()


@auth.requires(is_admin)
def post_form():

    article_id = cast(int, request.vars.article_id)
    article = Article.get_by_id(db, article_id)
    recommendation = cast(Recommendation, db.get_last_recomm(article))

    if not article:
        session.flash = current.T(f'No article found.')
        redirect(URL("mastodon", f"post_form?article_id={article_id}"))
        return

    mastodon_client = Mastodon(db)
    mastodon_instance_name = merge_instance_name(mastodon_client)

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
        try:
            mastodon_client.send_post(article_id, recommendation.id, toot_texts)
        except Exception as e:
            session.flash = current.T(f'Error sending post to {mastodon_instance_name}: {e}')
            redirect(URL("mastodon", f"post_form?article_id={article_id}"))
        
        session.flash = current.T(f'Post send to {mastodon_instance_name}')
        redirect(URL(c='manager', f='recommendations', vars=dict(articleId=article_id), user_signature=True))
    else:
        response.view = 'default/myLayout.html'

        data = dict(
            form=form,
            pageTitle=get_mastodon_icon(mastodon_instance_name),
        )

        if not already_send:
            data['prevContent'] = get_before_send_information_message(mastodon_client, mastodon_instance_name)
        else:
            data['prevContent'] = get_after_send_information_message(mastodon_client, mastodon_instance_name)
 
        return data

def merge_instance_name(mastodon_client: Mastodon):
    instance_name = ''

    if mastodon_client.has_mastodon_general_config():
        instance_name += mastodon_client.get_instance_name()
    
    if mastodon_client.has_mastodon_specific_config() and mastodon_client.get_instance_name(True) != instance_name:
        if (len(instance_name) > 0):
            instance_name += ' & '
        instance_name += mastodon_client.get_instance_name(True)
    
    return instance_name

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
    

def get_after_send_information_message(mastodon_client: Mastodon, mastodon_instance_name: str):
    message: str = current.T(f"The following post has already been sent and is online on {mastodon_instance_name}.")
    message = add_account_info_at_end(mastodon_client, message)
    return P(TAG(message), _class="alert alert-info", cr2br="true")


def get_before_send_information_message(mastodon_client: Mastodon, mastodon_instance_name: str):
    message: str = current.T(f"There are no toots sent for this recommendation yet.\nThe following toots have been automatically generated.\nEdit toots and click 'Send to {mastodon_instance_name}'")
    message = add_account_info_at_end(mastodon_client, message)
    return P(TAG(message), _class="alert alert-warning", cr2br="true")


def get_mastodon_icon(mastodon_instance_name: str):
    return DIV(IMG(_src=URL(c='static', f='images/mastodon-logo.svg'), _alt='Mastodon logo', _style='height: 50px; width: 50px; margin-right: 10px'), TAG(mastodon_instance_name))


def add_account_info_at_end(mastodon_client: Mastodon, message: str):
    general_mastodon_pseudo: str = f"{current.T('@PeerCommunityIn')} on {mastodon_client.get_instance_name()}"
    specific_mastodon_pseudo: Union[str, None] = cast(str, config.take('social.tweeter'))

    if mastodon_client.has_mastodon_general_config():
        message += f'\n\nGeneral account: {general_mastodon_pseudo}'

    if mastodon_client.has_mastodon_specific_config() and specific_mastodon_pseudo:
        specific_mastodon_pseudo += f' on {mastodon_client.get_instance_name(True)}'

        if not mastodon_client.has_mastodon_general_config():
            message += '\n'
        message += f'\nSpecific account: @{specific_mastodon_pseudo}'

    return message
