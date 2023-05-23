from typing import Any, Dict, List, Union, cast
from gluon import current
from gluon.globals import Response, Request, Session
from gluon.html import DIV, FORM, IMG, INPUT, TAG, TEXTAREA, URL
from gluon.http import redirect
from pydal.objects import Row
from pydal.base import DAL

from app_modules.twitter import Twitter



db = cast(DAL, db)
response = cast(Response, response)
request = cast(Request, request)
session = cast(Session, session)

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

    twitter_client = Twitter(db)

    tweets_text: List[str] = []
    tweets_in_db = twitter_client.get_posts_from_db(article_id, recommendation.id)
    already_send = len(tweets_in_db) > 0

    if not already_send:
        tweets_text = twitter_client.generate_post(article, recommendation)
    else:
        for tweet in tweets_in_db:
            tweets_text.append(tweet.text_content)

    form = generate_form(tweets_text, not already_send)

    if not already_send and form.process().accepted:
        tweet_texts = get_tweets_text_from_form()
        error = twitter_client.send_post(article, recommendation, tweet_texts)

        if error:
            session.flash = current.T(f'Error sending post to Twitter: {error}')
            redirect(URL("twitter", f"post_form?article_id={article.id}"))
        else:
            redirect(URL(c='manager', f='recommendations', vars=dict(articleId=article_id), user_signature=True))
    else:
        response.view = 'default/myLayout.html'

        data = dict(
            form=form,
            pageTitle=get_twitter_icon(),
        )

        if not already_send:
            data['prevContent'] = get_information_message()
 
        return data


def get_tweets_text_from_form() -> List[str]:
    tweets_text: List[str] = []
    i = 0
    for i in range(NB_TEXTAREA):
        text = cast(str, request.vars[f'tweet_{i}'])
        if len(text.strip()) > 0:
            tweets_text.append(text)
    return tweets_text


def generate_form(tweets_text: List[str], show_submit: bool):
    inputs: List[TEXTAREA] = []
    style = 'width: 600px; height: 120px; margin-bottom: 10px; margin-left: auto; margin-right: auto'

    i = 0
    for i in range(len(tweets_text)):
        inputs.append(TEXTAREA(tweets_text[i], _name=f'tweet_{i}', _class='form-control', _maxlength=280, _style=style))
        i = i + 1

    if show_submit:
        while i <= NB_TEXTAREA - 1:
            inputs.append(TEXTAREA('', _name=f'tweet_{i}', _class='form-control', _maxlength=280, _style=style))
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
    

def get_information_message():
    return DIV(TAG(current.T("There are no tweets sent for this recommendation yet. The following tweets have been automatically generated.<br/>Edit tweets and click 'Send to Twitter'")), _class="alert alert-warning")


def get_twitter_icon():
    return DIV(IMG(_src=URL(c='static', f='images/twitter-logo.png'), _alt='Twitter logo', _style='height: 50px; width: 50px; margin-right: 10px'), TAG('Twitter'))
