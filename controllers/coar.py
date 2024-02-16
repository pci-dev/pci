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
                vars=dict(articleId=articleId)),
            ),
            STYLE("a {display:block;}"),
    )

def cancel_submission():
    articleId = request.vars.articleId

    return f"NIY: cancel article id={articleId}"
