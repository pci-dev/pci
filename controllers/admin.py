# -*- coding: utf-8 -*-

import re
import copy
import random
import os
import tempfile
import shutil
import datetime

# sudo pip install tweepy
# import tweepy
from gluon.contrib.markdown import WIKI

from app_modules.helper import *

from controller_modules import admin_module
from controller_modules import adjust_grid
from app_modules import common_small_html
from app_modules import common_tools
from app_modules import emailing_tools

from app_components import app_forms

from gluon.contrib.markmin.markmin2latex import render, latex_escape

from gluon.contrib.appconfig import AppConfig

myconf = AppConfig(reload=True)

# frequently used constants
csv = False  # no export allowed
expClass = dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)

pciRRactivated = myconf.get("config.registered_reports", default=False)

DEFAULT_DATE_FORMAT = common_tools.getDefaultDateFormat()

######################################################################################################################################################################
## Menu Routes
######################################################################################################################################################################
def index():
    return list_users()

@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developer"))
def list_users():
    selectable = None
    links = None
    create = True  # allow create buttons
    if len(request.args) == 0 or (len(request.args) == 1 and request.args[0] == "auth_user"):
        selectable = [
            (
                T("Add role 'recommender' to selected users"),
                lambda ids: [admin_module.set_as_recommender(ids, auth, db)],
                "btn btn-info pci-admin",
            )
        ]
        links = [dict(header=T("Roles"), body=lambda row: admin_module.mkRoles(row, auth, db))]

    db.auth_user.email.represent = lambda text, row: A(text, _href="mailto:%s" % text)

    db.auth_user.website.readable = False
    db.auth_user.registration_datetime.readable = True

    if len(request.args) == 1: # list/search view (i.e. not edit form)
        db.auth_user.thematics.requires = IS_IN_DB(db, db.t_thematics.keyword, "%(keyword)s", zero=None)
        db.auth_user.thematics.type = "string" # for advanced search dd, vs "list:string" in edit form

    if hasattr(request, 'raw_args') and request.raw_args and \
            'edit' in request.raw_args:
        user_id = [val for val in request.args if val.isdigit()]
        auth_query = db((db.auth_membership.user_id == next(iter(user_id), None)) & (db.auth_membership.group_id == db.auth_group._id) & (db.auth_group.role == "recommender")).select()

        if not auth_query:
            db.auth_user.email_options.readable = False
            db.auth_user.email_options.writable = False
            
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
        db.auth_user.thematics,
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

    if len(request.args) != 0:  # grid view
        fields += [
            db.auth_user.last_alert,
        ]

    db.auth_user._id.readable = True
    db.auth_user._id.represent = lambda i, row: common_small_html.mkUserId(auth, db, i, linked=True)
    db.t_reviews.recommendation_id.label = T("Article DOI")
    db.t_articles.anonymous_submission.label = T("Anonymous submission")
    db.t_articles.anonymous_submission.represent = lambda text, row: common_small_html.mkAnonymousMask(auth, db, text)
    db.t_articles.already_published.represent = lambda text, row: common_small_html.mkJournalImg(auth, db, text)
    db.auth_user.registration_key.represent = lambda text, row: SPAN(text, _class="pci-blocked") if (text == "blocked" or text == "disabled") else text
    db.auth_user.last_alert.readable = True
    db.auth_user.last_alert.writable = True

    original_grid = SQLFORM.smartgrid(
                    db.auth_user,
                    fields=fields,
                    linked_tables=[
                        "auth_user",
                        "auth_membership",
                        "t_articles",
                        "t_recommendations",
                        "t_reviews",
                        "t_press_reviews",
                        "t_comments",
                    ],
                    links=links,
                    csv=False,
                    exportclasses=dict(auth_user=expClass, auth_membership=expClass),
                    editable=dict(auth_user=True, auth_membership=False),
                    details=dict(auth_user=True, auth_membership=False),
                    searchable=dict(auth_user=True, auth_membership=False),
                    create=dict(
                        auth_user=create,
                        auth_membership=create,
                        t_articles=create,
                        t_recommendations=create,
                        t_reviews=create,
                        t_press_reviews=create,
                        t_comments=create,
                    ),
                    selectable=selectable,
                    maxtextlength=250,
                    paginate=25,
    )

    # options to be removed from the search dropdown:
    remove_options = ['auth_user.registration_key', 'auth_user.alerts', 
                    'auth_user.last_alert', 'auth_user.registration_datetime',
                    'auth_user.ethical_code_approved', 'auth_user.id',]

    # the grid is adjusted after creation to adhere to our requirements
    grid = adjust_grid.adjust_grid_basic(original_grid, 'users', remove_options) \
            if len(request.args) == 1 else original_grid

    if "auth_membership.user_id" in request.args:
        if grid and grid.element(_title="Add record to database"):
            grid.element(_title="Add record to database")[0] = T("Add role")
            # grid.element(_title="Add record to database")['_title'] = T('Manually add new round of recommendation. Expert use!!')

    response.view = "default/myLayout.html"
    return dict(
        titleIcon="user",
        pageTitle=getTitle(request, auth, db, "#AdministrateUsersTitle"),
        pageHelp=getHelp(request, auth, db, "#AdministrateUsers"),
        customText=getText(request, auth, db, "#AdministrateUsersText"),
        grid=grid,
        
    )


