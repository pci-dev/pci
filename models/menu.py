# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

from typing import Any, List, Optional, Tuple, Union
from gluon.contrib.appconfig import AppConfig # type: ignore
from gluon.custom_import import track_changes
from gluon.html import A, I, LI, SPAN
from gluon import DIV, current
from models.article import Article, ArticleStatus
from models.suggested_recommender import SuggestedRecommender
from models.user import User
from app_modules import common_tools

from app_modules.common_tools import URL, is_silent_mode

request = current.request
session = current.session
db = current.db
auth = current.auth
response = current.response
T = current.T

myconf = AppConfig()
postprint = bool(myconf.get("config.postprint", default=False))

track_changes(True)

# ----------------------------------------------------------------------------------------------------------------------
# Customize your APP title, subtitle and menus here
# ----------------------------------------------------------------------------------------------------------------------

response.logo = ""
response.title = myconf.take("app.longname")
response.subtitle = T(myconf.take("app.description"))

# ----------------------------------------------------------------------------------------------------------------------
# read more at http://dev.w3.org/html5/markup/meta.name.html
# ----------------------------------------------------------------------------------------------------------------------
# response.meta.author = myconf.get('app.author')
response.meta.description = myconf.get("app.description")
# response.meta.keywords = myconf.get('app.keywords')
response.meta.generator = myconf.get("app.generator")

# ----------------------------------------------------------------------------------------------------------------------
# your http://google.com/analytics id
# ----------------------------------------------------------------------------------------------------------------------
response.google_analytics_id = None

# ----------------------------------------------------------------------------------------------------------------------
# this is the main application menu add/remove items as required
# ----------------------------------------------------------------------------------------------------------------------
appName = " " + myconf.take("app.longname")

# ----------------------------------------------------------------------------------------------------------------------
# If the app is discontinued add in appconfig.ini [app] section:
# discontinued = True
# ; 307 for temporary, 301 for permanent
# redir_code = 307
# redir_url = https://www.peercommunityin.org
# ----------------------------------------------------------------------------------------------------------------------
discontinued = myconf.get("app.discontinued", default=False)
if discontinued:
    redir_code = myconf.get("app.redir_code", default=307)
    redir_url = myconf.get("app.redir_url", default="https://www.peercommunityin.org")
    raise HTTP(redir_code, T('Sorry, %(appName)s is discontinued. You are being redirected to <a href="%(redir_url)s">%(redir_url)s</a>') % locals(), Location=redir_url)

pciRRactivated = myconf.get("config.registered_reports", default=False)


# Appends developers menu (web2py)
def _DevMenu():
    app = request.application
    ctr = request.controller
    # txtMenu = IMG(_title=T('Development'), _alt=T('Devel.'), _src=URL(c='static', f='images/devel.png'), _class='pci-menuImage')
    txtMenu = menu_entry_item("Development", "glyphicon-qrcode")
    return [
        (
            txtMenu,
            False,
            "#",
            [
                (T("Current GIT version"), False, URL("about", "version", user_signature=True)),
                (T("TEST: Recommenders country map"), False, URL("maps", "recommenders_map", user_signature=True)),
                (T("TEST: Redirection"), False, URL("admin", "testRedir", user_signature=True)),
                # divider(),
                # (T('Restart daemon'), False, URL('admin', 'restart_daemon')),
                divider(),
                (T("Design"), False, URL("admin", "default", "design/%s" % app)),
                divider(),
                (T("Controller"), False, URL("admin", "default", "edit/%s/controllers/%s.py" % (app, ctr))),
                (T("View"), False, URL("admin", "default", "edit/%s/views/%s" % (app, response.view))),
                (T("DB Model"), False, URL("admin", "default", "edit/%s/models/db.py" % app)),
                (T("Menu Model"), False, URL("admin", "default", "edit/%s/models/menu.py" % app)),
                (T("Config.ini"), False, URL("admin", "default", "edit/%s/private/appconfig.ini" % app)),
                (T("Layout"), False, URL("admin", "default", "edit/%s/views/layout.html" % app)),
                (T("Stylesheet"), False, URL("admin", "default", "edit/%s/static/css/web2py-bootstrap3.css" % app)),
                (T("Database"), False, URL(app, "appadmin", "index")),
                (T("Errors"), False, URL("admin", "default", "errors/" + app)),
                (T("About"), False, URL("admin", "default", "about/" + app)),
                # (T('Queue tasks in scheduler'), False, URL(app, 'admin', 'queueTasks')),
                # (T('Terminate scheduler'), False, URL(app, 'admin', 'terminateScheduler')),
                # (T('Kill scheduler'), False, URL(app, 'admin', 'killScheduler')),
                # (T('Transfer help'), False, URL('help', 'transfer_help')),
                # (T('Test flash'), False, URL('alerts', 'test_flash')),
                # (T('Test FB + tweeter'), False, URL('about', 'test')),
                # (T('Shrink user images'), False, URL('admin', 'resizeAllUserImages')),
            ],
        ),
    ]


