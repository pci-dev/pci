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

    users = db(db.auth_user.deleted==True)
    ret += ['', f"retrofitted users: {users.count()}", '']
    for u in users.select():
        ret += [f"{u.id}: {u.email} = {u.first_name}"]

    return "<pre>" + '\n'.join(ret) + "</pre>"


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

    user = db(db.auth_user.email==email).select().first()
    if user: return user

    return db.auth_user.insert(email=email, first_name=name,
                                deleted=True, last_name="(x)")
