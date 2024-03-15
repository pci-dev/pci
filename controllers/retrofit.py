def index():
    items = [
        (db.t_articles.submitter_details, "user_id"),
        (db.t_reviews.reviewer_details, "reviewer_id"),
        (db.t_recommendations.recommender_details, "recommender_id"),
        (db.t_press_reviews.contributor_details, "contributor_id"),
    ]
    ret = []
    for f in items:
        objects = db(f[0] != None).select()
        retrofit_users(objects, f[0], f[1])

        ret += [f"{f[0]}: {len(objects)}"]

    show_retrofited_users(ret)

    return "<pre>" + '\n'.join(ret) + "</pre>"


def show_retrofited_users(ret):
    users = db(db.auth_user.deleted==True)
    ret += ['', f"retrofitted users: {users.count()}", '']

    for u in users.select(orderby=db.auth_user.id):
        ret += [f"{u.id}: {u.laboratory} = {u.first_name}"]


def retrofit_users(items, source, target):
    for it in items:
        user = get_user(it[source])
        it.update_record(**{target: user.id})


def get_user(details_str):
    class no_user: id = None

    import re
    m = re.match("(.*) \[(.*)\]", details_str)

    if not m: return no_user
    name, email = m[1], m[2]
    if not email: return no_user

    user = db(db.auth_user.laboratory==email).select().first()
    if user: return user

    return db.auth_user.insert(laboratory=email, first_name=name,
                                email=None,
                                deleted=True, city="(x)")