######################################################################################################################################################################
# Prepares lists of email addresses by role
@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developer"))
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
    myContents.append(H1(T("Users with completed or awaiting reviews:")))
    emails = []
    query = db(
        (db.auth_user.id == db.t_reviews.reviewer_id)
        & (db.t_reviews.review_state.belongs(["Awaiting review", "Review completed"]))
    ).select(
        db.auth_user.email, groupby=db.auth_user.email
    )
    for user in query:
            emails.append(user.email)
    list_emails = ", ".join(emails)
    myContents.append(list_emails)

    myContents.append(H1(T("Users with completed reviews"), BR(), T("for recommended or rejected preprints:")))
    query = db(
        (db.auth_user.id == db.t_reviews.reviewer_id)
        & (db.t_reviews.review_state == "Review completed")
        & (db.t_reviews.recommendation_id == db.t_recommendations.id)
        & (db.t_recommendations.article_id == db.t_articles.id)
        & (db.t_articles.status.belongs(["Recommended", "Rejected"]))
    ).select(
        db.auth_user.email, groupby=db.auth_user.email
    )
    myContents.append(", ".join(
        [ _.email for _ in query]
    ))

    # Other users
    myContents.append(H1(T("Other users (no role, not listed above):")))
    emails = []
    query = db.executesql(
        """SELECT DISTINCT auth_user.email FROM auth_user 
				WHERE auth_user.id NOT IN (SELECT DISTINCT auth_membership.user_id FROM auth_membership) 
				AND auth_user.id NOT IN (SELECT DISTINCT t_articles.user_id FROM t_articles WHERE t_articles.user_id IS NOT NULL) 
				AND auth_user.id NOT IN (SELECT DISTINCT t_reviews.reviewer_id FROM t_reviews WHERE t_reviews.reviewer_id IS NOT NULL AND review_state IN ('Awaiting review', 'Review completed')) 
				AND auth_user.email IS NOT NULL;"""
    )
    for user_email in query:
        emails.append(user_email[0])
    list_emails = ", ".join(emails)
    myContents.append(list_emails)

    # Semestrial Newsletter users
    myContents.append(H1(T("Users receiving the newsletter:")))
    query = db.executesql("""
        SELECT email FROM auth_user
        WHERE alerts != 'Never' AND country is not NULL;
    """
    )
    list_emails = ", ".join([email[0] for email in query])
    myContents.append(list_emails)

    return dict(
        titleIcon="earphone",
        pageTitle=getTitle(request, auth, db, "#EmailsListsUsersTitle"),
        customText=getText(request, auth, db, "#EmailsListsUsersText"),
        pageHelp=getHelp(request, auth, db, "#EmailsListsUsers"),
        content=myContents,
        grid="",
    )