# default public menu
def _BaseMenu(footerMenu=False):
    ctr = request.controller
    fct = request.function

    isHomeActive = False
    if ctr == "default" and fct != "user":
        isHomeActive = True

    if footerMenu:
        homeLink = (IMG(_style="", _src=URL(c="static", f="images/pci-logo.svg")), isHomeActive, URL("default", "index"))
    else:
        homeLink = (IMG(_style="height:40px", _src=URL(c="static", f="images/small-background.png")), isHomeActive, URL("default", "index"))

    menuBar = [
        homeLink,
    ]
    return menuBar


def _ToolsMenu():
    ctr = request.controller
    isActive = False
    if ctr == "tools":
        isActive = True

    if auth.has_membership(None, None, "administrator"):
        myClass = "pci-admin"
    else:
        myClass = "pci-manager"

    toolMenu = [
        (T("Send me a test e-mail"), False, URL("admin_actions", "testMail", user_signature=True)),
        (T("Send me the newsletter"), False, URL("alerts", "testMyNewsletterMail", user_signature=True)),
        (T("Delete trapped e-mails"), False, URL("admin_actions", "delete_trapped_emails")),
        (T("test delete mail"), False, URL("alerts", "testDeleteMail", user_signature=True)),
        # (T('Test ALL e-mail alerts'), False, URL('alerts', 'alertUsers')),
        (T("RSS for bioRxiv"), False, URL("rss", "rss4bioRxiv", user_signature=True)),
        (T("RSS for eLife"), False, URL("rss", "rss4elife", user_signature=False)),
        (T("RSS for Altmetric"), False, URL("rss", "rss4altmetric", user_signature=False)),
        (T("Social networks", lazy=False), False, URL("about", "social", user_signature=True)),
    ]

    return [
        (SPAN(I(_class="glyphicon glyphicon-wrench"), T("Tools"), _class=myClass), isActive, "#", toolMenu),
    ]


