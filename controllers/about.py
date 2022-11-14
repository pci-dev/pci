# -*- coding: utf-8 -*-
import os
from subprocess import Popen, PIPE, STDOUT

# import os.path
import re
from gluon.custom_import import track_changes
from gluon.storage import Storage

track_changes(True)  # reimport module if changed; disable in production
# from app_modules.common import mkPanel
from app_modules.helper import *

from app_components import app_forms
from app_modules import common_tools
from app_modules import common_small_html

from gluon.contrib.appconfig import AppConfig

myconf = AppConfig(reload=True)

csv = False  # no export allowed
expClass = None  # dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)

pciRRactivated = myconf.get("config.registered_reports", default=False)

######################################################################################################################################################################
## Routes
######################################################################################################################################################################
def index():
    return about()

def version():
    pageTitle = getTitle(request, auth, db, "#VersionTitle")
    customText = getText(request, auth, db, "#VersionInfo")
    opt = "--decorate --decorate-refs-exclude remotes/origin/*"
    version = _run(f"git log {opt} --oneline HEAD -1")

    response.view = "default/info.html"
    return dict(pageTitle=pageTitle, customText=customText, message=version, shareable=False, currentUrl=URL(c="about", f="version", host=host, scheme=scheme, port=port))


def _run(command):
    return "".join(
        Popen(
            command.split(" "),
            cwd=request.folder,
            stdout=PIPE,
            stderr=STDOUT,
            encoding="utf-8",
        )
        .stdout
        .readlines()
    )


######################################################################################################################################################################
def ethics():
    pageTitle = getTitle(request, auth, db, "#EthicsTitle")
    customText = getText(request, auth, db, "#EthicsInfo")
    message = ""
    tweeterAcc = myconf.get("social.tweeter")
    if auth.user_id:
        if db.auth_user[auth.user_id].ethical_code_approved:
            message = DIV(B(T("You have agreed to comply with this code of conduct"), _style="color:green;"), _style="text-align:center; margin:32px;")
        else:
            pageTitle = DIV(H1("Before login, you must agree to comply with the code of conduct"), pageTitle,)
            message = FORM(
                DIV(
                    SPAN(
                        INPUT(_type="checkbox", _name="ethics_approved", _id="ethics_approved", _value="yes", value=False),
                        LABEL(T("Yes, I agree to comply with this code of conduct")),
                    ),
                    _style="padding:16px;",
                ),
                INPUT(_type="submit", _value=T("Set in my profile"), _class="btn btn-info"),
                _action=URL("user_actions", "validate_ethics", vars=request.vars),
                _style="text-align:center;",
            )

    response.view = "default/info.html"
    return dict(
        pageTitle=pageTitle,
        customText=customText,
        message=message,
        shareable=True,
        currentUrl=URL(c="about", f="ethics", host=host, scheme=scheme, port=port),
        tweeterAcc=tweeterAcc,
        pciRRactivated=pciRRactivated,
    )


######################################################################################################################################################################
def rss_info():
    url = _rss_url()
    img = IMG(_src=URL(c="about", f="rss_flashcode"), _alt="flashcode", _style="margin-left:32px;")

    aurl = DIV(A(url, _href=url), img, _style="text-align:center")

    response.view = "default/info.html"
    return dict(pageTitle=getTitle(request, auth, db, "#RssTitle"), customText=getText(request, auth, db, "#RssInfo"), message=aurl)


def rss_flashcode():
    import treepoem
    import io

    fmt = "png"
    buf = io.BytesIO()
    treepoem.generate_barcode(
        barcode_type="datamatrix",
        data=_rss_url(),
    ).save(buf, fmt)

    response.headers['Content-Type'] = f"image/{fmt}"
    return buf.getvalue()


def _rss_url():
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    url = URL(c="rss", f="rss", scheme=scheme, host=host, port=port)
    return url


