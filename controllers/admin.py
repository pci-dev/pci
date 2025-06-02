# -*- coding: utf-8 -*-

import re
import random
import datetime
from enum import Enum
from typing import Callable, Literal, Union

from app_modules.helper import *

from controller_modules import admin_module
from controller_modules import adjust_grid
from app_modules import common_small_html
from app_modules import common_tools
from app_modules import emailing_tools

from app_components import app_forms

from gluon import IS_EMAIL
from gluon.contrib.appconfig import AppConfig # type: ignore
from gluon.http import redirect # type: ignore
from gluon.sqlhtml import SQLFORM
from models.mail_queue import MailQueue, SendingStatus
from models.recommendation import Recommendation, RecommendationState
from pydal.objects import Field
from pydal.validators import IS_IN_DB

from gluon.http import redirect # type: ignore

from app_modules.common_tools import URL

myconf = AppConfig(reload=True)

# frequently used constants
csv = False  # no export allowed
expClass = dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)

pciRRactivated = myconf.get("config.registered_reports", default=False)

DEFAULT_DATE_FORMAT = common_tools.getDefaultDateFormat()

db = current.db
response = current.response
request = current.request
auth = current.auth
session = current.session
T = current.T

######################################################################################################################################################################
## Menu Routes
######################################################################################################################################################################
def index():
    return list_users()


def toggle_silent_mode():
    if common_tools.user_can_active_silent_mode() and not current.session.silent_mode:
        current.session.silent_mode = True
        current.session.flash = "Silent mode: No email will be sent by the PCI site"
    else:
        current.session.silent_mode = None
        current.session.flash = "You have left silent mode"

    redirect(current.request.vars.previous_url)
          

@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developer"))
def list_users():
    selectable = None
    links = None
    create = True  # allow create buttons
    if len(request.args) == 0 or (len(request.args) == 1 and request.args[0] == "auth_user"):
        selectable = [
            (
                T("Add role 'recommender' to selected users"),
                lambda ids: [admin_module.set_as_recommender(ids)],
                "btn btn-info pci-admin",
            )
        ]
        links = [dict(header=T("Roles"), body=lambda row: admin_module.mkRoles(row))]

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
    db.auth_user._id.represent = lambda i, row: common_small_html.mkUserId(i, linked=True)
    db.t_reviews.recommendation_id.label = T("Article DOI")
    db.t_articles.anonymous_submission.label = T("Anonymous submission")
    db.t_articles.anonymous_submission.represent = lambda text, row: common_small_html.mkAnonymousMask(text)
    db.t_articles.already_published.represent = lambda text, row: common_small_html.mkJournalImg(text)
    db.auth_user.registration_key.represent = lambda text, row: SPAN(text, _class="pci-blocked") if (text == "blocked" or text == "disabled") else text
    db.auth_user.last_alert.readable = True
    db.auth_user.last_alert.writable = True

    fixup_email_requires(db.auth_user.email)

    def onvalidation(form):
        # validate only for sqlform's user edit form
        if not "email" in form.vars: return

        user_id = request.args[-1]
        if form.vars.email == db.auth_user[user_id].email:
            return
        if db(db.auth_user.email == form.vars.email).count():
            form.errors.update({"email": "E-mail already associated to another user"})


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
                    onvalidation=onvalidation,
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
                    constraints={
                        'auth_user': db.auth_user.deleted == False
                    }
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
        pageTitle=getTitle("#AdministrateUsersTitle"),
        pageHelp=getHelp("#AdministrateUsers"),
        customText=getText("#AdministrateUsersText"),
        grid=grid,
    )


