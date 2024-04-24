from app_modules import crossref
from app_modules.clockss import send_to_clockss

crossref.init_conf(db)

is_admin = auth.has_membership(role="administrator")

def index():
    request.function = "post_form" # zap header in layout.html
    return post_form()


@auth.requires(is_admin)

def post_form():
    article_id = request.vars.article_id

    article = db.t_articles[article_id]
    recomm = db.get_last_recomm(article)

    if not article_id:   return error("article_id: no such parameter")
    if not article:      return error("article: no such article")
    if not recomm :      return error("article: no recommendation yet")
    if not recomm.recommendation_title:
        return error("recommendation: no title (not recommended)")

    generated_xml = crossref.crossref_xml(recomm)

    form = SQLFORM.factory(
        Field("xml", label=T("Crossref XML"), type="text", default=generated_xml),
    )
    form.element(_type="submit")["_value"] = T("Send to Crossref & Clockss")
    form.element(_name="xml").attributes.update(dict(
        _style="""
            font-family:monospace;
            cursor:default;
            /*min-height: inherit;*/
        """,
        _rows=20,
    ))
    form.insert(0, PRE(get_crossref_status(recomm), _name="status"))

    if form.process(keepvalues=True).accepted:
        status = crossref.post_and_forget(recomm, form.vars.xml)
        if not status:
            send_to_clockss(article, recomm)

        form.element(_name="status", replace=PRE(status or "request sent"))

        form.element(_name="xml")["_disabled"] = 1
        url = URL("manager", f"recommendations?articleId={recomm.article_id}")
        form.element(_type="submit").attributes.update(dict(
            _value="Back",
            _onclick= f'window.location.replace("{url}"); return false;'))


    response.flash = None
    response.view = "default/myLayout.html"
    return dict(
        form=form,
        titleIcon="envelope",
        pageTitle="Crossref post form",
    )


@auth.requires(is_admin)

def get_status():
    recomm_id = request.vars.recomm_id

    try:
        recomm = db.t_recommendations[recomm_id]
        assert recomm
    except:
        return f"error: no such recomm_id={recomm_id}"

    status = crossref.get_status(recomm)
    return (
        3 if status.startswith("error:") else
        2 if crossref.QUEUED in status else
        1 if crossref.FAILED in status else
        0
    )


def get_crossref_status(recomm):
    status = crossref.get_status(recomm)
    if status.startswith("error:") \
    or crossref.QUEUED in status:
        return status

    if crossref.FAILED in status:
        return "error: " + crossref.FAILED + "\n\n" + status
    else:
        return "success"


def error(message):
    response.view = "default/myLayout.html"
    return dict(
        form=PRE(message),
        titleIcon="envelope",
        pageTitle="Crossref post error",
    )
