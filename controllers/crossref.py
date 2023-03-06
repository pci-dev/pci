from app_modules import crossref

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
    form.element(_type="submit")["_value"] = T("Send to Crossref")
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

    status = crossref.wait_for_status(recomm)
    return (
        2 if status.find("error:")+1 else
        1 if '"Failure"' in status else
        0
    )


def get_crossref_status(recomm):
    status = crossref.get_status(recomm).text
    if status.find("error:")+1:
        return status

    error_str = 'record_diagnostic status="Failure"'
    if error_str in status:
        return "error: " + error_str + "\n\n" + status
    else:
        return "success"


def error(message):
    response.view = "default/myLayout.html"
    return dict(
        form=PRE(message),
        titleIcon="envelope",
        pageTitle="Crossref post error",
    )