def fixup_email_requires(email: Field):
    import pydal
    email.requires = [
        pydal.validators.IS_EMAIL(),
        pydal.validators.IS_LOWER(),
        #pydal.validators.IS_NOT_IN_DB(), # discard this one
    ]

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
        if user.email:
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
        [ _.email for _ in query if _.email]
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

    # Newsletter users
    myContents.append(H1(T("Users receiving the newsletter:")))
    query = db.executesql("""
        SELECT email FROM auth_user
        WHERE alerts != 'Never'
        AND country is not NULL
        AND not deleted
        ;
    """
    )
    list_emails = ", ".join([email[0] for email in query])
    myContents.append(list_emails)

    return dict(
        titleIcon="earphone",
        pageTitle=getTitle("#EmailsListsUsersTitle"),
        customText=getText("#EmailsListsUsersText"),
        pageHelp=getHelp("#EmailsListsUsers"),
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
        pageTitle=getTitle("#AdministrateThematicFieldsTitle"),
        pageHelp=getHelp("#AdministrateThematicFields"),
        customText=getText("#AdministrateThematicFieldsText"),
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
                common_small_html.mkRecommCitation(myRecomm),
                BR(),
                B("Recommends: "),
                common_small_html.mkArticleCitation(myRecomm),
                P(),
            )
        )
    return dict(
        titleIcon="education",
        pageTitle=getTitle("#allRecommCitationsTextTitle"),
        customText=getText("#allRecommCitationsTextText"),
        pageHelp=getHelp("#allRecommCitationsHelpTexts"),
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
    db.t_status_article._id.represent = lambda text, row: common_small_html.mkStatusDiv(row.status)
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
    common_small_html.mkStatusArticles()
    return dict(
        titleIcon="bookmark",
        pageTitle=getTitle("#AdministrateArticleStatusTitle"),
        pageHelp=getHelp("#AdministrateArticleStatus"),
        customText=getText("#AdministrateArticleStatusText"),
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
    db.t_recommendations._format = lambda row: admin_module.mkRecommendationFormat2(row)
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
        pageTitle=getTitle("#AdminPdfTitle"),
        customText=getText("#AdminPdfText"),
        grid=grid,
    )


@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developer"))
def recap_reviews():
    response.view = "default/myLayout.html"

    if not db(db.t_reviews.id).count() > 0:
        response.view = "default/info.html"
        return dict(message="no reviews yet")

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
        customText=getText("#AdminRecapReviews"),
        pageTitle=getTitle("#AdminRecapReviewsTitle"),
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

    def represent_sending_status(text: str, row: MailQueue):
        return DIV(
            SPAN(admin_module.makeMailStatusDiv(text)),
            SPAN(I(T("Sending attempts:")), XML("&nbsp;"), B(row.sending_attempts), _style="font-size: 12px; margin-top: 5px"),
            _class="pci2-flex-column",
            _style="margin: 5px 10px;",
        )
    
    def represent_sending_date(text: str, row: MailQueue):
        return datetime.datetime.strptime(str(text), "%Y-%m-%d %H:%M:%S") if text else None
    
    def represent_mail_content(text: str, row: MailQueue):
        return XML(admin_module.sanitizeHtmlContent(text))
    
    def represent_mail_subject(text: str, row: MailQueue):
        return DIV(B(text), BR(), SPAN(row.mail_template_hashtag), _class="ellipsis-over-500")

    db.mail_queue.sending_status.represent = represent_sending_status

    db.mail_queue.id.readable = False
    db.mail_queue.sending_attempts.readable = False

    db.mail_queue.sending_date.represent = represent_sending_date
    db.mail_queue.mail_content.represent = represent_mail_content
    db.mail_queue.mail_subject.represent = represent_mail_subject
    db.mail_queue.cc_mail_addresses.widget = app_forms.cc_widget
    db.mail_queue.replyto_addresses.widget = app_forms.cc_widget
    db.mail_queue.bcc_mail_addresses.widget = app_forms.cc_widget

    db.mail_queue.sending_status.writable = False
    db.mail_queue.sending_attempts.writable = False
    db.mail_queue.user_id.writable = False
    db.mail_queue.mail_template_hashtag.writable = False
    db.mail_queue.reminder_count.writable = False
    db.mail_queue.article_id.readable = False
    db.mail_queue.recommendation_id.writable = False

    db.mail_queue.removed_from_queue.writable = False
    db.mail_queue.removed_from_queue.readable = False

    db.mail_queue.user_id.searchable = False
    db.mail_queue.review_id.searchable = False
    db.mail_queue.recommendation_id.searchable = False

    db.mail_queue.dest_mail_address.requires = IS_EMAIL()

    if len(request.args) > 2 and request.args[0] == "edit":
        db.mail_queue.mail_template_hashtag.readable = True

        mail = MailQueue.get_mail_by_id(request.args[2])
        if mail:
            is_manager = bool(auth.has_membership(role=Role.MANAGER.value))
            is_pending = mail.sending_status == SendingStatus.PENDING.value
            dest_mail_address_writable = is_manager and is_pending
            db.mail_queue.dest_mail_address.writable = dest_mail_address_writable

            if dest_mail_address_writable and "dest_mail_address" in request.post_vars:
                dest_mail_address = request.post_vars["dest_mail_address"]
                _, error = IS_EMAIL()(dest_mail_address) # type: ignore
                if not error:
                    MailQueue.update_dest_mail_address(mail.id, dest_mail_address)
    else:
        db.mail_queue.mail_template_hashtag.readable = False
        db.mail_queue.dest_mail_address.writable = False

    myScript = common_tools.get_script("replace_mail_content.js")

    link_body: Callable[[Any], Union[A, Literal['']]] = lambda row: A(
        (T("Scheduled") if row.removed_from_queue == False else T("Unscheduled")),
        _href=URL(c="admin_actions", f="toggle_shedule_mail_from_queue", vars=dict(emailId=row.id)),
        _class="btn btn-default",
        _style=("background-color: #3e3f3a;" if row.removed_from_queue == False else "background-color: #ce4f0c;"),
    ) if row.sending_status == "pending" else (admin_module.mkEditResendButton(row, urlFunction=urlFunction, urlController=urlController) if row.sending_status == "sent" else "")
    
    links = [
        dict(
            header="",
            body = link_body,
        )
    ]

    original_grid: ... = SQLFORM.grid( # type: ignore
        db.mail_queue,
        details=True,
        editable=lambda row: (row.sending_status == "pending"), # type: ignore
        deletable=lambda row: (row.sending_status != "sent"), # type: ignore
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
            #db.mail_queue.cc_mail_addresses,
            #db.mail_queue.replyto_addresses,
            # db.mail_queue.user_id,
            db.mail_queue.mail_subject,
            db.mail_queue.dest_mail_address,
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
        pageTitle=getTitle("#AdminMailQueueTitle"),
        customText=getText("#AdminMailQueueText"),
        grid=grid,
        myFinalScript=myScript,
        absoluteButtonScript=common_tools.absoluteButtonScript,
    )


def mail_form_processing(form: ...):
    app_forms.update_mail_content_keep_editing_form(form)

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
    page_url = URL(request.controller, request.function, args=request.args)
    if form.process().accepted:
        session.flash = T("Configuration saved")
        redirect(page_url)
    elif form.errors:
        response.flash = T("Form has errors")
        redirect(page_url)

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
        pageHelp=getHelp("#EmailForRegisterdReviewer"),
        titleIcon="envelope",
        html_string=html_string,
        resent=resent,
        pageTitle=getTitle("#EmailForRegisteredReviewerInfoTitle"),
        customText=getText("#EmailForRegisteredReviewerInfo"),
    )