# Appends administrators menu
def _AdminMenu():
    ctr = current.request.controller
    isActive = False
    if ctr == "admin":
        isActive = True

    silent_mode_url = URL("admin", "toggle_silent_mode", vars=dict(previous_url=URL(args=current.request.args, vars=current.request.get_vars)))
    if is_silent_mode():
        silent_mode_menu: ... = menu_entry("Disable silent Mode", "glyphicon-volume-up", silent_mode_url)
    else:
        silent_mode_menu: ... = menu_entry("Enable silent Mode", "glyphicon-volume-off", silent_mode_url)


    adminMenu = [
        menu_entry("Users & roles", "glyphicon-user", URL("admin", "list_users")),
        menu_entry("Synthesis of reviews", "glyphicon-list-alt", URL("admin", "recap_reviews")),
        menu_entry("This PCI recommendation citations", "glyphicon-education", URL("admin", "allRecommCitations")),
        menu_entry("Extract PCI recommendations data", "glyphicon-education", URL("admin", "extract")),
        menu_entry("Recommendation PDF files", "glyphicon-duplicate", URL("admin", "manage_pdf")),
        menu_entry("Mailing queue", "glyphicon-send", URL("admin", "mailing_queue")),
        menu_entry("Send mail to all subscribers", "glyphicon-send", URL("admin", "send_mail_for_newsletter_subscriber")),
        silent_mode_menu,
        menu_entry("URLs of interest", "glyphicon-list-alt", URL("admin", "urls")),
        divider(),
        menu_entry("Thematic fields", "glyphicon-tags", URL("admin", "thematics_list")),
        menu_entry("Status of articles", "glyphicon-bookmark", URL("admin", "article_status")),
        menu_entry("Help texts", "glyphicon-question-sign", URL("custom_help_text", "help_texts")),
        menu_entry("E-mail templates", "glyphicon-envelope", URL("custom_help_text", "mail_templates")),
        menu_entry("Upload filetypes", "glyphicon-file", URL("admin", "edit_config/allowed_upload_filetypes")),
        menu_entry("COAR whitelist", "glyphicon-inbox", URL("admin", "edit_config/coar_whitelist")),
        menu_entry("ISSN", "glyphicon-cog", URL("admin", "edit_config/issn")),
        divider(),
        menu_entry("Contact lists", "glyphicon-earphone", URL("admin", "mailing_lists")),
    ]

    return [
        (SPAN(I(_class="glyphicon glyphicon-cog"), current.T("Admin"), _class="pci-admin"), isActive, "#", adminMenu),
    ]


# Appends personnal menu
def _UserMenu():
    ctr = request.controller
    current_user = User.get_by_id(current.auth.user_id)
    has_new_article_in_cache = current_user and current_user.new_article_cache
    isActive = False
    if ctr == "user":
        isActive = True

    myContributionsMenu: List[Any] = []
    nRevOngoing = 0
    nRevTot = 0
    revClass = ""
    contribMenuClass = ""
    notificationPin = ""

    nRevPend = db(
        (db.t_reviews.reviewer_id == auth.user_id)
        & (db.t_reviews.review_state == "Awaiting response")
        & (db.t_reviews.recommendation_id == db.t_recommendations.id)
        & (db.t_recommendations.article_id == db.t_articles.id)
        & (db.t_articles.status.belongs(("Under consideration", "Scheduled submission under consideration")))
    ).count()

    txtRevPend = menu_entry_item(T("%s Invitation(s) to review a preprint") % nRevPend, "glyphicon-envelope", _class="pci-recommender")

    if nRevPend > 0:
        txtRevPend = SPAN(txtRevPend, _class="pci-enhancedMenuItem")
        contribMenuClass = "pci-enhancedMenuItem"
        notificationPin = DIV(nRevPend, _class="pci2-notif-pin")

    if has_new_article_in_cache: 
        contribMenuClass = "pci-enhancedMenuItem"

    myContributionsMenu += [
        (txtRevPend, False, URL("user", "my_reviews", vars=dict(pendingOnly=True), user_signature=True)),
    ]

    nWaitingForReviewer = db((db.t_articles.is_searching_reviewers == True) & (db.t_articles.status.belongs(("Under consideration", "Scheduled submission under consideration")))).count()
    txtWaitingForReviewer = menu_entry_item(T("%s Preprint(s) in need of reviewers") % nWaitingForReviewer, "glyphicon-inbox")
    if nWaitingForReviewer > 0:
        txtWaitingForReviewer = SPAN(txtWaitingForReviewer, _class="pci-enhancedMenuItem")
        contribMenuClass = "pci-enhancedMenuItem"
        myContributionsMenu += [
            (txtWaitingForReviewer, False, URL("user", "articles_awaiting_reviewers", user_signature=True))
        ]

    myContributionsMenu += [
        menu_entry("Submit a preprint", "glyphicon-edit", URL("user", "new_submission", user_signature=True)),
    ]

    if current_user and current_user.new_article_cache:
        myContributionsMenu.append(menu_entry("Your incomplete submission", "glyphicon-edit", common_tools.URL("user", "fill_new_article", user_signature=True), _class="pci-enhancedMenuItem"))

    myContributionsMenu.append(divider())

    nRevTot = db((db.t_reviews.reviewer_id == auth.user_id)).count()
    nRevOngoing = db((db.t_reviews.reviewer_id == auth.user_id) & (db.t_reviews.review_state == "Awaiting review")).count()
    nRevisions = db((db.t_articles.user_id == auth.user_id) & (db.t_articles.status.belongs("Awaiting revision", "Pre-submission"))).count()
    if nRevOngoing > 0:
        revClass = "pci-enhancedMenuItem"
        contribMenuClass = "pci-enhancedMenuItem"
    if nRevisions > 0:
        contribMenuClass = "pci-enhancedMenuItem"

    if nRevTot > 0: myContributionsMenu += [
        menu_entry("Your past and ongoing reviews", "glyphicon-eye-open", URL("user", "my_reviews", vars=dict(pendingOnly=False), user_signature=True), _class=revClass),
    ]

    _class = "pci-enhancedMenuItem" if nRevisions > 0 else None

    myContributionsMenu += [
        menu_entry("Your submitted preprints", "glyphicon-duplicate", URL("user", "my_articles", user_signature=True), _class=_class),
    ]

    return [
        (SPAN(I(_class="glyphicon glyphicon-edit"), T("For contributors"), notificationPin, _class=contribMenuClass), isActive, "#", myContributionsMenu),
    ]