######################################################################################################################################################################
# Display the list of thematic fields
# Can be modified only by developer and administrator
@auth.requires_login()
def thematics_list():
    response.view = "default/myLayout.html"

    write_auth = auth.has_membership("administrator") or auth.has_membership("developer")
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
        titleIcon="tags",
        pageTitle=getTitle(request, auth, db, "#AdministrateThematicFieldsTitle"),
        pageHelp=getHelp(request, auth, db, "#AdministrateThematicFields"),
        customText=getText(request, auth, db, "#AdministrateThematicFieldsText"),
        grid=grid,
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager") or auth.has_membership(role="administrator") or auth.has_membership(role="developer"))
def allRecommCitations():
    response.view = "default/myLayout.html"

    allRecomms = db(
        (db.t_articles.status == "Recommended") & (db.t_recommendations.article_id == db.t_articles.id) & (db.t_recommendations.recommendation_state == "Recommended")
    ).select(db.t_recommendations.ALL, orderby=db.t_recommendations.last_change)
    grid = OL()
    for myRecomm in allRecomms:
        grid.append(
            LI(
                common_small_html.mkRecommCitation(auth, db, myRecomm),
                BR(),
                B("Recommends: "),
                common_small_html.mkArticleCitation(auth, db, myRecomm),
                P(),
            )
        )
    return dict(
        titleIcon="education",
        pageTitle=getTitle(request, auth, db, "#allRecommCitationsTextTitle"),
        customText=getText(request, auth, db, "#allRecommCitationsTextText"),
        pageHelp=getHelp(request, auth, db, "#allRecommCitationsHelpTexts"),
        grid=grid,
    )


######################################################################################################################################################################
# Lists article status
# writable by developers only!!
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager") or auth.has_membership(role="administrator") or auth.has_membership(role="developer"))
def article_status():
    response.view = "default/myLayout.html"

    write_auth = auth.has_membership("developer")
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
        fields=[
            db.t_status_article.status,
            db.t_status_article._id,
            db.t_status_article.priority_level,
            db.t_status_article.color_class,
            db.t_status_article.explaination,
        ],
        orderby=db.t_status_article.priority_level,
    )
    common_small_html.mkStatusArticles(db)
    return dict(
        titleIcon="bookmark",
        pageTitle=getTitle(request, auth, db, "#AdministrateArticleStatusTitle"),
        pageHelp=getHelp(request, auth, db, "#AdministrateArticleStatus"),
        customText=getText(request, auth, db, "#AdministrateArticleStatusText"),
        grid=grid,
    )