######################################################################################################################################################################
## Keep for future use?
def social():
    frames = []
    tweeterAcc = myconf.get("social.tweeter")
    if tweeterAcc:
        frames.append(H2("Twitter"))
        frames.append(
            DIV(
                XML(
                    '<a class="twitter-timeline" href="https://twitter.com/%(tweeterAcc)s">Tweets by %(tweeterAcc)s</a> <script async src="//platform.twitter.com/widgets.js" charset="utf-8"></script>'
                    % (locals())
                ),
                _class="tweeterPanel",
            )
        )

    # facebookAcc = myconf.get('social.facebook')
    # if facebookAcc:
    # frames.append(H2('Facebook'))
    # frames.append(DIV(XML('<div class="fb-page" data-href="https://www.facebook.com/%s" data-tabs="timeline" data-width=500 data-small-header="true" data-hide-cover="false" data-show-facepile="true"><blockquote cite="https://www.facebook.com/%s" class="fb-xfbml-parse-ignore"><a href="https://www.facebook.com/%s">%s</a></blockquote></div>' % (facebookAcc,facebookAcc,facebookAcc,myconf.get('app.description'))), _class='facebookPanel'))

    response.view = "default/info.html"
    return dict(
        pageTitle=getTitle(request, auth, db, "#SocialTitle"),
        customText=getText(request, auth, db, "#SocialInfo"),
        message=DIV(frames, _class="pci-socialDiv"),
        facebook=True,
        shareable=True,
        currentUrl=URL(c="about", f="social", host=host, scheme=scheme, port=port),
        pciRRactivated=pciRRactivated,
    )


######################################################################################################################################################################
def gtu():
    tweeterAcc = myconf.get("social.tweeter")
    response.view = "default/info.html"
    return dict(
        pageTitle=getTitle(request, auth, db, "#GtuTitle"),
        customText=getText(request, auth, db, "#GtuInfo"),
        shareable=True,
        currentUrl=URL(c="about", f="gtu", host=host, scheme=scheme, port=port),
        tweeterAcc=tweeterAcc,
        pciRRactivated=pciRRactivated,
    )


######################################################################################################################################################################
def about():
    tweeterAcc = myconf.get("social.tweeter")
    response.view = "default/info.html"
    return dict(
        pageTitle=getTitle(request, auth, db, "#AboutTitle"),
        customText=getText(request, auth, db, "#AboutInfo"),
        shareable=True,
        currentUrl=URL(c="about", f="about", host=host, scheme=scheme, port=port),
        tweeterAcc=tweeterAcc,
        pciRRactivated=pciRRactivated,
    )


######################################################################################################################################################################
def contact():
    tweeterAcc = myconf.get("social.tweeter")
    response.view = "default/info.html"
    return dict(
        pageTitle=getTitle(request, auth, db, "#ContactTitle"),
        customText=getText(request, auth, db, "#ContactInfo"),
        shareable=True,
        currentUrl=URL(c="about", f="contact", host=host, scheme=scheme, port=port),
        tweeterAcc=tweeterAcc,
        pciRRactivated=pciRRactivated,
    )


######################################################################################################################################################################
def buzz():
    response.view = "default/info.html"
    return dict(
        pageTitle=getTitle(request, auth, db, "#BuzzTitle"),
        customText=getText(request, auth, db, "#BuzzInfo"),
        shareable=True,
        currentUrl=URL(c="about", f="buzz", host=host, scheme=scheme, port=port),
        pciRRactivated=pciRRactivated,
    )


######################################################################################################################################################################
def thanks_to_reviewers():
    tweeterAcc = myconf.get("social.tweeter")
    response.view = "default/info.html"
    return dict(
        pageTitle=getTitle(request, auth, db, "#ThanksToReviewersTitle"),
        customText=getText(request, auth, db, "#ThanksToReviewersInfo"),
        tweeterAcc=tweeterAcc,
    )


