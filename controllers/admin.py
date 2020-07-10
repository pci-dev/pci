# -*- coding: utf-8 -*-

import re
import copy
import random
import os
import tempfile
import shutil

# sudo pip install tweepy
# import tweepy
from gluon.contrib.markdown import WIKI


from app_modules.emailing import *
from app_modules.helper import *

from controller_modules import admin_module
from app_modules import common_small_html

from gluon.contrib.markmin.markmin2latex import render, latex_escape

from gluon.contrib.appconfig import AppConfig

myconf = AppConfig(reload=True)


# frequently used constants
csv = False  # no export allowed
expClass = dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
trgmLimit = myconf.take("config.trgm_limit") or 0.4


######################################################################################################################################################################
## Menu Routes
######################################################################################################################################################################
@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developper"))
def list_users():
    selectable = None
    links = None
    create = True  # allow create buttons
    if len(request.args) == 0 or (len(request.args) == 1 and request.args[0] == "auth_user"):
        selectable = [(T("Add role 'recommender' to selected users"), lambda ids: [admin_module.set_as_recommender(ids, auth, db)], "btn btn-info pci-admin")]
        links = [dict(header=T("Roles"), body=lambda row: admin_module.mkRoles(row, auth, db))]
    db.auth_user.registration_datetime.readable = True

    # db.auth_user.uploaded_picture.represent = (
    #     lambda text, row: (IMG(_src=URL("default", "download", args=row.uploaded_picture), _width=100))
    #     if (row.uploaded_picture is not None and row.uploaded_picture != "")
    #     else (IMG(_src=URL(r=request, c="static", f="images/default_user.png"), _width=100))
    # )

    db.auth_user.email.represent = lambda text, row: A(text, _href="mailto:%s" % text)

    fields = [
        db.auth_user.id,
        db.auth_user.registration_key,
        # db.auth_user.uploaded_picture,
        db.auth_user.first_name,
        db.auth_user.last_name,
        db.auth_user.email,
        # db.auth_user.registration_datetime,
        # db.auth_user.laboratory,
        # db.auth_user.institution,
        # db.auth_user.city,
        # db.auth_user.country,
        # db.auth_user.thematics,
        # db.auth_user.alerts,
        db.auth_membership.user_id,
        db.auth_membership.group_id,
        db.t_articles.id,
        db.t_articles.title,
        db.t_articles.anonymous_submission,
        db.t_articles.authors,
        db.t_articles.already_published,
        db.t_articles.status,
        db.t_recommendations.id,
        db.t_recommendations.article_id,
        db.t_recommendations.recommender_id,
        db.t_recommendations.recommendation_state,
        db.t_recommendations.recommendation_title,
        db.t_reviews.id,
        db.t_reviews.recommendation_id,
        db.t_reviews.review_state,
        db.t_reviews.review,
        db.t_press_reviews.id,
        db.t_press_reviews.recommendation_id,
        db.t_comments.id,
        db.t_comments.article_id,
        db.t_comments.user_comment,
        db.t_comments.comment_datetime,
        db.t_comments.parent_id,
    ]
    db.auth_user._id.readable = True
    db.auth_user._id.represent = lambda i, row: common_small_html.mkUserId(auth, db, i, linked=True)
    db.t_reviews.recommendation_id.label = T("Article DOI")
    db.t_articles.anonymous_submission.label = T("Anonymous submission")
    db.t_articles.anonymous_submission.represent = lambda text, row: common_small_html.mkAnonymousMask(auth, db, text)
    db.t_articles.already_published.represent = lambda text, row: common_small_html.mkJournalImg(auth, db, text)
    db.auth_user.registration_key.represent = lambda text, row: SPAN(text, _class="pci-blocked") if (text == "blocked" or text == "disabled") else text
    grid = SQLFORM.smartgrid(
        db.auth_user,
        fields=fields,
        linked_tables=["auth_user", "auth_membership", "t_articles", "t_recommendations", "t_reviews", "t_press_reviews", "t_comments"],
        links=links,
        csv=False,
        exportclasses=dict(auth_user=expClass, auth_membership=expClass),
        editable=dict(auth_user=True, auth_membership=False),
        details=dict(auth_user=True, auth_membership=False),
        searchable=dict(auth_user=True, auth_membership=False),
        create=dict(auth_user=create, auth_membership=create, t_articles=create, t_recommendations=create, t_reviews=create, t_press_reviews=create, t_comments=create),
        selectable=selectable,
        maxtextlength=250,
        paginate=25,
    )
    if "auth_membership.user_id" in request.args:
        if grid and grid.element(_title="Add record to database"):
            grid.element(_title="Add record to database")[0] = T("Add role")
            # grid.element(_title="Add record to database")['_title'] = T('Manually add new round of recommendation. Expert use!!')

    response.view = "default/myLayout.html"
    return dict(
        pageTitle=getTitle(request, auth, db, "#AdministrateUsersTitle"),
        pageHelp=getHelp(request, auth, db, "#AdministrateUsers"),
        customText=getText(request, auth, db, "#AdministrateUsersText"),
        grid=grid
    )


