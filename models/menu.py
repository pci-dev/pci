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
        menu_entry("Search articles", "glyphicon-search", URL("articles", "recommended_articles")),
        menu_entry("All recommended articles", "glyphicon-book", URL("articles", "all_recommended_articles")),
    ]

    if tracking: articleMenu += [
        menu_entry("Progress log", "glyphicon-tasks", URL("articles", "tracking")),
    ]

    if footerMenu:
        homeLink = (IMG(_style="", _src=URL(c="static", f="images/pci-logo.svg")), isHomeActive, URL("default", "index"))
    else:
        homeLink = (IMG(_style="height:40px", _src=URL(c="static", f="images/small-background.png")), isHomeActive, URL("default", "index"))

    menuBar = [
        homeLink,
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
        (T("Delete trapped e-mails"), False, URL("admin_actions", "delete_trapped_emails")),
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
        menu_entry("Users & roles", "glyphicon-user", URL("admin", "list_users", user_signature=True)),
        menu_entry("Synthesis of reviews", "glyphicon-list-alt", URL("admin", "recap_reviews", user_signature=True)),
        menu_entry("All recommendation citations", "glyphicon-education", URL("admin", "allRecommCitations", user_signature=True)),
        menu_entry("Recommendation PDF files", "glyphicon-duplicate", URL("admin", "manage_pdf", user_signature=True)),
        menu_entry("Mailing queue", "glyphicon-send", URL("admin", "mailing_queue", user_signature=True)),
        menu_entry("Mailing queue Search", "glyphicon-send", URL("admin", "mailing_queue", vars=dict(searchable=True), user_signature=True)),
        divider(),
        menu_entry("Thematic fields", "glyphicon-tags", URL("admin", "thematics_list", user_signature=True)),
        menu_entry("Status of articles", "glyphicon-bookmark", URL("admin", "article_status", user_signature=True)),
        menu_entry("Help texts", "glyphicon-question-sign", URL("custom_help_text", "help_texts", user_signature=True)),
        menu_entry("E-mail templates", "glyphicon-envelope", URL("custom_help_text", "mail_templates", user_signature=True)),
        divider(),
        menu_entry("Contact lists", "glyphicon-earphone", URL("admin", "mailing_lists", user_signature=True)),
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

    nRevPend = db(
        (db.t_reviews.reviewer_id == auth.user_id)
        & (db.t_reviews.review_state == "Awaiting response")
        & (db.t_reviews.recommendation_id == db.t_recommendations.id)
        & (db.t_recommendations.article_id == db.t_articles.id)
        & (db.t_articles.status == "Under consideration")
    ).count()

    txtRevPend = menu_entry_item(T("%s Invitation(s) to review a preprint") % nRevPend, "glyphicon-envelope", _class="pci-recommender")

    if nRevPend > 0:
        txtRevPend = SPAN(txtRevPend, _class="pci-enhancedMenuItem")
        contribMenuClass = "pci-enhancedMenuItem"
        notificationPin = DIV(nRevPend, _class="pci2-notif-pin")

    myContributionsMenu += [
        (txtRevPend, False, URL("user", "my_reviews", vars=dict(pendingOnly=True), user_signature=True)),
    ]

    nWaitingForReviewer = db((db.t_articles.is_searching_reviewers == True) & (db.t_articles.status == "Under consideration")).count()
    txtWaitingForReviewer = menu_entry_item(T("%s Preprint(s) in need of reviewers") % nWaitingForReviewer, "glyphicon-inbox")
    if nWaitingForReviewer > 0:
        txtWaitingForReviewer = SPAN(txtWaitingForReviewer, _class="pci-enhancedMenuItem")
        contribMenuClass = "pci-enhancedMenuItem"

    myContributionsMenu += [
        (txtWaitingForReviewer, False, URL("user", "articles_awaiting_reviewers", user_signature=True)),
        menu_entry("Submit a preprint", "glyphicon-edit", URL("user", "new_submission", user_signature=True)),
        divider(),
    ]

    nRevTot = db((db.t_reviews.reviewer_id == auth.user_id)).count()
    nRevOngoing = db((db.t_reviews.reviewer_id == auth.user_id) & (db.t_reviews.review_state == "Awaiting review")).count()
    nRevisions = db((db.t_articles.user_id == auth.user_id) & (db.t_articles.status == "Awaiting revision")).count()
    if nRevOngoing > 0:
        revClass = "pci-enhancedMenuItem"
        contribMenuClass = "pci-enhancedMenuItem"
    if nRevisions > 0:
        contribMenuClass = "pci-enhancedMenuItem"

    if nRevTot > 0: myContributionsMenu += [
        menu_entry("Your reviews", "glyphicon-eye-open", URL("user", "my_reviews", vars=dict(pendingOnly=False), user_signature=True), _class=revClass),
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

    if not pciRRactivated: recommendationsMenu += [
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
        menu_entry("Preprint(s) you are co-handling", "glyphicon-link",
            URL("recommender", "my_co_recommendations", vars=dict(pendingOnly=False), user_signature=True),
            _class="pci-recommender",
        ),
    ]

    if not pciRRactivated: recommendationsMenu += [
            (
                SPAN(
                    menu_entry_item("Your recommendations of postprints", "glyphicon-certificate", _class="pci-recommender"),
                    _class=classPostprintsOngoing,
                ),
                False,
                URL("recommender", "my_recommendations", vars=dict(pressReviews=True), user_signature=True),
            )
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
    if ctr == "manager":
        isActive = True

    txtMenu = SPAN(I(_class="glyphicon glyphicon-th-list"), T("For managers"))

    nbPend = db(db.t_articles.status.belongs(("Pending", "Pre-recommended", "Pre-recommended-private", "Pre-revision", "Pre-rejected"))).count()
    txtPending = str(nbPend) + " " + (T("Pending validation(s)"))
    if nbPend > 0:
        txtPending = SPAN(menu_entry_item(txtPending, "glyphicon-time", _class="pci-enhancedMenuItem"), _class="pci-manager")
        txtMenu = SPAN(I(_class="glyphicon glyphicon-th-list"), T("For managers"), _class="pci-enhancedMenuItem")
        notificationPin = DIV(nbPend, _class="pci2-notif-pin")

    nbGoing = db(db.t_articles.status.belongs(("Under consideration", "Awaiting revision", "Awaiting consideration"))).count()
    txtGoing = str(nbGoing) + " " + (T("Handling process(es) underway"))
    if nbGoing > 0:
        txtGoing = SPAN(menu_entry_item(txtGoing, "glyphicon-refresh", _class="pci-enhancedMenuItem"), _class="pci-manager")
        txtMenu = SPAN(I(_class="glyphicon glyphicon-th-list"), T("For managers"), _class="pci-enhancedMenuItem")

    return [
        (
            SPAN(txtMenu, notificationPin, _class="pci-manager"),
            isActive,
            "#",
            [
                (txtPending, False, URL("manager", "pending_articles", user_signature=True)),
                (txtGoing, False, URL("manager", "ongoing_articles", user_signature=True)),
                menu_entry("Perform tasks in place of recommenders", "glyphicon-education", URL("manager", "all_recommendations", user_signature=True)),
                menu_entry("Handling process(es) completed", "glyphicon-ok-sign", URL("manager", "completed_articles", user_signature=True), _class="pci-manager"),
                menu_entry("All articles", "glyphicon-book", URL("manager", "all_articles", user_signature=True), _class="pci-manager"),
                menu_entry("Comments", "glyphicon-comment", URL("manager", "manage_comments", user_signature=True), _class="pci-manager"),
            ],
        ),
    ]


def _AboutMenu():
    aboutMenu = [
        menu_entry("About", "glyphicon-text-color", URL("about", "about")),
    ]

    if not pciRRactivated: aboutMenu += [
        menu_entry("PCI and journals", "glyphicon-file", "https://peercommunityin.org/pci-and-journals/", new_window=True),
    ]

    if pciRRactivated: aboutMenu += [
        menu_entry("Full Policies and Procedures", "glyphicon-list-alt", URL("about", "full_policies")),
        divider(),
        menu_entry("List of PCI RR-friendly Journals", "glyphicon-file", URL("about", "pci_rr_friendly_journals")),
        menu_entry("List of PCI RR-interested Journals", "glyphicon-file", URL("about", "pci_rr_interested_journals")),
        menu_entry("Apply to become a Journal Adopter", "glyphicon-pencil", URL("about", "become_journal_adopter")),
        menu_entry("Journal Adopter FAQ", "glyphicon-question-sign", URL("about", "journal_adopter_faq")),
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
        txtMenu = SPAN(I(_class="glyphicon glyphicon-user"), B(auth.user.first_name))
    else:
        txtMenu = SPAN(I(_class="glyphicon glyphicon-log-in"), T("Log in"), _class="pci-enhancedMenuItem")

    auth_menu = []

    if auth.is_logged_in(): auth_menu += [
        menu_entry("Public page", "glyphicon-briefcase", URL(c="public", f="user_public_page", vars=dict(userId=auth.user.id))),
        divider(),
        menu_entry("Profile", "glyphicon-user", URL("default", "user/profile", user_signature=True)),
        menu_entry("Change password", "glyphicon-lock", URL("default", "user/change_password", user_signature=True)),
        menu_entry("Change e-mail address", "glyphicon-envelope", URL("default", "change_email", user_signature=True)),
        divider(),
        menu_entry("Log out", "glyphicon-off", URL("default", "user/logout", user_signature=True)),
    ]
    else: auth_menu += [
        menu_entry("Log in", "glyphicon-log-in", URL("default", "user/login", user_signature=True)),
        menu_entry("Sign up", "glyphicon-edit", URL("default", "user/register", user_signature=True)),
    ]

    return [(SPAN(txtMenu, _class="pci-manager"), isActive, "#", auth_menu)]


def menu_entry(text, icon, url, new_window=False, _class=None):
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