def _RecommendationMenu():
    ctr = request.controller
    isActive = False

    notificationPin = ""

    if ctr == "recommender":
        isActive = True

    recommendationsMenu: List[Union[Tuple[SPAN, bool, str], LI]] = []
    colorRequests = False
    nPostprintsOngoing = 0
    nPreprintsOngoing = 0
    nPreprintsCompleted = 0
    classPreprintsCompleted = ""
    classPreprintsOngoing = ""

    # recommendations

    nPreprintsRecomPend = db(
        (db.t_articles.status == "Awaiting consideration")
        & (db.t_articles._id == db.t_suggested_recommenders.article_id)
        & (db.t_suggested_recommenders.suggested_recommender_id == auth.user_id)
        & (db.t_suggested_recommenders.declined == False)
        & (db.t_suggested_recommenders.recommender_validated == True)
    ).count()
    
    txtPreprintsRecomPend = menu_entry_item(
        T("%s Request(s) to handle a preprint") % nPreprintsRecomPend, "glyphicon-envelope",
        _class="pci-recommender"
    )

    if nPreprintsRecomPend > 0:
        txtPreprintsRecomPend = SPAN(txtPreprintsRecomPend, _class="pci-enhancedMenuItem")
        notificationPin = DIV(nPreprintsRecomPend, _class="pci2-notif-pin")
        colorRequests = True

    recommendationsMenu += [
        (txtPreprintsRecomPend, False, URL("recommender", "my_awaiting_articles", vars=dict(pendingOnly=True, pressReviews=False), user_signature=True))
    ]

    nPreprintsOngoing = db(
        (db.t_recommendations.recommender_id == auth.user_id)
        & (db.t_recommendations.article_id == db.t_articles.id)
        & ~(db.t_articles.already_published == True)
        & (db.t_articles.status.belongs(("Under consideration", "Scheduled submission under consideration")))
    ).count()

    nPreprintsCompleted = db(
        (db.t_recommendations.recommender_id == auth.user_id)
        & (db.t_recommendations.article_id == db.t_articles.id)
        & ~(db.t_articles.already_published == True)
        & (db.t_articles.status.belongs(("Recommended-private", "Recommended", "Rejected", "Cancelled")))
    ).count()
    if nPreprintsOngoing > 0:
        classPreprintsOngoing = "pci-enhancedMenuItem"
        colorRequests = True
        
    if nPreprintsCompleted > 0:
        classPreprintsCompleted = "pci-enhancedMenuItem"
        colorRequests = True

    nPostprintsOngoing = db(
        (db.t_recommendations.recommender_id == auth.user_id)
        & (db.t_recommendations.article_id == db.t_articles.id)
        & (db.t_articles.already_published == True)
        & (db.t_articles.status.belongs(("Under consideration", "Scheduled submission under consideration")))
    ).count()
    if nPostprintsOngoing > 0:
        classPostprintsOngoing = "pci-enhancedMenuItem"
        colorRequests = True
    else:
        classPostprintsOngoing = ""

    nPreprintsRequireRecomm =  len(Article.get_articles_need_recommender_for_user(auth.user_id))
    if nPreprintsRequireRecomm > 0:
        classPreprintsRequireRecomm = "pci-enhancedMenuItem"
    else:
        classPreprintsRequireRecomm = ""

    # scheduled submissions (RR only) specific menu entry (validation also available for Managers, as usual)
    nbPend = db(db.pending_scheduled_submissions_query).count()
    if nbPend > 0:
        colorRequests = True
        notificationPin = DIV(nPreprintsRecomPend + nbPend, _class="pci2-notif-pin")
        txtPending = str(nbPend) + " " + (T("Pending validation(s)"))

        recommendationsMenu += [
            menu_entry(txtPending, "glyphicon-time", URL("manager", "pending_articles", vars=dict(recommender=auth.user_id)),
                       _class="pci-enhancedMenuItem"),
        ]

    recommendationsMenu += [
        (
            SPAN(
                menu_entry_item("Preprint(s) in need of a recommender", "glyphicon-inbox", _class="pci-recommender"),
                _class=classPreprintsRequireRecomm,
            ),
            False,
            URL("recommender", "fields_awaiting_articles", user_signature=True),
        )
    ]

    if postprint:
        recommendationsMenu += [
            menu_entry("Recommend a postprint", "glyphicon-edit", URL("recommender", "new_submission", user_signature=True)),
        ]

    recommendationsMenu += [
        divider(),
        (
            SPAN(
                menu_entry_item("Preprint(s) you are handling", "glyphicon-education", _class="pci-recommender"),
                _class=classPreprintsOngoing,
            ),
            False,
            URL("recommender", "my_recommendations", vars=dict(pressReviews=False), user_signature=True),
        ),
        (
            SPAN(
                menu_entry_item("Your completed evaluation(s)", "glyphicon-ok-sign", _class="pci-recommender"),
                _class=classPreprintsCompleted,
            ),
            False,
            URL("recommender", "completed_evaluations", vars=dict(pressReviews=False), user_signature=True),
        ),
    ]

    if postprint:
        recommendationsMenu += [
            (
                SPAN(
                    menu_entry_item("Your recommendations of postprints", "glyphicon-certificate", _class="pci-recommender"),
                    _class=classPostprintsOngoing,
                ),
                False,
                URL("recommender", "my_recommendations", vars=dict(pressReviews=True), user_signature=True),
            )
    ]

    recommendationsMenu += [
        menu_entry("Preprint(s) you are co-handling", "glyphicon-link",
            URL("recommender", "my_co_recommendations", vars=dict(pendingOnly=False), user_signature=True),
            _class="pci-recommender",
        ),
    ]

    if colorRequests:
        requestsMenuTitle = SPAN(SPAN(I(_class="glyphicon glyphicon-education"), T("For recommenders"), notificationPin, _class="pci-recommender"), _class="pci-enhancedMenuItem")
    else:
        requestsMenuTitle = SPAN(I(_class="glyphicon glyphicon-education"), T("For recommenders"), _class="pci-recommender")

    return [(requestsMenuTitle, isActive, "#", recommendationsMenu)]


