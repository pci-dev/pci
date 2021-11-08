# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

from gluon.custom_import import track_changes

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

showGuideLines = myconf.get("menu.guidelines", default=False)


# Appends developers menu (web2py)
def _DevMenu():
    app = request.application
    ctr = request.controller
    # txtMenu = IMG(_title=T('Development'), _alt=T('Devel.'), _src=URL(c='static', f='images/devel.png'), _class='pci-menuImage')
    txtMenu = SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-qrcode"), T("Development"))
    return [
        (
            txtMenu,
            False,
            "#",
            [
                (T("Current GIT version"), False, URL("about", "version", user_signature=True)),
                (T("TEST: Recommenders country map"), False, URL("maps", "recommenders_map", user_signature=True)),
                (T("TEST: Redirection"), False, URL("admin", "testRedir", user_signature=True)),
                # LI(_class="divider"),
                # (T('Restart daemon'), False, URL('admin', 'restart_daemon')),
                LI(_class="divider"),
                (T("Design"), False, URL("admin", "default", "design/%s" % app)),
                LI(_class="divider"),
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
                # (T('Shrink article images'), False, URL('admin', 'resizeAllArticleImages')),
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
    isArticleActive = False
    if ctr == "articles":
        isArticleActive = True

    tracking = myconf.get("config.tracking", default=False)

    articleMenu = [
        (SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-search"), T("Search articles")), False, URL("articles", "recommended_articles")),
        (SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-book"), T("All recommended articles")), False, URL("articles", "all_recommended_articles")),
    ]

    if tracking:
        articleMenu.append((SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-tasks"), T("Progress log")), False, URL("articles", "tracking")))

    if footerMenu:
        homeLink = (SPAN(I(_class="glyphicon glyphicon-home"), T("Home")), isHomeActive, URL("default", "index"))
    else:
        homeLink = (IMG(_style="height:40px", _src=URL(c="static", f="images/small-background.png")), isHomeActive, URL("default", "index"))

    menuBar = [
        homeLink,
        # (T(u'🔍 Search'), False, URL('articles', 'recommended_articles')),
        (SPAN(I(_class="glyphicon glyphicon-book"), T("Articles")), isArticleActive, "#", articleMenu),
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
        (T("test delete mail"), False, URL("alerts", "testDeleteMail", user_signature=True)),
        (T("Send newsletter now"), False, URL("alerts", "sendNewsletterMails", user_signature=True)),
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
    ctr = request.controller
    isActive = False
    if ctr == "admin":
        isActive = True

    adminMenu = [
        (SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-user"), T("Users & roles")), False, URL("admin", "list_users", user_signature=True)),
        # (T('Images'),            False, URL('admin', 'manage_images', user_signature=True)),
        (SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-list-alt"), T("Synthesis of reviews")), False, URL("admin", "recap_reviews", user_signature=True)),
        (
            SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-education"), T("All recommendation citations")),
            False,
            URL("admin", "allRecommCitations", user_signature=True),
        ),
        (SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-duplicate"), T("Recommendation PDF files")), False, URL("admin", "manage_pdf", user_signature=True)),
        (SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-send"), T("Mailing queue")), False, URL("admin", "mailing_queue", user_signature=True)),
        (
                SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-send"), T("Mailing queue Search")),
                False,
                URL("admin", "mailing_queue", vars=dict(searchable=True), user_signature=True),
        ),    
        LI(_class="divider"),
        (SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-tags"), T("Thematic fields")), False, URL("admin", "thematics_list", user_signature=True)),
        (SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-bookmark"), T("Status of articles")), False, URL("admin", "article_status", user_signature=True)),
        (SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-question-sign"), T("Help texts")), False, URL("custom_text", "help_texts", user_signature=True)),
        (SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-envelope"), T("E-mail templates")), False, URL("custom_help_text", "mail_templates", user_signature=True)),
        LI(_class="divider"),
        (SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-earphone"), T("Contact lists")), False, URL("admin", "mailing_lists", user_signature=True))
    ]

    return [
        (SPAN(I(_class="glyphicon glyphicon-cog"), T("Admin"), _class="pci-admin"), isActive, "#", adminMenu),
    ]


# Appends personnal menu
def _UserMenu():
    ctr = request.controller
    isActive = False
    if ctr == "user":
        isActive = True

    myContributionsMenu = []
    nRevOngoing = 0
    nRevTot = 0
    revClass = ""
    contribMenuClass = ""
    notificationPin = ""
    # reviews
    # (gab) proposition :

    # pending reviews, if any
    nRevPend = db(
        (db.t_reviews.reviewer_id == auth.user_id)
        & (db.t_reviews.review_state == "Awaiting response")
        & (db.t_reviews.recommendation_id == db.t_recommendations.id)
        & (db.t_recommendations.article_id == db.t_articles.id)
        & (db.t_articles.status == "Under consideration")
    ).count()

    txtRevPend = SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-envelope"), T("%s Invitation(s) to review a preprint") % nRevPend, _class="pci-recommender")

    if nRevPend > 0:
        txtRevPend = SPAN(txtRevPend, _class="pci-enhancedMenuItem")
        contribMenuClass = "pci-enhancedMenuItem"
        notificationPin = DIV(nRevPend, _class="pci2-notif-pin")

    myContributionsMenu.append((txtRevPend, False, URL("user", "my_reviews", vars=dict(pendingOnly=True), user_signature=True)))

    nWaitingForReviewer = db((db.t_articles.is_searching_reviewers == True) & (db.t_articles.status == "Under consideration")).count()
    txtWaitingForReviewer = SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-inbox"), T("%s Preprint(s) in need of reviewers") % nWaitingForReviewer)
    if nWaitingForReviewer > 0:
        txtWaitingForReviewer = SPAN(txtWaitingForReviewer, _class="pci-enhancedMenuItem")
        contribMenuClass = "pci-enhancedMenuItem"

    myContributionsMenu.append((txtWaitingForReviewer, False, URL("user", "articles_awaiting_reviewers", user_signature=True)))

    myContributionsMenu.append(
        (SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-edit"), T("Submit a preprint")), False, URL("user", "new_submission", user_signature=True))
    )
    myContributionsMenu.append(LI(_class="divider"))

    nRevTot = db((db.t_reviews.reviewer_id == auth.user_id)).count()
    nRevOngoing = db((db.t_reviews.reviewer_id == auth.user_id) & (db.t_reviews.review_state == "Awaiting review")).count()
    if nRevOngoing > 0:
        revClass = "pci-enhancedMenuItem"
        contribMenuClass = "pci-enhancedMenuItem"
    if nRevTot > 0:
        myContributionsMenu.append(
            (
                SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-eye-open"), T("Your reviews"), _class=revClass),
                False,
                URL("user", "my_reviews", vars=dict(pendingOnly=False), user_signature=True),
            )
        )

    nRevisions = db((db.t_articles.user_id == auth.user_id) & (db.t_articles.status == "Awaiting revision")).count()
    if nRevisions > 0:
        myContributionsMenu.append(
            (
                (SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-duplicate"), T("Your submitted preprints"), _class="pci-enhancedMenuItem")),
                False,
                URL("user", "my_articles", user_signature=True),
            )
        )
        contribMenuClass = "pci-enhancedMenuItem"
    else:
        myContributionsMenu.append(
            (SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-duplicate"), T("Your submitted preprints")), False, URL("user", "my_articles", user_signature=True))
        )

    return [
        (SPAN(I(_class="glyphicon glyphicon-edit"), T("For contributors"), notificationPin, _class=contribMenuClass), isActive, "#", myContributionsMenu),
    ]


def _RecommendationMenu():
    ctr = request.controller
    isActive = False

    notificationPin = ""

    if ctr == "recommender":
        isActive = True

    recommendationsMenu = []
    colorRequests = False
    nPostprintsOngoing = 0
    nPreprintsOngoing = 0

    # recommendations

    nPreprintsRecomPend = db(
        (db.t_articles.status == "Awaiting consideration")
        & (db.t_articles._id == db.t_suggested_recommenders.article_id)
        & (db.t_suggested_recommenders.suggested_recommender_id == auth.user_id)
        & (db.t_suggested_recommenders.declined == False)
    ).count()
    # (gab) proposition à la place de :
    txtPreprintsRecomPend = SPAN(
        I(_class="pci2-icon-margin-right glyphicon glyphicon-envelope"), T("%s Request(s) to handle a preprint") % nPreprintsRecomPend, _class="pci-recommender"
    )
    # txtPreprintsRecomPend = SPAN('Do you agree to initiate a recommendation?', _class='pci-recommender')

    if nPreprintsRecomPend > 0:
        txtPreprintsRecomPend = SPAN(txtPreprintsRecomPend, _class="pci-enhancedMenuItem")
        colorRequests = True
        notificationPin = DIV(nPreprintsRecomPend, _class="pci2-notif-pin")

    recommendationsMenu.append((txtPreprintsRecomPend, False, URL("recommender", "my_awaiting_articles", vars=dict(pendingOnly=True, pressReviews=False), user_signature=True)))

    nPreprintsOngoing = db(
        (db.t_recommendations.recommender_id == auth.user_id)
        & (db.t_recommendations.article_id == db.t_articles.id)
        & ~(db.t_articles.already_published == True)
        & (db.t_articles.status == "Under consideration")
    ).count()
    if nPreprintsOngoing > 0:
        classPreprintsOngoing = "pci-enhancedMenuItem"
        colorRequests = True
    else:
        classPreprintsOngoing = ""

    nPostprintsOngoing = db(
        (db.t_recommendations.recommender_id == auth.user_id)
        & (db.t_recommendations.article_id == db.t_articles.id)
        & (db.t_articles.already_published == True)
        & (db.t_articles.status == "Under consideration")
    ).count()
    if nPostprintsOngoing > 0:
        classPostprintsOngoing = "pci-enhancedMenuItem"
        colorRequests = True
    else:
        classPostprintsOngoing = ""

    nPreprintsRequireRecomm = db((db.t_articles.status == "Awaiting consideration")).count()
    if nPreprintsRequireRecomm > 0:
        classPreprintsRequireRecomm = "pci-enhancedMenuItem"
    else:
        classPreprintsRequireRecomm = ""

    recommendationsMenu.append(
        (
            SPAN(
                SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-inbox"), T("Preprint(s) in need of a recommender"), _class="pci-recommender"),
                _class=classPreprintsRequireRecomm,
            ),
            False,
            URL("recommender", "fields_awaiting_articles", user_signature=True),
        )
    )

    if not pciRRactivated:
        recommendationsMenu.append(
            (SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-edit"), T("Recommend a postprint")), False, URL("recommender", "new_submission", user_signature=True))
        )

    recommendationsMenu.append(LI(_class="divider"))
    recommendationsMenu.append(
        (
            SPAN(
                SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-education"), T("Preprint(s) you are handling"), _class="pci-recommender"), _class=classPreprintsOngoing,
            ),
            False,
            URL("recommender", "my_recommendations", vars=dict(pressReviews=False), user_signature=True),
        )
    )
    recommendationsMenu.append(
        (
            SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-link"), T("Preprint(s) you are co-handling"), _class="pci-recommender"),
            False,
            URL("recommender", "my_co_recommendations", vars=dict(pendingOnly=False), user_signature=True),
        )
    )

    if not pciRRactivated:
        recommendationsMenu.append(
            (
                SPAN(
                    SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-certificate"), T("Your recommendations of postprints"), _class="pci-recommender"),
                    _class=classPostprintsOngoing,
                ),
                False,
                URL("recommender", "my_recommendations", vars=dict(pressReviews=True), user_signature=True),
            )
        )

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
    if ctr == "manager":
        isActive = True

    txtMenu = SPAN(I(_class="glyphicon glyphicon-th-list"), T("For managers"))

    nbPend = db(db.t_articles.status.belongs(("Pending", "Pre-recommended", "Pre-recommended-private", "Pre-revision", "Pre-rejected"))).count()
    txtPending = str(nbPend) + " " + (T("Pending validation(s)"))
    if nbPend > 0:
        txtPending = SPAN(SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-time"), txtPending, _class="pci-enhancedMenuItem"), _class="pci-manager")
        txtMenu = SPAN(I(_class="glyphicon glyphicon-th-list"), T("For managers"), _class="pci-enhancedMenuItem")
        notificationPin = DIV(nbPend, _class="pci2-notif-pin")

    nbGoing = db(db.t_articles.status.belongs(("Under consideration", "Awaiting revision", "Awaiting consideration"))).count()
    txtGoing = str(nbGoing) + " " + (T("Handling process(es) underway"))
    if nbGoing > 0:
        txtGoing = SPAN(SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-refresh"), txtGoing, _class="pci-enhancedMenuItem"), _class="pci-manager")
        txtMenu = SPAN(I(_class="glyphicon glyphicon-th-list"), T("For managers"), _class="pci-enhancedMenuItem")

    return [
        (
            SPAN(txtMenu, notificationPin, _class="pci-manager"),
            isActive,
            "#",
            [
                (txtPending, False, URL("manager", "pending_articles", user_signature=True)),
                (txtGoing, False, URL("manager", "ongoing_articles", user_signature=True)),
                (
                    SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-education"), T("Perform tasks in place of recommenders")),
                    False,
                    URL("manager", "all_recommendations", user_signature=True),
                ),
                (
                    SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-ok-sign"), T("Handling process(es) completed"), _class="pci-manager"),
                    False,
                    URL("manager", "completed_articles", user_signature=True),
                ),
                (
                    SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-book"), T("All articles"), _class="pci-manager"),
                    False,
                    URL("manager", "all_articles", user_signature=True),
                ),
                (
                    SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-comment"), T("Comments"), _class="pci-manager"),
                    False,
                    URL("manager", "manage_comments", user_signature=True),
                ),
            ],
        ),
    ]


def _AboutMenu():
    aboutMenu = [
        menu_entry("About", "glyphicon-text-color", URL("about", "about")),
    ]

    if not pciRRactivated: aboutMenu += [
        menu_entry("PCI and journals", "glyphicon-file", "https://peercommunityin.org/pci-and-journals/"),
    ]

    aboutMenu += [
        menu_entry("Recommenders", "glyphicon-thumbs-up", URL("about", "recommenders")),
        menu_entry("Thanks to Reviewers", "glyphicon-heart", URL("about", "thanks_to_reviewers")),
        menu_entry("Code of Conduct", "glyphicon-list-alt", URL("about", "ethics")),
        menu_entry("Contact & Credits", "glyphicon-envelope", URL("about", "contact")),
        menu_entry("General Terms of Use", "glyphicon-wrench", URL("about", "gtu")),
    ]

    return [(SPAN(I(_class="glyphicon glyphicon-info-sign"), T("About")), True, "#", aboutMenu)]


def _HelpMenu():
    helpMenu = [
        menu_entry("How does it work?", "glyphicon-wrench", URL("help", "help_generic")),
        menu_entry("Guide for Authors", "glyphicon-book", URL("help", "guide_for_authors")),
        menu_entry("Guide for Reviewers", "glyphicon-book", URL("help", "guide_for_reviewers")),
        menu_entry("Guide for Recommenders", "glyphicon-book", URL("help", "guide_for_recommenders")),
        menu_entry("Become a Recommender", "glyphicon-user", URL("help", "become_a_recommenders")),
        menu_entry("How to...?", "glyphicon-wrench", URL("help", "help_practical")),
        menu_entry("FAQs", "glyphicon-question-sign", URL("help", "faq")),
        menu_entry("How should you cite an article?", "glyphicon-pencil", URL("help", "cite")),
    ]

    return [(SPAN(I(_class="glyphicon glyphicon-question-sign"), T("Help")), True, "#", helpMenu)]


def _AccountMenu():
    ctr = request.controller
    fct = request.function
    isActive = False
    if ctr == "default" and fct == "user":
        isActive = True

    txtMenu = SPAN(I(_class="glyphicon glyphicon-log-in"), T("Log in"), _class="pci-enhancedMenuItem")
    auth_menu = []

    if auth.is_logged_in():
        txtMenu = SPAN(I(_class="glyphicon glyphicon-user"), B(auth.user.first_name))

        auth_menu += [
            (
                SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-briefcase"), T("Public page")),
                False,
                URL(c="public", f="user_public_page", vars=dict(userId=auth.user.id)),
            ),
            LI(_class="divider"),
            (SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-user"), T("Profile")), False, URL("default", "user/profile", user_signature=True)),
            (SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-lock"), T("Change password")), False, URL("default", "user/change_password", user_signature=True)),
            (SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-envelope"), T("Change e-mail address")), False, URL("default", "change_email", user_signature=True)),
            LI(_class="divider"),
            (SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-off"), T("Log out")), False, URL("default", "user/logout", user_signature=True)),
        ]
    else:
        auth_menu += [
            (SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-log-in"), T("Log in")), False, URL("default", "user/login", user_signature=True)),
            (SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-edit"), T("Sign up")), False, URL("default", "user/register", user_signature=True)),
        ]

    return [(SPAN(txtMenu, _class="pci-manager"), isActive, "#", auth_menu)]


def menu_entry(text, icon, url):
    return (SPAN(I(_class="pci2-icon-margin-right glyphicon " + icon), T(text)), False, url)


def divider():
    return LI(_class="divider")


response.menu = _BaseMenu()
response.footer_menu = _BaseMenu(footerMenu=True)


if auth.is_logged_in():
    response.menu += _UserMenu()
    response.footer_menu += _UserMenu()

if auth.has_membership(None, None, "recommender"):
    response.menu += _RecommendationMenu()
    response.footer_menu += _RecommendationMenu()

if auth.has_membership(None, None, "manager"):
    response.menu += _ManagerMenu()
    response.footer_menu += _ManagerMenu()

if auth.has_membership(None, None, "administrator") or auth.has_membership(None, None, "developer"):
    response.menu += _AdminMenu()
    response.footer_menu += _AdminMenu()

if auth.has_membership(None, None, "administrator") or auth.has_membership(None, None, "developer"):
    response.menu += _ToolsMenu()
    response.footer_menu += _ToolsMenu()

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


#

