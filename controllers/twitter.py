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

from app_modules.twitter import Twitter

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
        redirect(URL("twitter", f"post_form?article_id={article_id}"))
        return

    twitter_client = Twitter(db)

    tweets_text: List[str] = []
    tweets_in_db = twitter_client.get_posts_from_db(article_id, recommendation.id)
    already_send = len(tweets_in_db) > 0

    if not already_send:
        tweets_text = twitter_client.generate_post(db, article)
    else:
        for tweet in tweets_in_db:
            tweets_text.append(tweet.text_content)

    form = generate_form(tweets_text, not already_send, twitter_client.POST_MAX_LENGTH)

    if not already_send and form.process().accepted:
        tweet_texts = get_tweets_text_from_form()

        try:
            twitter_client.send_post(article_id, recommendation.id, tweet_texts)
        except Exception as e:
            session.flash = current.T(f'Error sending post to Twitter: {e}')
            redirect(URL("twitter", f"post_form?article_id={article_id}"))
        
        session.flash = current.T('Post send to Twitter')
        redirect(URL(c='manager', f='recommendations', vars=dict(articleId=article_id), user_signature=True))
    else:
        response.view = 'default/myLayout.html'

        data = dict(
            form=form,
            pageTitle=get_twitter_icon(),
        )

        if not already_send:
            data['prevContent'] = get_before_send_information_message(twitter_client)
        else:
            data['prevContent'] = get_after_send_information_message(twitter_client)
 
        return data


def get_tweets_text_from_form() -> List[str]:
    tweets_text: List[str] = []
    i = 0
    for i in range(NB_TEXTAREA):
        text = cast(str, request.vars[f'tweet_{i}'])
        if len(text.strip()) > 0:
            tweets_text.append(text)
    return tweets_text


def generate_form(tweets_text: List[str], show_submit: bool, max_length: int):
    inputs: List[TEXTAREA] = []
    style = 'width: 600px; height: 120px; margin-bottom: 10px; margin-left: auto; margin-right: auto'

    i = 0
    for i in range(len(tweets_text)):
        inputs.append(TEXTAREA(tweets_text[i], _name=f'tweet_{i}', _class='form-control', _maxlength=max_length, _style=style))
        i = i + 1

    if show_submit:
        while i <= NB_TEXTAREA - 1:
            inputs.append(TEXTAREA('', _name=f'tweet_{i}', _class='form-control', _maxlength=max_length, _style=style))
            i = i + 1

    form = None
    if show_submit:
        form = FORM(
            *inputs,
            INPUT(_value=current.T('Send to Twitter'), _type='submit', _style='margin-left: auto; margin-right: auto; display: inherit'))
    else:
        for textarea in inputs:
            textarea['_readonly'] = 'true'

        form = FORM(*inputs)

    return form


def get_after_send_information_message(twitter_client: Twitter):
    message: str = current.T(f"The following post has already been sent and is online on Twitter")
    message = add_account_names_at_end(twitter_client, message)
    return P(TAG(message), _class="alert alert-info")
  

def get_before_send_information_message(twitter_client: Twitter):
    message: str = current.T("There are no tweets sent for this recommendation yet. The following tweets have been automatically generated.<br/>Edit tweets and click 'Send to Twitter'")
    message = add_account_names_at_end(twitter_client, message)
    return P(TAG(message), _class="alert alert-warning")


def get_twitter_icon():
    return DIV(IMG(_src=URL(c='static', f='images/twitter-logo.png'), _alt='Twitter logo', _style='height: 50px; width: 50px; margin-right: 10px'), TAG('Twitter'))


def add_account_names_at_end(twitter_client: Twitter, message: str):
    general_twitter_pseudo: str = current.T('@PeerCommunityIn')
    specific_twitter_pseudo: Union[str, None] = config.take('social.tweeter')

    if twitter_client.has_general_twitter_config():
        message += f' with {general_twitter_pseudo}'
    if twitter_client.has_specific_twitter_config() and specific_twitter_pseudo:
        if twitter_client.has_general_twitter_config():
            message += f' and @{specific_twitter_pseudo}'
        else:
            message += f' with @{specific_twitter_pseudo}'

    return message