# Appends managers menu
def _ManagerMenu():
    ctr = request.controller
    isActive = False
    notificationPin = ""
    notificationCount = 0
    if ctr == "manager":
        isActive = True

    txtMenu = SPAN(I(_class="glyphicon glyphicon-th-list"), T("For managers"))

    nbPend = db(db.t_articles.status.belongs(("Pending", "Pre-recommended", "Pre-recommended-private", "Pre-revision", "Pre-rejected"))).count()
    txtPending = str(nbPend) + " " + (T("Pending validation(s)"))
    if nbPend > 0:
        txtPending = SPAN(menu_entry_item(txtPending, "glyphicon-time", _class="pci-enhancedMenuItem"), _class="pci-manager")
        txtMenu = SPAN(I(_class="glyphicon glyphicon-th-list"), T("For managers"), _class="pci-enhancedMenuItem")
        notificationCount += nbPend
    nbGoing = db(db.t_articles.status.belongs(("Under consideration", "Awaiting revision", "Awaiting consideration"))).count()
    txtGoing = str(nbGoing) + " " + (T("Handling process(es) underway"))
    if nbGoing > 0:
        txtGoing = SPAN(menu_entry_item(txtGoing, "glyphicon-refresh", _class="pci-enhancedMenuItem"), _class="pci-manager")
        txtMenu = SPAN(I(_class="glyphicon glyphicon-th-list"), T("For managers"), _class="pci-enhancedMenuItem")
        notificationCount += nbGoing

    nbPendingSurvey = db((db.t_articles.status == "Pending-survey")).count()
    txtPendingSurvey= str(nbPendingSurvey) + " " + (T("Report(s) pending survey"))
    if nbPendingSurvey > 0 and pciRRactivated:
        txtPendingSurvey = SPAN(menu_entry_item(txtPendingSurvey, "glyphicon-time", _class="pci-enhancedMenuItem"), _class="pci-manager")
        txtMenu = SPAN(I(_class="glyphicon glyphicon-th-list"), T("For managers"), _class="pci-enhancedMenuItem")
        notificationCount += nbPendingSurvey

    nbPreSubmitted = db((db.t_articles.status == "Pre-submission")).count()
    txtPreSubmitted = str(nbPreSubmitted) + " " + (T("Article(s) in Pre-submission stage"))
    if nbPreSubmitted > 0:
        txtPreSubmitted = SPAN(menu_entry_item(txtPreSubmitted, "glyphicon-warning-sign", _class="pci-enhancedMenuItem"), _class="pci-manager")
        txtMenu = SPAN(I(_class="glyphicon glyphicon-th-list"), T("For managers"), _class="pci-enhancedMenuItem")
        notificationCount += nbPreSubmitted

    notificationPin = DIV(notificationCount, _class="pci2-notif-pin") if notificationCount > 0 else ""
    managerMenu: List[Union[Tuple[SPAN, bool, str], LI]] = [
        (txtPending, False, URL("manager", "pending_articles", user_signature=True)),
        (txtGoing, False, URL("manager", "ongoing_articles", user_signature=True)),
    ]

    if pciRRactivated: managerMenu += [
        (txtPendingSurvey, False, URL("manager", "pending_surveys", user_signature=True)),
    ]

    managerMenu += [
        (txtPreSubmitted, False, URL("manager", "presubmissions", user_signature=True)),
        menu_entry("Perform tasks in place of recommenders", "glyphicon-education", URL("manager", "all_recommendations", user_signature=True)),
        menu_entry("Perform tasks in place of users", "glyphicon-user", URL("manager", "impersonate_users", user_signature=True)),
        menu_entry("Handling process(es) completed", "glyphicon-ok-sign", URL("manager", "completed_articles", user_signature=True), _class="pci-manager"),
        menu_entry("All articles", "glyphicon-book", URL("manager", "all_articles", user_signature=True), _class="pci-manager"),
        menu_entry("Comments", "glyphicon-comment", URL("manager", "manage_comments", user_signature=True), _class="pci-manager"),
    ]

    sugg_recommender_to_validate = SuggestedRecommender.get_all(True, False, [ArticleStatus.AWAITING_CONSIDERATION, ArticleStatus.PENDING])
    if len(sugg_recommender_to_validate) > 0:
        txtMenu = SPAN(I(_class="glyphicon glyphicon-th-list"), T("For managers"), _class="pci-enhancedMenuItem")
        managerMenu.append(menu_entry("Manage suggested recommenders", "glyphicon-user", URL("manager", "manage_suggested_recommenders", user_signature=True), _class="pci-manager pci-enhancedMenuItem"))
    else:
        managerMenu.append(menu_entry("Manage suggested recommenders", "glyphicon-user", URL("manager", "manage_suggested_recommenders", user_signature=True), _class="pci-manager"))

    if pciRRactivated: managerMenu += [
        menu_entry("Recommender Statistics", "glyphicon-stats", URL("manager", "recommender_statistics", user_signature=True), _class="pci-manager")
    ]
    return [(SPAN(txtMenu, notificationPin, _class="pci-manager"), isActive, "#", managerMenu)]


