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

    from app_modules.emailing_tools import getMailCommonVars
    mail_vars = getMailCommonVars()
    mail_vars["aboutEthicsLink"] = URL("about", "ethics", scheme=True)
    mail_vars["helpGenericLink"] = URL("help", "help_generic", scheme=True)
    mail_vars["completeSubmissionLink"] = URL("user", "edit_my_article",
                vars=dict(articleId=articleId, key=request.vars.key),
    )
    mail_vars["cancelSubmissionLink"] = URL("coar", "cancel_submission",
                vars=dict(articleId=articleId, coarId=request.vars.coarId),
    )

    hashtag_template = "#UserCompleteSubmissionCOAR"

    from app_modules.emailing_tools import getMailTemplateHashtag, replaceMailVars
    import re
    mail_template = getMailTemplateHashtag(db, hashtag_template)["content"]
    mail_template = re.sub(r"<p>Dear .*Welcome on board!</p>", "", mail_template, flags=re.MULTILINE)
    content = replaceMailVars(mail_template, mail_vars)

    response.view = "default/myLayoutBot.html"
    pageTitle = "BEFORE COMPLETING YOUR SUBMISSION"
    customText = XML(content)

    return dict(pageTitle=pageTitle, customText=customText)


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
