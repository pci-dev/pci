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
    mail_vars["gtuLink"] = URL("about", "gtu", scheme=True)
    mail_vars["aboutEthicsLink"] = URL("about", "ethics", scheme=True)
    mail_vars["helpGenericLink"] = URL("help", "help_generic", scheme=True)
    mail_vars["completeSubmissionLink"] = URL("user", "edit_my_article",
                vars=dict(articleId=articleId, key=request.vars.key),
    )
    mail_vars["cancelSubmissionLink"] = URL("coar", "cancel_submission",
                vars=dict(articleId=articleId, coarId=request.vars.coarId),
    )

    content = _page_text.format(**mail_vars)

    response.view = "default/myLayoutBot.html"
    pageTitle = "BEFORE COMPLETING YOUR SUBMISSION"
    customText = XML(content)

    return dict(pageTitle=pageTitle, customText=customText)


def cancel_submission():
    articleId = request.vars.articleId
    coarId = request.vars.coarId

    article = db.t_articles[articleId or None]

    if not article: fail(404, f"no article: {articleId}")
    if not article.coar_notification_id: fail(404, "no coar id for this submission")
    if not article.coar_notification_id == coarId: fail(404, "coar id does not match")
    if article.coar_notification_closed: fail(404, "coar submission already closed")

    article.status = "Cancelled"
    article.coar_notification_closed = True
    article.update_record()

    session.flash = f"Submission #{articleId} / coar-id {coarId} cancelled"
    redirect(URL("default", "index")) #request.home))


def fail(code, message):
    raise HTTP(code, message)


_page_text = """
<h2>Please read the following information attentively</h2>
<p>
You have just submitted your preprint to PCI via an open archive. <b>Before completing the submission process, please carefully check the following points</b>:
</p>
<ul>
<li>{appName} is a preprint reviewing service and <b>not a journal</b>,</li>
<li>If <b>positively evaluated</b> by {appName}, your preprint will be <b>publicly recommended</b> and you could then <b>transfer it for publication in the Peer Community Journal or submit it to a PCI-friendly journal</b>,</li>
<li>If your preprint contains <b>data, scripts</b> (e.g. for statistical analysis, like R scripts) <b>and/or codes</b> (e.g. codes for original programs or software), they <b>should be made available to reviewers</b> at submission. Data, scripts or codes must be carefully described such that another researcher can reuse them. If your preprint is eventually recommended, data and script should be made available to the readers either in the text or through a correctly versioned deposit in an open repository with a DOI or another permanent identifier (such as a SWHID of <a href="https://www.softwareheritage.org/" target="_blank">Software heritage</a>).</li>
<li>Your <b>preprint must not be published or under consideration for evaluation elsewhere</b> at the time of its submission to {appName}. If your preprint is sent out for review by {appName}, you are not permitted to submit it to a journal until the {appName} evaluation process has been completed. You cannot, therefore, submit your preprint to a journal before its rejection or recommendation by {appName},</li>
<li><b>You and your co-authors should have no financial conflict of interest</b> (see a definition <a href="{aboutEthicsLink}">here</a>) relating to the articles you submit. If you are unsure whether your article may be associated with financial conflicts of interest, please send an Email to contact@peercommunityin.org to ask for clarification.</li>
</ul>
<p>
<b>Please note that</b>:
</p>
<ul>
<li>It can take up to 20 days before a recommender decides to handle your preprint and therefore to send it out for peer-review.</li>
<li>The median time between submission and the recommender's decision based on the first round of peer-review is currently 50 days.</li>
<li>The evaluation of your preprint might take several rounds of review before the recommender take the final decision to reject or recommend your preprint. </li>
<li>Details about the evaluation & recommendation process can be found <a href="{helpGenericLink}">here</a>.</li>
</ul>
<p>
By clicking on the green button below, you confirm that you agree to comply with the <a href="{gtuLink}">General Terms of Use</a> and the <a href="{aboutEthicsLink}">code of conduct</a>.
</p>
<hr style="border-top: 1px solid #dddddd; margin: 15px 0px;">
<div style="width: 100%; text-align: center; margin-bottom: 25px;"><a href="{completeSubmissionLink}" style="text-decoration: none;"><span style="margin: 10px; font-size: 14px; font-weight: bold; color: white; padding: 5px 15px; border-radius: 5px; hyphens: none;background: #93c54b">Complete your submission</span></a><b></b><a href="{cancelSubmissionLink}" style="text-decoration: none;"><span style="margin: 10px; font-size: 14px; font-weight:bold; color: white; padding: 5px 15px; border-radius: 5px; hyphens: none;background: #f47c3c">Cancel your submission</span></a></div>
"""