def _AboutMenu():
    aboutMenu = [
        menu_entry("About", "glyphicon-text-color", URL("about", "about")),
        menu_entry("Other PCIs", "glyphicon-link",  "https://peercommunityin.org/current-pcis/", new_window=True)
    ]

    if not pciRRactivated: aboutMenu += [
        divider(),
        menu_entry("PCI and journals", "glyphicon-link", "https://peercommunityin.org/pci-and-journals/", new_window=True),
    ]

    aboutMenu += [menu_entry("Peer Community Journal", "glyphicon-link", "https://peercommunityin.org/pc-journal/", True)]

    if pciRRactivated: aboutMenu += [
        menu_entry("Full Policies and Procedures", "glyphicon-list-alt", URL("about", "full_policies")),
        divider(),
        menu_entry("List of PCI RR-friendly Journals", "glyphicon-file", URL("about", "pci_rr_friendly_journals")),
        menu_entry("List of PCI RR-interested Journals", "glyphicon-file", URL("about", "pci_rr_interested_journals")),
        menu_entry("Apply to become a Journal Adopter", "glyphicon-pencil", URL("about", "become_journal_adopter")),
        menu_entry("Journal Adopter FAQ", "glyphicon-question-sign", URL("about", "journal_adopter_faq")),
    ]
    else:
        aboutMenu += [
           menu_entry("PCI-friendly Journals", "glyphicon-file", URL("about", "pci_friendly_journals")),
        ]


    aboutMenu += [
        divider(),
        menu_entry("Recommenders", "glyphicon-thumbs-up", URL("about", "recommenders")),
        menu_entry("Thanks to Reviewers", "glyphicon-heart", URL("about", "thanks_to_reviewers")),
        divider(),
        menu_entry("Code of Conduct", "glyphicon-list-alt", URL("about", "ethics")),
        menu_entry("Contact & Credits", "glyphicon-envelope", URL("about", "contact")),
        menu_entry("General Terms of Use", "glyphicon-wrench", URL("about", "gtu")),
    ]

    return [(SPAN(I(_class="glyphicon glyphicon-info-sign"), T("About")), True, "#", aboutMenu)]


