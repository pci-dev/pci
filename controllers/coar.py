def index():
    return DIV(
            A("COAR outbox", _href=URL("coar_notify", " ")),
            A("submit request", _href=URL("test_coar", " ")),
            BR(),
            A("complete submission", _href=URL("coar", "complete_submission",
                vars=dict(articleId="", key=""))),
            A("cancel submission", _href=URL("coar", "cancel_submission",
                vars=dict(articleId=""))),
            STYLE("a {display:block;}"),
    )

def complete_submission():
    articleId = request.vars.articleId

    return DIV(
            P("are you sure?"),
            A("Complete your submission", _href=URL("user", "edit_my_article",
                vars=dict(articleId=articleId, key=request.vars.key)),
            ),
            A("Cancel your submission", _href=URL("coar", "cancel_submission",
                vars=dict(articleId=articleId, coarId=request.vars.coarId)),
            ),
            STYLE("a {display:block;}"),
    )

def cancel_submission():
    articleId = request.vars.articleId
    coarId = request.vars.coarId

    article = db.t_articles[articleId or None]

    if not article: return f"no article: {articleId}"
    if not article.coar_notification_id: return "no coar id for this submission"
    if not article.coar_notification_id == coarId: return "coar id does not match"
    if article.coar_notification_closed: return "coar submission already closed"

    article.status = "Cancelled"
    article.coar_notification_closed = True
    article.update_record()

    session.flash = f"Submission #{articleId} / coar-id {coarId} cancelled"
    redirect(URL("default", "index")) #request.home))