@auth.requires(auth.has_membership(role="administrator"))
def send_mail_for_newsletter_subscriber():
    form = FORM(
            DIV(LABEL("Mail subject"), INPUT(_type="text", _name="subject", _class='form-control'), _style="margin-top: 20px"),
            DIV(LABEL("Mail content"), TEXTAREA("", _name='content', _class='form-control', _id="mail_queue_mail_content"), _style="margin-top: 10px"),
            CENTER(INPUT(_type="submit", _value="Send")))

    if form.process().accepted: #type: ignore
        subject = str(form.vars.subject) # type: ignore
        content = str(form.vars.content) # type: ignore

        common_tools.run_web2py_script("send_mail_subscribers_command.py", subject, content)
        current.response.flash = "Email send to all subscribers"

    current.response.view = "default/myLayout.html"
    return dict(form=form,
                pageTitle=getTitle("#SendMailSubscribersTitle"),
                customText=getText("#SendMailSubscribersText"))


@auth.requires(auth.has_membership(role="administrator"))
def extract_recommendations():

    try:
        start_year = int(request.vars.start_year)
        end_year = int(request.vars.end_year)
    except:
        raise HTTP(400, "invalid parameter: {start|end}_year must be an integer")

    response.headers["Content-Type"] = "text/tsv"

    return "\n".join(["\t".join(row.values())

        for row in (
            [{h: h.value for h in Header}] +
            get_data(start_year, end_year)
        )
    ]) + "\n"


class Header(Enum):
    PCI_NAME = "Nom de la PCI"
    REF_ARTICLE = "Référence de l'article recommendé"
    SUBMITTER_NAME = "Nom du submitter"
    RECOMMENDATION_DATE = "Date de la recommendation"
    PUBLISHED_ARTICLE_DOI = "DOI du published now in"
    SUBMITTER_MAIL = "Mail du submitter"


def get_data(start_year: int, end_year: int):
    start_date = datetime.datetime(year=start_year, month=1, day=1)
    end_date = datetime.datetime(year=end_year, month=12, day=31)

    rows = db(
          (db.t_articles.id == db.t_recommendations.article_id)
        & (db.auth_user.id == db.t_articles.user_id)
        & (db.t_recommendations.validation_timestamp >= start_date)
        & (db.t_recommendations.validation_timestamp <= end_date)
        & (db.t_recommendations.recommendation_state == RecommendationState.RECOMMENDED.value)
    ).select(distinct=True)

    pci_name: str = myconf.get("app.longname")

    return [ mk_line(row, pci_name) for row in rows ]


def mk_line(row, pci_name: str):
    article: Article = row.t_articles
    submitter: User = row.auth_user
    recommendation: Recommendation = row.t_recommendations

    article_ref: str = Article.get_article_reference(article, False).strip()
    reco_date: str = recommendation.validation_timestamp.strftime("%Y-%m-%d") \
            if recommendation.validation_timestamp else ""

    return {
        Header.PCI_NAME: pci_name,
        Header.REF_ARTICLE: article_ref,
        Header.SUBMITTER_NAME: User.get_name(submitter),
        Header.RECOMMENDATION_DATE: reco_date or "",
        Header.PUBLISHED_ARTICLE_DOI: article.doi_of_published_article or "",
        Header.SUBMITTER_MAIL: submitter.email or ""
    }


def extract():
    response.view = "default/info.html"
    return dict(message=DIV([
        UL(A(url, _href=url))

        for url in [
            URL("api", "all/recommendations"),
            URL("admin", "extract_recommendations", vars={
                    "start_year": datetime.datetime.today().year - 1,
                    "end_year": datetime.datetime.today().year - 1,
            }),
        ]
    ]))

def urls():
    response.view = "default/info.html"
    return dict(message=DIV([
        UL(A(url, _href=url))

        for url in [
            URL("admin", "extract"),
            URL("api", "recommendations"),
            URL("api", " "),
            URL("coar_notify", " "),
            URL("coar_notify", "show?id=XXX"),
            URL("metadata", "recommendation?article_id=XXX"),
        ]
    ]))
