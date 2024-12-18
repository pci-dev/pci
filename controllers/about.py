# -*- coding: utf-8 -*-
import datetime
from typing import Dict, List, Optional, Tuple
from gluon.custom_import import track_changes
from models.recommendation import Recommendation, RecommendationState
from models.review import Review, ReviewState
from models.user import User

track_changes(True)  # reimport module if changed; disable in production
# from app_modules.common import mkPanel
from app_modules.helper import *

from app_modules import common_tools
from app_modules.utils import run
from app_modules.orcid import OrcidTools
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
    pageTitle = getTitle("#VersionTitle")
    customText = getText("#VersionInfo")
    opt = "--decorate --decorate-refs-exclude remotes/origin/*"
    version = run(f"git log {opt} --oneline HEAD -1")

    response.view = "default/info.html"
    return dict(pageTitle=pageTitle, customText=customText, message=version, shareable=False, currentUrl=URL(c="about", f="version", host=host, scheme=scheme, port=port))


######################################################################################################################################################################
def ethics():
    pageTitle = getTitle("#EthicsTitle")
    customText = getText("#EthicsInfo")
    message = ""
    tweeterAcc = myconf.get("social.twitter")
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
    return dict(pageTitle=getTitle("#RssTitle"), customText=getText("#RssInfo"), message=aurl)


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
    tweeterAcc = myconf.get("social.twitter")
    mastodonAcc = myconf.get("social.mastodon")
    if tweeterAcc :
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
    if mastodonAcc and pciRRactivated:
        frames =[]
        frames.append(H2("Mastodon"))
        frames.append(
            DIV(
                XML(
                    '<a class="twitter-timeline" href="https://spore.social/%(mastodonAcc)s">Posts by %(mastodonAcc)s</a>'
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
        pageTitle=getTitle("#SocialTitle"),
        customText=getText("#SocialInfo"),
        message=DIV(frames, _class="pci-socialDiv"),
        facebook=True,
        shareable=True,
        currentUrl=URL(c="about", f="social", host=host, scheme=scheme, port=port),
        pciRRactivated=pciRRactivated,
    )


######################################################################################################################################################################
def gtu():
    tweeterAcc = myconf.get("social.twitter")
    response.view = "default/info.html"
    return dict(
        pageTitle=getTitle("#GtuTitle"),
        customText=getText("#GtuInfo"),
        shareable=True,
        currentUrl=URL(c="about", f="gtu", host=host, scheme=scheme, port=port),
        tweeterAcc=tweeterAcc,
        pciRRactivated=pciRRactivated,
    )


######################################################################################################################################################################
def about():
    tweeterAcc = myconf.get("social.twitter")
    response.view = "default/info.html"
    return dict(
        pageTitle=getTitle("#AboutTitle"),
        customText=getText("#AboutInfo"),
        shareable=True,
        currentUrl=URL(c="about", f="about", host=host, scheme=scheme, port=port),
        tweeterAcc=tweeterAcc,
        pciRRactivated=pciRRactivated,
    )


######################################################################################################################################################################
def contact():
    tweeterAcc = myconf.get("social.twitter")
    response.view = "default/info.html"
    return dict(
        pageTitle=getTitle("#ContactTitle"),
        customText=getText("#ContactInfo"),
        shareable=True,
        currentUrl=URL(c="about", f="contact", host=host, scheme=scheme, port=port),
        tweeterAcc=tweeterAcc,
        pciRRactivated=pciRRactivated,
    )


######################################################################################################################################################################
def buzz():
    response.view = "default/info.html"
    return dict(
        pageTitle=getTitle("#BuzzTitle"),
        customText=getText("#BuzzInfo"),
        shareable=True,
        currentUrl=URL(c="about", f="buzz", host=host, scheme=scheme, port=port),
        pciRRactivated=pciRRactivated,
    )


######################################################################################################################################################################
def thanks_to_reviewers():
    tweeterAcc = myconf.get("social.twitter")
    response.view = "default/info.html"
        
    years_reviews = _get_review_with_reviewer_by_year()

    html = DIV()
    for year in sorted(years_reviews.keys(), reverse=True):
        html.append(H2(year, _style="font-weight: bold; font-size: xx-large"))
        html_list_user = UL(_style="list-style: none; padding: 10px")

        nb_anonymous = 0
        user_ids: List[int] = []
        for review_user in years_reviews[year]:
            review = review_user[0]
            user = review_user[1]

            if user.id in user_ids:
                continue
            
            if (user.first_name and user.first_name.startswith('[Anon]')) or (user.last_name and user.last_name.startswith('[Anon]')):
                nb_anonymous += 1
                user_ids.append(user.id)
            elif not review.anonymously:
                user_ids.append(user.id)
                if user.first_name and user.last_name:
                    html_list_user.append(LI(user.last_name + ' ' + user.first_name))
                elif user.first_name:
                    html_list_user.append(LI(user.first_name))
                elif user.last_name:
                    html_list_user.append(LI(user.last_name))

        for review_user in years_reviews[year]:
            if review_user[1].id not in user_ids and review_user[0].anonymously:
                nb_anonymous += 1
                user_ids.append(review_user[1].id)
        
        if nb_anonymous > 0:
            html_list_user.append(BR())
            if nb_anonymous == 1:
                html_list_user.append(f'and 1 anonymous reviewer')
            else:
                html_list_user.append(f'and {nb_anonymous} anonymous reviewers')
        
        if len(user_ids) == 1:
            html.append(P('1 reviewers:', _style="font-weight: bold;"))
        else:
            html.append(P(f'{len(user_ids)} reviewers:', _style="font-weight: bold;"))
        
        html.append(html_list_user)

    return dict(
        pageTitle=getTitle("#ThanksToReviewersTitle"),
        customText=html,
        tweeterAcc=tweeterAcc,
    )

def _get_recommendation_dict():
    dict_id_recommendations: Dict[int, Recommendation] = {}
    recommendations = Recommendation.get_all([RecommendationState.RECOMMENDED])
    for recommendation in recommendations:
        if recommendation.validation_timestamp:
            dict_id_recommendations[recommendation.id] = recommendation
    return dict_id_recommendations

def _get_review_with_reviewer_by_year():
    years_reviews: Dict[int, List[Tuple[Review, User]]] = {}
    dict_id_recommendations = _get_recommendation_dict()

    reviews_users = Review.get_all_with_reviewer([ReviewState.REVIEW_COMPLETED])
    for review_user in reviews_users:
        review = review_user[0]
        review_date: Optional[datetime.datetime]
        if review.due_date:
            review_date = review.due_date
        else:
            review_date = Review.get_due_date_from_review_duration(review)

        if review_date > datetime.datetime.today():
            continue
        
        recommendation = dict_id_recommendations.get(review.recommendation_id)
        if recommendation and recommendation.validation_timestamp and review_date < recommendation.validation_timestamp:
            review_date = recommendation.validation_timestamp

        year = review_date.year
        if year not in years_reviews:
            years_reviews[year] = []
        years_reviews[year].append(review_user)
    
    return years_reviews

######################################################################################################################################################################
def full_policies():
    response.view = "default/info.html"
    return dict(pageTitle=getTitle("#FullPoliciesTitle"), customText=getText("#FullPoliciesInfo"),)


######################################################################################################################################################################
def pci_partners():
    redirect("https://peercommunityin.org/pci-and-journals/")


######################################################################################################################################################################
def pci_rr_friendly_journals():
    response.view = "default/info.html"
    return dict(pageTitle=getTitle("#PciRRFriendlyJournalsTitle"), customText=getText("#PciRRFriendlyJournalsInfo"),)


######################################################################################################################################################################
def pci_friendly_journals():
    response.view = "default/info.html"
    return dict(pageTitle=getTitle("#PciFriendlyJournalsTitle"), customText=getText("#PciFriendlyJournalsInfo"))


######################################################################################################################################################################
def pci_rr_interested_journals():
    response.view = "default/info.html"
    return dict(pageTitle=getTitle("#PciRRInterestedJournalsTitle"), customText=getText("#PciRRInterestedJournalsInfo"),)


######################################################################################################################################################################
def become_journal_adopter():
    response.view = "default/info.html"
    return dict(pageTitle=getTitle("#BecomeJournalAdopterTitle"), customText=getText("#BecomeJournalAdopterInfo"),)


######################################################################################################################################################################
def journal_adopter_faq():
    response.view = "default/info.html"
    return dict(pageTitle=getTitle("#JournalAdopterFaqTitle"), customText=getText("#JournalAdopterFaqInfo"),)


######################################################################################################################################################################
def recommenders():
    users = db.auth_user
    search_fields = [
        'first_name',
        'last_name',
        'laboratory',
        'institution',
        'city',
        'country',
        'thematics'
    ]

    users.thematics.label = "Thematics fields"
    users.thematics.type = "string"
    users.thematics.requires = IS_IN_DB(db, db.t_thematics.keyword, zero=None)

    users.last_name.label = 'Name'
    users.last_name.represent = lambda txt, row: mkName(row)

    users.laboratory.label = 'Affiliation'
    users.laboratory.represent = lambda txt, row: mkAffiliation(row)

    def mkName(row: ...):
        user_name = ''
        user = User.get_by_id(row.auth_user.id)
        if not user:
            return user_name
        
        if user.first_name:
            user_name += ' '.join([name.capitalize() for name in user.first_name.split(' ')])
        if user.last_name:
            if user.first_name:
                user_name += ' '
            user_name += user.last_name.upper()

        if user.deleted:
            return user_name
        else:
            user_name = OrcidTools.build_name_with_orcid(user_name, user.orcid)
            return A(user_name, _href=URL(c="public", f="user_public_page", vars=dict(userId=user.id)))

    def mkAffiliation(row):
        user = users[row.auth_user.id]
        return str(user.laboratory) + ', ' + str(user.institution) \
                + ', ' + str(user.city) + ', ' + str(user.country)

    for f in users.fields:
        users[f].readable = f in search_fields
    for f in db.auth_group:
        f.searchable = False
    for f in db.auth_membership:
        f.searchable = False

    query = (db.auth_user.id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group.id) & (db.auth_group.role == "recommender") & (db.auth_user.deleted == False)

    try:
      original_grid = SQLFORM.grid(
                    query,
                    create=False,
                    details=False,
                    editable=False,
                    deletable=False,
                    maxtextlength=250,
                    paginate=1000,
                    csv=csv,
                    exportclasses=expClass,
                    fields=[
                        users.id,
                        users.last_name,
                        users.laboratory,
                    ],
                    links=None,
                    orderby=users.last_name,
                    _class="web2py_grid action-button-absolute about-recommender",
                )
    except:
        raise HTTP(418, "I'm a teapot")

    # the grid is adjusted after creation to adhere to our requirements
    grid = adjust_grid.adjust_grid_basic(original_grid, 'recommenders_about') \
            if len(request.args) == 0 else original_grid

    response.view = "default/gab_list_layout.html"

    return dict(
        pageTitle=getTitle("#PublicRecommendationBoardTitle"),
        customText=getText("#PublicRecommendationBoardText"),
        pageHelp=getHelp("#PublicRecommendationBoardDescription"),
        grid=grid,
    )