######################################################################################################################################################################
# Prepares lists of email addresses by role
@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developper"))
def mailing_lists():
    response.view = "default/myLayout.html"

    myContents = DIV()
    myContents.append(H1(T("Roles:")))
    contentDiv = DIV(_style="padding-left:32px;")
    for theRole in db(db.auth_group.role).select():
        contentDiv.append(H2(theRole.role))
        emails = []
        query = db((db.auth_user._id == db.auth_membership.user_id) & (db.auth_membership.group_id == theRole.id)).select(db.auth_user.email, orderby=db.auth_user.email)
        for user in query:
            if user.email:
                emails.append(user.email)
        list_emails = ", ".join(emails)
        contentDiv.append(list_emails)
    myContents.append(contentDiv)

    # Special searches: authors
    myContents.append(H1(T("Authors:")))
    emails = []
    query = db((db.auth_user._id == db.t_articles.user_id)).select(db.auth_user.email, groupby=db.auth_user.email)
    for user in query:
        if user.email:
            emails.append(user.email)
    list_emails = ", ".join(emails)
    myContents.append(list_emails)

    # Special searches: reviewers
    myContents.append(H1(T("Reviewers:")))
    emails = []
    query = db((db.auth_user._id == db.t_reviews.reviewer_id) & (db.t_reviews.review_state.belongs(["Under consideration", "Completed"]))).select(
        db.auth_user.email, groupby=db.auth_user.email
    )
    for user in query:
        if user.email:
            emails.append(user.email)
    list_emails = ", ".join(emails)
    myContents.append(list_emails)

    # Other users
    myContents.append(H1(T("Others:")))
    emails = []
    query = db.executesql(
        """SELECT DISTINCT auth_user.email FROM auth_user 
				WHERE auth_user.id NOT IN (SELECT DISTINCT auth_membership.user_id FROM auth_membership) 
				AND auth_user.id NOT IN (SELECT DISTINCT t_articles.user_id FROM t_articles WHERE t_articles.user_id IS NOT NULL) 
				AND auth_user.id NOT IN (SELECT DISTINCT t_reviews.reviewer_id FROM t_reviews WHERE t_reviews.reviewer_id IS NOT NULL AND review_state IN ('Under consideration', 'Completed')) 
				AND auth_user.email IS NOT NULL;"""
    )
    for user_email in query:
        emails.append(user_email[0])
    list_emails = ", ".join(emails)
    myContents.append(list_emails)

    return dict(
        customText=getText(request, auth, db, "#EmailsListsUsersText"),
        pageTitle=getTitle(request, auth, db, "#EmailsListsUsersTitle"),
        pageHelp=getHelp(request, auth, db, "#EmailsListsUsers"),
        content=myContents,
        grid="",
    )