######################################################################################################################################################################
def full_policies():
    response.view = "default/info.html"
    return dict(pageTitle=getTitle(request, auth, db, "#FullPoliciesTitle"), customText=getText(request, auth, db, "#FullPoliciesInfo"),)


######################################################################################################################################################################
def pci_partners():
    redirect("https://peercommunityin.org/pci-and-journals/")


######################################################################################################################################################################
def pci_rr_friendly_journals():
    response.view = "default/info.html"
    return dict(pageTitle=getTitle(request, auth, db, "#PciRRFriendlyJournalsTitle"), customText=getText(request, auth, db, "#PciRRFriendlyJournalsInfo"),)


######################################################################################################################################################################
def pci_rr_interested_journals():
    response.view = "default/info.html"
    return dict(pageTitle=getTitle(request, auth, db, "#PciRRInterestedJournalsTitle"), customText=getText(request, auth, db, "#PciRRInterestedJournalsInfo"),)


######################################################################################################################################################################
def become_journal_adopter():
    response.view = "default/info.html"
    return dict(pageTitle=getTitle(request, auth, db, "#BecomeJournalAdopterTitle"), customText=getText(request, auth, db, "#BecomeJournalAdopterInfo"),)


######################################################################################################################################################################
def journal_adopter_faq():
    response.view = "default/info.html"
    return dict(pageTitle=getTitle(request, auth, db, "#JournalAdopterFaqTitle"), customText=getText(request, auth, db, "#JournalAdopterFaqInfo"),)


######################################################################################################################################################################
def recommenders():
    myVars = request.vars
    qyKw = ""
    qyTF = []
    excludeList = []
    for myVar in myVars:
        if isinstance(myVars[myVar], list):
            myValue = (myVars[myVar])[1]
        else:
            myValue = myVars[myVar]
        if myVar == "qyKeywords":
            qyKw = myValue
        elif re.match("^qy_", myVar) and myValue == "on":
            qyTF.append(re.sub(r"^qy_", "", myVar))
    qyKwArr = qyKw.split(" ")

    searchForm = app_forms.searchByThematic(auth, db, myVars)
    if searchForm.process(keepvalues=True).accepted:
        response.flash = None
    else:
        qyTF = []
        for thema in db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword):
            qyTF.append(thema.keyword)

    filtered = db.executesql("SELECT * FROM search_recommenders(%s, %s, %s) ORDER BY last_name, first_name;", placeholders=[qyTF, qyKwArr, excludeList], as_dict=True)
    myRows = []
    my1 = ""
    myIdx = []
    nbRecomm = len(filtered)
    for fr in filtered:
        sfr = Storage(fr)
        if sfr.last_name and sfr.last_name[0].upper() != my1:
            my1 = sfr.last_name[0].upper()
            myRows.append(TR(TD(my1, A(_name=my1)), TD(""), _class="pci-capitals"))
            myIdx.append(A(my1, _href="#%s" % my1, _style="margin-right:20px;"))
        myRows.append(common_small_html.mkUserRow(auth, db, sfr, withMail=False, withRoles=False, withPicture=False))
    grid = DIV(
        HR(),
        DIV(nbRecomm + T(" recommenders selected"), _style="text-align:center; margin-bottom:20px;"),
        LABEL(T("Quick access: "), _style="margin-right:20px;"),
        SPAN(myIdx, _class="pci-capitals"),
        HR(),
        TABLE(THEAD(TR(TH(T("Name")), TH(T("Affiliation")))), TBODY(myRows), _class="web2py_grid pci-UsersTable"),
        _class="pci2-flex-column pci2-flex-center recommender-list-front",
    )

    response.view = "default/gab_list_layout.html"
    return dict(
        pageTitle=getTitle(request, auth, db, "#PublicRecommendationBoardTitle"),
        customText=getText(request, auth, db, "#PublicRecommendationBoardText"),
        pageHelp=getHelp(request, auth, db, "#PublicRecommendationBoardDescription"),
        searchForm=searchForm,
        grid=grid,
    )