def _HelpMenu():
    helpMenu = []

    if not pciRRactivated: helpMenu += [
        menu_entry("How does it work?", "glyphicon-wrench", URL("help", "help_generic")),
        divider(),
    ]
    helpMenu += [
        menu_entry("Guide for Authors", "glyphicon-book", URL("help", "guide_for_authors")),
        menu_entry("Guide for Reviewers", "glyphicon-book", URL("help", "guide_for_reviewers")),
        divider(),
        menu_entry("Guide for Recommenders", "glyphicon-book", URL("help", "guide_for_recommenders")),
        menu_entry("Become a Recommender", "glyphicon-user", URL("help", "become_a_recommenders")),
    ]
    if pciRRactivated: helpMenu += [
        menu_entry("TOP Guidelines", "glyphicon-map-marker", URL("help", "top_guidelines")),
    ]
    helpMenu += [
        divider(),
        menu_entry("How to...?", "glyphicon-wrench", URL("help", "help_practical")),
        menu_entry("FAQs", "glyphicon-question-sign", URL("help", "faq")),
    ]

    if not pciRRactivated: helpMenu += [
        menu_entry("How should you cite an article?", "glyphicon-pencil", URL("help", "cite")),
    ]

    return [(SPAN(I(_class="glyphicon glyphicon-question-sign"), T("Help")), True, "#", helpMenu)]