######################################################################################################################################################################
# PDF management
@auth.requires(auth.has_membership(role="manager") or auth.has_membership(role="administrator") or auth.has_membership(role="developer"))
def manage_pdf():
    response.view = "default/myLayout.html"

    # Do the complex query in full sql and return valid ids
    myList = []
    myQy = db.executesql(
        "SELECT r.id FROM (t_recommendations AS r JOIN t_articles AS a ON (r.article_id=a.id)) LEFT JOIN t_pdf AS p ON r.id=p.recommendation_id WHERE a.status IN ('Recommended', 'Pre-recommended', 'Recommended-private', 'Pre-recommended-private') AND r.recommendation_state LIKE 'Recommended';"
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
    return dict(
        titleIcon="duplicate",
        pageTitle=getTitle(request, auth, db, "#AdminPdfTitle"),
        customText=getText(request, auth, db, "#AdminPdfText"),
        grid=grid,
    )


@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developer"))
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
		WHERE w.review_state NOT IN ('Awaiting response', 'Declined', 'Declined manually', 'Cancelled')
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
        a.report_stage,
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

    if pciRRactivated:
        db.executesql(
            """SELECT colpivot('_t_%(runId)s', 
	    	'SELECT * FROM _v_%(runId)s', 
	    	array['type_article', 'report_stage', 'title', 'article_doi', 'article_id', 'submitter', 'submission', 'first_outcome', 'recommenders', 'co_recommenders', 'article_status', 'article_status_last_change', 'recommendation_doi', 'recommendation_info'],
	    	array['recomm_round', 'reviewer_num'], 
	    	'#.reviewer',
	    	null
	    );"""
            % locals()
        )
    else:
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

    resu = db.executesql("""SELECT * FROM _t_%(runId)s ORDER BY submission DESC;""" % locals())
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
        titleIcon="list-alt",
        customText=getText(request, auth, db, "#AdminRecapReviews"),
        pageTitle=getTitle(request, auth, db, "#AdminRecapReviewsTitle"),
        grid=DIV(grid, _style="width:100%; overflow-x:scroll;"),
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developer"))
def rec_as_latex():
    response.view = "default/info.html"

    if "articleId" in request.vars:
        articleId = request.vars["articleId"]
    elif "id" in request.vars:
        articleId = request.vars["id"]
    else:
        session.flash = T("Unavailable")
        redirect(URL('default','index'))
    if not articleId.isdigit():
        session.flash = T("Unavailable")
        redirect(URL('default','index'))

    withHistory = "withHistory" in request.vars
    bib = admin_module.recommBibtex(articleId)
    latFP = admin_module.frontPageLatex(articleId)
    latRec = admin_module.recommLatex(articleId, withHistory)
    message = DIV(
        H2("BibTex:"),
        PRE(bib),
        H2("Front page:"),
        PRE(latFP),
        H2("Recommendation:"),
        PRE(latRec),
    )
    return dict(message=message)


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developer"))
def testRedir():
    session.flash = "redirect!"
    url = URL("default", "index", user_signature=True)  # , scheme=scheme, host=host, port=port)
    redirect(url)


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developer"))
def mailing_queue():
    response.view = "default/myLayout.html"
    urlFunction = request.function
    urlController = request.controller

    db.mail_queue.sending_status.represent = lambda text, row: DIV(
        SPAN(admin_module.makeMailStatusDiv(text)),
        SPAN(I(T("Sending attempts:")), XML("&nbsp;"), B(row.sending_attempts), _style="font-size: 12px; margin-top: 5px"),
        _class="pci2-flex-column",
        _style="margin: 5px 10px;",
    )

    db.mail_queue.id.readable = False
    db.mail_queue.sending_attempts.readable = False

    db.mail_queue.sending_date.represent = lambda text, row: datetime.datetime.strptime(str(text), "%Y-%m-%d %H:%M:%S")
    db.mail_queue.mail_content.represent = lambda text, row: XML(admin_module.sanitizeHtmlContent(text))
    db.mail_queue.mail_subject.represent = lambda text, row: B(text)
    db.mail_queue.article_id.represent = lambda art_id, row: common_small_html.mkRepresentArticleLightLinked(auth, db, art_id)
    db.mail_queue.mail_subject.represent = lambda text, row: DIV(B(text), BR(), SPAN(row.mail_template_hashtag), _class="ellipsis-over-500")
    db.mail_queue.cc_mail_addresses.widget = app_forms.cc_widget
    db.mail_queue.replyto_addresses.widget = app_forms.cc_widget
    db.mail_queue.bcc_mail_addresses.widget = app_forms.cc_widget

    db.mail_queue.sending_status.writable = False
    db.mail_queue.sending_attempts.writable = False
    db.mail_queue.dest_mail_address.writable = False
    db.mail_queue.user_id.writable = False
    db.mail_queue.mail_template_hashtag.writable = False
    db.mail_queue.reminder_count.writable = False
    db.mail_queue.article_id.writable = False
    db.mail_queue.recommendation_id.writable = False

    db.mail_queue.removed_from_queue.writable = False
    db.mail_queue.removed_from_queue.readable = False

    db.mail_queue.user_id.searchable = False
    db.mail_queue.review_id.searchable = False
    db.mail_queue.recommendation_id.searchable = False

    if len(request.args) > 2 and request.args[0] == "edit":
        db.mail_queue.mail_template_hashtag.readable = True
    else:
        db.mail_queue.mail_template_hashtag.readable = False
    myScript = common_tools.get_script("replace_mail_content.js")

    link_body=lambda row: A(
        (T("Scheduled") if row.removed_from_queue == False else T("Unscheduled")),
        _href=URL(c="admin_actions", f="toggle_shedule_mail_from_queue", vars=dict(emailId=row.id)),
        _class="btn btn-default",
        _style=("background-color: #3e3f3a;" if row.removed_from_queue == False else "background-color: #ce4f0c;"),
    ) if row.sending_status == "pending" else (admin_module.mkEditResendButton(auth, db, row, urlFunction=urlFunction, urlController=urlController) if row.sending_status == "sent" else "")
    
    links = [
        dict(
            header="",
            body = link_body,
        )
    ]

    original_grid = SQLFORM.grid(
        db.mail_queue,
        details=True,
        editable=lambda row: (row.sending_status == "pending"),
        deletable=lambda row: (row.sending_status != "sent"),
        create=False,
        searchable=True,
        paginate=50,
        maxtextlength=256,
        orderby=~db.mail_queue.id,
        onvalidation=mail_form_processing,
        fields=[
            db.mail_queue.sending_status,
            db.mail_queue.removed_from_queue,
            db.mail_queue.sending_date,
            db.mail_queue.sending_attempts,
            db.mail_queue.dest_mail_address,
            #db.mail_queue.cc_mail_addresses,
            #db.mail_queue.replyto_addresses,
            # db.mail_queue.user_id,
            db.mail_queue.mail_subject,
            db.mail_queue.mail_template_hashtag,
            db.mail_queue.article_id,
        ],
        links=links,
        links_placement="left",
        _class="web2py_grid action-button-absolute",
    )

    remove_options = ['mail_queue.user_id', 'mail_queue.recommendation_id',
                      'mail_queue.review_id', 'mail_queue.reminder_count',
                      'mail_queue.sending_date']

    # the grid is adjusted after creation to adhere to our requirements
    grid = adjust_grid.adjust_grid_basic(original_grid, 'mail_queue', remove_options) \
            if len(request.args) == 0 else original_grid

    return dict(
        titleIcon="send",
        pageTitle=getTitle(request, auth, db, "#AdminMailQueueTitle"),
        customText=getText(request, auth, db, "#AdminMailQueueText"),
        grid=grid,
        myFinalScript=myScript,
        absoluteButtonScript=common_tools.absoluteButtonScript,
    )


def mail_form_processing(form):
    app_forms.update_mail_content_keep_editing_form(form, db, request, response)

    if form.content_saved:
        redirect(URL("admin", "mailing_queue", args=request.args, user_signature=True))


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="administrator"))
def edit_config():
    form = SQLFORM(
        db.config,
        record=1,
        showid=False,
        fields=[request.args[0]] if request.args else db.config.fields,
    )
    if form.process().accepted:
        session.flash = T("Configuration saved")
        redirect(URL(c="admin", f=" "))
    elif form.errors:
        response.flash = T("Form has errors")

    response.view = "default/myLayout.html"
    return dict(
        form=form,
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="manager"))
def edit_and_resend_email():
    response.view = "default/myLayout.html"
    mailId = request.vars["mailId"]
    articleId = request.vars["articleId"]
    hashtag = request.vars["hashtag"]
    urlFunction = request.vars['urlFunction']
    urlController = request.vars['urlController']

    if mailId is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    
    mail = db(db.mail_queue.id == mailId).select()[0]

    default_replyto = emailing_tools.to_string_addresses(mail.replyto_addresses)
    default_cc = emailing_tools.to_string_addresses(mail.cc_mail_addresses)

    form = SQLFORM.factory(
        Field("sending_date", label=T("Previous Sending Date"), type="string", length=250, default=mail.sending_date, writable=False),
        Field("dest_mail_address", label=T("Destination Email"), type="string", length=250, default=mail.dest_mail_address),
        Field("replyto", label=T("Reply-to"), type="string", length=250, default=default_replyto),
        Field("cc_mail_addresses", type="string", label=T("CC"), default=default_cc),
        Field("subject", label=T("Subject"), type="string", length=250, default=mail.mail_subject, required=True),
        Field("content", label=T("Content"), type="text", required=True),
    )
    form.element(_type="submit")["_value"] = T("Send e-mail")
    form.element("textarea[name=content]")["_style"] = "height:500px;"
    html_string = str(mail.mail_content)
    
    resent = False
    if form.process().accepted:
        try:
            emailing.resend_mail(
                session, 
                auth, 
                db, 
                form,
                articleId=articleId,
                hashtag=hashtag,
                )
            resent = True
        except Exception as e:
            session.flash = (session.flash or "") + T("E-mail failed.")
            raise e
        redirect(URL(c=urlController, f=urlFunction, vars=dict(articleId=articleId), user_signature=True))

    return dict(
        form=form,
        pageHelp=getHelp(request, auth, db, "#EmailForRegisterdReviewer"),
        titleIcon="envelope",
        html_string=html_string,
        resent=resent,
        pageTitle=getTitle(request, auth, db, "#EmailForRegisteredReviewerInfoTitle"),
        customText=getText(request, auth, db, "#EmailForRegisteredReviewerInfo"),
    )
