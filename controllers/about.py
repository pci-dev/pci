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
from controller_modules import adjust_grid

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
        elif myVar == "exclude":
            myValue = myVars[myVar]
            myValue = myValue.split(",") if type(myValue) is str else myValue
            excludeList = list(map(int, myValue))

    temp_db = DAL("sqlite:memory")
    qy_recomm = temp_db.define_table(
        "qy_recomm",
        Field("id", type="integer"),
        Field("num", type="integer"),
        Field("roles", type="string"),
        Field("score", type="double", label=T("Score"), default=0),
        Field("first_name", type="string", length=128, label=T("First name")),
        Field("last_name", type="string", length=128, label=T("Last name")),
        Field("uploaded_picture", type="upload", uploadfield="picture_data", label=T("Picture")),
        Field("city", type="string", label=T("City"), represent=lambda t, r: t if t else ""),
        Field("country", type="string", label=T("Country"), represent=lambda t, r: t if t else ""),
        Field("laboratory", type="string", label=T("Department"), represent=lambda t, r: t if t else ""),
        Field("thematics", type="string", label=T("Thematic Fields"), requires=IS_IN_DB(db, db.t_thematics.keyword, zero=None)),
        Field("keywords", type="string", label=T("Keywords")),
        Field("expertise", type="string", label=T("Areas of expertise")),
        Field("excluded", type="boolean", label=T("Excluded")),
        Field("any", type="string", label=T("All fields")),
    )
    qyKwArr = qyKw.split(" ")

    qyTF = []
    for thema in db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword):
        qyTF.append(thema.keyword)

    filtered = db.executesql("SELECT * FROM search_recommenders(%s, %s, %s) ORDER BY last_name, first_name;", placeholders=[qyTF, qyKwArr, excludeList], as_dict=True)

    full_text_search_fields = [
        'first_name',
        'last_name',
        'laboratory',
        'city',
        'country',
        'thematics',
        'expertise',
        "keywords",
    ]

    users_ids = [ fr['id'] for fr in filtered ]
    keywords = { user.id: user.keywords for user in db(db.auth_user.id.belongs(users_ids)).select() }
    expertise = { user.id: user.cv for user in db(db.auth_user.id.belongs(users_ids)).select() }
    for fr in filtered:
        fr['keywords'] = keywords[fr['id']] or ""
        fr['expertise'] = expertise[fr['id']] or ""
        qy_recomm.insert(**fr, any=" ".join([str(fr[k]) if k in full_text_search_fields else "" for k in fr]))

    links = []

    temp_db.qy_recomm.uploaded_picture.readable = False
    temp_db.qy_recomm.num.readable = False
    temp_db.qy_recomm.roles.readable = False
    temp_db.qy_recomm.score.readable = False
    temp_db.qy_recomm.excluded.readable = False
    selectable = None

    original_grid = SQLFORM.smartgrid(
        qy_recomm,
        editable=False,
        deletable=False,
        create=False,
        details=False,
        searchable=dict(auth_user=True, auth_membership=False),
        selectable=selectable,
        maxtextlength=250,
        paginate=1000,
        csv=csv,
        exportclasses=expClass,
        fields=[
            temp_db.qy_recomm._id,
            temp_db.qy_recomm.num,
            temp_db.qy_recomm.score,
            temp_db.qy_recomm.uploaded_picture,
            temp_db.qy_recomm.first_name,
            temp_db.qy_recomm.last_name,
            temp_db.qy_recomm.laboratory,
            temp_db.qy_recomm.city,
            temp_db.qy_recomm.country,
            temp_db.qy_recomm.thematics,
            temp_db.qy_recomm.excluded,
        ],
        links=links,
        orderby=temp_db.qy_recomm.num,
        _class="web2py_grid action-button-absolute",
    )

    # options to be removed from the search dropdown:
    remove_options = ['qy_recomm.id']

    # the grid is adjusted after creation to adhere to our requirements
    grid = adjust_grid.adjust_grid_basic(original_grid, 'recommenders', remove_options)

    response.view = "default/gab_list_layout.html"

    return dict(
        pageTitle=getTitle(request, auth, db, "#PublicRecommendationBoardTitle"),
        customText=getText(request, auth, db, "#PublicRecommendationBoardText"),
        pageHelp=getHelp(request, auth, db, "#PublicRecommendationBoardDescription"),
        grid=grid,
    )
