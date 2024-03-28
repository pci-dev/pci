def index():
    return translated_articles()


def translated_articles():
    fully_translated = db(
            (db.t_articles.translated_title != None)
        &   (db.t_articles.translated_abstract != None)
        &   (db.t_articles.translated_keywords != None)
    )
    not_translated = db(
            (db.t_articles.translated_title == None)
        &   (db.t_articles.translated_abstract == None)
        &   (db.t_articles.translated_keywords == None)
    )
    _id = db.t_articles.id
    partly_translated = db(
            ~_id.belongs(not_translated.select(_id))
        &   ~_id.belongs(fully_translated.select(_id))
    )
    show = {
            "fully": fully_translated,
            "partly": partly_translated,
            "not": not_translated,
    }
    what = request.vars.show
    what = what if what in show else "partly"
    link = lambda what: f"<a href='?show={what}'>{what}</a>"
    txt = [
            f"{link(what):{30+len(what)}} {show[what].count():15}"
                for what in show
    ]
    txt += [
            f"-------------------------",
            f"showing {what} translated",
            f"-------------------------",
    ]
    txt += [
            f"{art.id}: {art.title}"
                for art in show[what].select(
                    orderby=db.t_articles.id,)
    ]

    return "<pre>\n" + "\n".join(txt) + "\n</pre>"