def _AccountMenu():
    ctr = request.controller
    fct = request.function
    isActive = False
    if ctr == "default" and fct == "user":
        isActive = True

    if auth.is_logged_in():
        if auth.user.city:
            txtMenu = SPAN(I(_class="glyphicon glyphicon-user"), B(auth.user.first_name))
        else:
            txtMenu = SPAN(I(_class="glyphicon glyphicon-user"), B(auth.user.first_name), _class="pci-enhancedMenuItem")
    else:
        txtMenu = SPAN(I(_class="glyphicon glyphicon-log-in"), T("Log in"), _class="pci-enhancedMenuItem")

    auth_menu = []

    if auth.is_logged_in():
        auth_menu += [
            menu_entry("Public page", "glyphicon-briefcase", URL(c="public", f="user_public_page", vars=dict(userId=auth.user.id))),
            divider()]
        
        if auth.user.city:
            auth_menu += menu_entry("Profile", "glyphicon-user", URL("default", "user/profile", user_signature=True)),
        else:
            auth_menu += menu_entry("Profile", "glyphicon-user", URL("default", "user/profile", user_signature=True), _class="pci-enhancedMenuItem"),

        auth_menu += [menu_entry("Change password", "glyphicon-lock", URL("default", "user/change_password", user_signature=True)),
            menu_entry("Change e-mail address", "glyphicon-envelope", URL("default", "change_email", user_signature=True)),
            divider(),
            menu_entry("Log out", "glyphicon-off", URL("default", "user/logout", user_signature=True)),
        ]
    else:
        auth_menu += [
            menu_entry("Log in", "glyphicon-log-in", URL("default", "user/login", user_signature=True)),
            menu_entry("Sign up", "glyphicon-edit", URL("default", "user/register", user_signature=True)),
        ]
        
    return [(SPAN(txtMenu, _class="pci-manager"), isActive, "#", auth_menu)]


def menu_entry(text: str, icon: str, url: str, new_window: bool = False, _class: Optional[str] = None):
    display = menu_entry_item(text, icon, _class)

    if new_window:
        return LI(A(display, _href=url, _target="_blank"))
    else:
        return (display, False, url)


def menu_entry_item(text, icon, _class=None):
    return SPAN(I(_class="pci2-icon-margin-right glyphicon " + icon), T(text), _class=_class)


def divider():
    return LI(_class="divider")


response.menu = _BaseMenu()
response.footer_menu = _BaseMenu(footerMenu=True)


if auth.is_logged_in():
    response.menu += _UserMenu()
    #response.footer_menu += _UserMenu()
if auth.has_membership(None, None, "recommender"):
    response.menu += _RecommendationMenu()
    #response.footer_menu += _RecommendationMenu()

if auth.has_membership(None, None, "manager"):
    response.menu += _ManagerMenu()
    #response.footer_menu += _ManagerMenu()

if auth.has_membership(None, None, "administrator") or auth.has_membership(None, None, "developer"):
    response.menu += _AdminMenu()
    #response.footer_menu += _AdminMenu()

if auth.has_membership(None, None, "administrator") or auth.has_membership(None, None, "developer"):
    response.menu += _ToolsMenu()
    #response.footer_menu += _ToolsMenu()

if auth.has_membership(None, None, "developer"):
    response.menu += _DevMenu()

response.footer_menu += _AboutMenu()
response.footer_menu += _HelpMenu()

response.help_about_menu = _AboutMenu()
response.help_about_menu += _HelpMenu()
response.help_about_menu += _AccountMenu()


# set the language
if "adminLanguage" in request.cookies and not (request.cookies["adminLanguage"] is None):
    T.force(request.cookies["adminLanguage"].value)