######################################################################################################################################################################
# Display the list of thematic fields
# Can be modified only by developper and administrator
@auth.requires_login()
def thematics_list():
    response.view = "default/myLayout.html"

    write_auth = auth.has_membership("administrator") or auth.has_membership("developper")
    db.t_thematics._id.readable = False
    grid = SQLFORM.grid(
        db.t_thematics,
        details=False,
        editable=True,
        deletable=write_auth,
        create=write_auth,
        searchable=False,
        maxtextlength=250,
        paginate=100,
        csv=csv,
        exportclasses=expClass,
        fields=[db.t_thematics.keyword],
        orderby=db.t_thematics.keyword,
    )
    return dict(
        pageHelp=getHelp(request, auth, db, "#AdministrateThematicFields"),
        customText=getText(request, auth, db, "#AdministrateThematicFieldsText"),
        pageTitle=getTitle(request, auth, db, "#AdministrateThematicFieldsTitle"),
        grid=grid,
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager") or auth.has_membership(role="administrator") or auth.has_membership(role="developper"))
def allRecommCitations():
    response.view = "default/myLayout.html"

    allRecomms = db(
        (db.t_articles.status == "Recommended") & (db.t_recommendations.article_id == db.t_articles.id) & (db.t_recommendations.recommendation_state == "Recommended")
    ).select(db.t_recommendations.ALL, orderby=db.t_recommendations.last_change)
    grid = OL()
    for myRecomm in allRecomms:
        grid.append(LI(common_small_html.mkRecommCitation(auth, db, myRecomm), BR(), B("Recommends: "), common_small_html.mkArticleCitation(auth, db, myRecomm), P()))
    return dict(
        grid=grid,
        pageTitle=getTitle(request, auth, db, "#allRecommCitationsTextTitle"),
        customText=getText(request, auth, db, "#allRecommCitationsTextText"),
        pageHelp=getHelp(request, auth, db, "#allRecommCitationsHelpTexts"),
    )


######################################################################################################################################################################
# Lists article status
# writable by developpers only!!
@auth.requires(
    auth.has_membership(role="recommender") or auth.has_membership(role="manager") or auth.has_membership(role="administrator") or auth.has_membership(role="developper")
)
def article_status():
    response.view = "default/myLayout.html"

    write_auth = auth.has_membership("developper")
    db.t_status_article._id.label = T("Coded representation")
    db.t_status_article._id.represent = lambda text, row: common_small_html.mkStatusDiv(auth, db, row.status)
    db.t_status_article.status.writable = write_auth
    grid = SQLFORM.grid(
        db.t_status_article,
        searchable=False,
        create=write_auth,
        details=False,
        deletable=write_auth,
        editable=write_auth,
        maxtextlength=500,
        paginate=100,
        csv=csv,
        exportclasses=expClass,
        fields=[db.t_status_article.status, db.t_status_article._id, db.t_status_article.priority_level, db.t_status_article.color_class, db.t_status_article.explaination],
        orderby=db.t_status_article.priority_level,
    )
    common_small_html.mkStatusArticles(db)
    return dict(
        pageHelp=getHelp(request, auth, db, "#AdministrateArticleStatus"),
        customText=getText(request, auth, db, "#AdministrateArticleStatusText"),
        pageTitle=getTitle(request, auth, db, "#AdministrateArticleStatusTitle"),
        grid=grid,
    )
    
######################################################################################################################################################################
# PDF management
@auth.requires(auth.has_membership(role="manager") or auth.has_membership(role="administrator") or auth.has_membership(role="developper"))
def manage_pdf():
    response.view = "default/myLayout.html"

    # Do the complex query in full sql and return valid ids
    myList = []
    myQy = db.executesql(
        'SELECT r.id FROM (t_recommendations AS r JOIN t_articles AS a ON (r.article_id=a.id)) LEFT JOIN t_pdf AS p ON r.id=p.recommendation_id WHERE a.status IN (\'Recommended\', \'Pre-recommended\') AND r.recommendation_state LIKE \'Recommended\';'
    )

    for q in myQy:
        myList.append(q[0])
    mySet = db((db.t_recommendations.id.belongs(myList)))
    db.t_recommendations._format = lambda row: admin_module.mkRecommendationFormat2(auth, db, row)
    db.t_pdf.recommendation_id.requires = IS_IN_DB(mySet, "t_recommendations.id", db.t_recommendations._format, orderby=db.t_recommendations.id)
    db.t_pdf.recommendation_id.widget = SQLFORM.widgets.radio.widget
    grid = SQLFORM.grid(
        db.t_pdf,
        details=False,
        editable=True,
        deletable=True,
        create=True,
        searchable=False,
        maxtextlength=250,
        paginate=20,
        csv=csv,
        exportclasses=expClass,
        fields=[db.t_pdf.recommendation_id, db.t_pdf.pdf],
        orderby=~db.t_pdf.id,
    )
    return dict(customText=getText(request, auth, db, "#AdminPdfText"), pageTitle=getTitle(request, auth, db, "#AdminPdfTitle"), grid=grid,)


######################################################################################################################################################################
# Supports management
@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developper"))
def manage_supports():
    response.view = "default/myLayout.html"

    grid = SQLFORM.grid(
        db.t_supports,
        details=False,
        editable=True,
        deletable=True,
        create=True,
        searchable=False,
        maxtextlength=512,
        paginate=20,
        csv=csv,
        exportclasses=expClass,
        orderby=db.t_supports.support_rank,
    )
    return dict(customText=getText(request, auth, db, "#AdminSupportsText"), pageTitle=getTitle(request, auth, db, "#AdminSupportsTitle"), grid=grid,)


######################################################################################################################################################################
# Resources management
@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developper"))
def manage_resources():
    response.view = "default/myLayout.html"

    grid = SQLFORM.grid(
        db.t_resources,
        details=False,
        editable=True,
        deletable=True,
        create=True,
        searchable=False,
        maxtextlength=512,
        paginate=20,
        csv=csv,
        exportclasses=expClass,
        orderby=db.t_resources.resource_rank,
    )
    return dict(customText=getText(request, auth, db, "#AdminResourcesText"), pageTitle=getTitle(request, auth, db, "#AdminResourcesTitle"), grid=grid,)


@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developper"))
def recap_reviews():
    response.view = "default/myLayout.html"

    runId = str(random.randint(1, 10000))
    db.executesql("DROP VIEW IF EXISTS _v_%(runId)s;" % locals())
    db.executesql(
        """CREATE OR REPLACE VIEW  _v_%(runId)s AS
	WITH
	recom AS (
		SELECT r.article_id, 
			array_to_string(array_agg(DISTINCT coalesce(ru.first_name,'')||' '||coalesce(ru.last_name,'')), ', ') AS recommenders,
			max(recommendation_doi) AS recommendation_doi
		FROM t_recommendations AS r
		LEFT JOIN auth_user AS ru ON r.recommender_id = ru.id
		GROUP BY r.article_id
	)
	, corecom AS (
		SELECT r.article_id,
			array_to_string(array_agg(DISTINCT coalesce(cru.first_name,'')||' '||coalesce(cru.last_name,'')), ', ') AS co_recommenders
		FROM t_press_reviews AS co
		LEFT JOIN auth_user AS cru ON co.contributor_id = cru.id
		LEFT JOIN t_recommendations AS r ON co.recommendation_id = r.id
		GROUP BY r.article_id
	)
	, recomms0 AS (
		SELECT r.article_id, r.id AS recom_id,
			rank() OVER (PARTITION BY r.article_id ORDER BY r.id) AS recomm_round, 
			r.recommendation_state AS decision, 
			r.recommendation_timestamp::date AS decision_start,
			r.last_change::date AS decision_last_change
		FROM t_recommendations AS r
	)
	, reviews AS (
		SELECT article_id, w.recommendation_id AS recomm_id, recomm_round,
			to_char(rank() OVER (PARTITION BY w.recommendation_id ORDER BY w.id), '00') AS reviewer_num,
			CASE WHEN anonymously THEN '[ANON] ' ELSE '' END||coalesce(wu.first_name,'')||' '||coalesce(wu.last_name,'') AS reviewer
		FROM t_reviews AS w
		LEFT JOIN auth_user AS wu ON w.reviewer_id = wu.id
		LEFT JOIN recomms0 ON w.recommendation_id = recomms0.recom_id
		WHERE w.review_state NOT IN ('Pending', 'Declined', 'Cancelled')
		UNION ALL
		SELECT article_id, recom_id AS recomm_id, recomm_round,
			'decision'::varchar AS reviewer_num,
			decision
		FROM recomms0
		UNION ALL
		SELECT article_id, recom_id AS recomm_id, recomm_round,
			'00_start'::varchar AS reviewer_num,
			decision_start::varchar
		FROM recomms0
		UNION ALL
		SELECT article_id, recom_id AS recomm_id, recomm_round,
			'last_change'::varchar AS reviewer_num,
			decision_last_change::varchar
		FROM recomms0
		UNION ALL
		SELECT article_id, recom_id AS recomm_id, recomm_round,
			'supp_info'::varchar AS reviewer_num,
			''::varchar
		FROM recomms0
	)
	SELECT  CASE WHEN a.already_published THEN 'Postprint' ELSE 'Preprint' END AS type_article,
		a.title, a.doi AS article_doi, a.id AS article_id,
		coalesce(au.first_name,'')||' '||coalesce(au.last_name,'') AS submitter,
		a.upload_timestamp::date AS submission,
		''::varchar AS first_outcome,
		coalesce(recom.recommenders, '') AS recommenders,
		coalesce(corecom.co_recommenders, '') AS co_recommenders,
		a.status AS article_status, a.last_status_change::date AS article_status_last_change,
		coalesce(recom.recommendation_doi, '') AS recommendation_doi,
		''::varchar AS recommendation_info,
		coalesce(reviews.recomm_round, 1) AS recomm_round, 
		coalesce(reviews.reviewer_num, ' 01') AS reviewer_num, 
		coalesce(reviews.reviewer, '') AS reviewer
	FROM t_articles AS a
	LEFT JOIN auth_user AS au ON a.user_id = au.id
	LEFT JOIN recom ON recom.article_id = a.id
	LEFT JOIN corecom ON corecom.article_id = a.id
	LEFT JOIN reviews ON reviews.article_id = a.id
	ORDER BY a.id DESC, recomm_round ASC;"""
        % locals()
    )

    db.executesql(
        """SELECT colpivot('_t_%(runId)s', 
		'SELECT * FROM _v_%(runId)s', 
		array['type_article', 'title', 'article_doi', 'article_id', 'submitter', 'submission', 'first_outcome', 'recommenders', 'co_recommenders', 'article_status', 'article_status_last_change', 'recommendation_doi', 'recommendation_info'],
		array['recomm_round', 'reviewer_num'], 
		'#.reviewer',
		null
	);"""
        % locals()
    )

    # Get columns as header
    head = TR()
    cols = db.executesql("""SELECT column_name FROM information_schema.columns WHERE table_name  LIKE '_t_%(runId)s'  ORDER BY ordinal_position;""" % locals())
    pat = re.compile(r"'(\d+)', '(.*)'")
    iCol = 0
    revwCols = []
    for cc in cols:
        c = cc[0]
        patMatch = pat.match(c)
        if patMatch:
            revRound = patMatch.group(1)
            field = patMatch.group(2)
            rn = re.match(r"^ ?(\d+)$", field)
            if field == "00_start":
                field = "Start"
            elif rn:
                rwNum = int(rn.group(1))
                field = "Rev._%s" % (rwNum)
                revwCols.append(iCol)
            c = SPAN(SPAN("ROUND_#" + revRound + " "), SPAN(field))
        head.append(TH(c))
        if iCol in revwCols:
            head.append(TH(c, SPAN(" quality")))
            head.append(TH(c, SPAN(" info")))
        iCol += 1
    grid = TABLE(_class="pci-AdminReviewsSynthesis")
    grid.append(head)

    resu = db.executesql("""SELECT * FROM _t_%(runId)s ORDER BY article_id;""" % locals())
    for r in resu:
        row = TR()
        iCol = 0
        for v in r:
            row.append(TD(v or ""))
            if iCol in revwCols:
                row.append(TD(""))
                row.append(TD(""))
            iCol += 1
        grid.append(row)

    db.executesql("DROP VIEW IF EXISTS _v_%(runId)s;" % locals())
    db.executesql("DROP TABLE IF EXISTS _t_%(runId)s;" % locals())
    return dict(
        customText=getText(request, auth, db, "#AdminRecapReviews"),
        pageTitle=getTitle(request, auth, db, "#AdminRecapReviewsTitle"),
        grid=DIV(grid, _style="width:100%; overflow-x:scroll;"),
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developper"))
def rec_as_latex():
    response.view = "default/info.html"

    if "articleId" in request.vars:
        articleId = request.vars["articleId"]
    elif "id" in request.vars:
        articleId = request.vars["id"]
    else:
        session.flash = T("Unavailable")
        redirect(URL("articles", "recommended_articles", user_signature=True))
    if not articleId.isdigit():
        session.flash = T("Unavailable")
        redirect(URL("articles", "recommended_articles", user_signature=True))

    withHistory = "withHistory" in request.vars
    bib = admin_module.recommBibtex(articleId)
    latFP = admin_module.frontPageLatex(articleId)
    latRec = admin_module.recommLatex(articleId, withHistory)
    message = DIV(H2("BibTex:"), PRE(bib), H2("Front page:"), PRE(latFP), H2("Recommendation:"), PRE(latRec),)
    return dict(message=message)


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developper"))
def testRedir():
    session.flash = "redirect!"
    url = URL("default", "index", user_signature=True)  # , scheme=scheme, host=host, port=port)
    redirect(url)

