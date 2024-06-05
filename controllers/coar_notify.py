import typing
import json
import requests

from app_modules import emailing
from http import HTTPStatus
from gluon import current
from models.article import Article
from models.user import User


if typing.TYPE_CHECKING:
    from gluon import HTTP, request, response


def index():
    if request.method == 'HEAD':
        add_describedby_header(response)
        return ""

    text = show_coar_status()

    if auth.has_membership(role="administrator"):
        text += "\n"
        text += show_coar_requests()
    else:
        text += login_button()

    return "<!doctype html>\n" + text .strip().replace('\n', '\n<br/>')


##
## the inbox (at /coar_notify/inbox)
##

def inbox():
    accepted_media_types = [
        "application/ld+json",
    ]
    allowed_methods = [
            "POST",
            "HEAD",
            "OPTIONS",
    ]
    def add_options_headers():
        response.headers.update({
            "Allow": ", ".join(allowed_methods),
            "Accept-Post": ", ".join(accepted_media_types),
        })

    if not current.coar.enabled:
        fail("COAR not enabled",
                HTTPStatus.NOT_FOUND)

    if request.method == "GET":
        fail(f"Allowed methods: {', '.join(allowed_methods)}",
                HTTPStatus.FORBIDDEN)

    elif request.method == "POST":
        parse_content_type(request)

        if not is_coar_whitelisted(request.env.remote_addr):
            fail(f"Not whitelisted: {request.env.remote_addr}",
                    HTTPStatus.FORBIDDEN)

        if not request.content_type in accepted_media_types:
            fail(f"Unsupported content-type: {request.content_type}",
                    HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

        try:
            body = json.loads(get_body(request))

            record_request(body)
            process_request(body)

        except HTTP as e:
            raise e
        except json.JSONDecodeError as e:
            fail(f"Invalid JSON: {e}")
        except Exception as e:
            fail(f"{e.__class__.__name__}: {e}")

        add_location_header(response, coar_id=body['id'])
        return HTTP(status=HTTPStatus.CREATED.value)

    elif request.method == "HEAD":
        add_describedby_header(response)
        add_options_headers()
        return ""

    elif request.method == "OPTIONS":
        add_options_headers()
        return ""

    else:
        fail(f"Method not allowed: {request.method}",
            HTTPStatus.METHOD_NOT_ALLOWED,
            Allow=", ".join(allowed_methods),
        )


def is_coar_whitelisted(host):
    for entry in db.cfg.coar_whitelist or []:
        if host == entry.split(" ")[0]:
            return True
    return False


def parse_content_type(request):
    from email.policy import EmailPolicy as mime
    header = mime.header_factory('content-type', request.env.content_type)

    request.encoding = header.params.get("charset")
    request.content_type = header.content_type

def get_body(request):
    request.body.seek(0)
    body = request.body.read()
    return str(body, request.encoding or "utf8")


def process_request(req):
    request_handlers = {
        "Offer coar-notify:EndorsementAction": request_endorsement,
        "Undo": cancel_endorsement,
    }
    req_type = req["type"] if "type" in req.keys() else None

    if type(req_type) is list: req_type = " ".join(req_type)

    if req_type not in request_handlers:
        fail(f"request.type: unsupported type '{req_type}'")

    request_handlers[req_type](req)


def request_endorsement(req):
    user_email = req["actor"]["id"]
    user_name = req["actor"]["name"]
    coar_req_id = req["id"]

    if not user_email.startswith("mailto:"):
        fail("actor.id must be a 'mailto:' url")

    if get_article_by_coar_req_id(coar_req_id):
        fail(f"already exists: request.id='{coar_req_id}'")

    user_email = user_email.replace("mailto:", "")
    user = db(db.auth_user.email.lower() == user_email.lower()).select().first()

    if not user:
        user = User.create_new_user(user_name.split()[0], user_name.split()[-1], user_email)
    else:
        user.reset_password_key = ''

    if "context" in req.keys():
        article = handle_resubmission(req, user)
        emailing.send_to_coar_resubmitter(session, auth, db, user, article)
    else:
        article = create_prefilled_submission(req, user)
        emailing.send_to_coar_requester(session, auth, db, user, article)


def handle_resubmission(req, user):
    context = req["context"]
    if not "id" in context:
        fail("no context.id")

    context_id = context["id"]
    article = update_resubmitted_article(req, context_id)

    if not article:
        fail(f"no matching article for context.id='{context_id}'")
    if article.status != 'Awaiting revision':
        fail(f"not awaiting revision: article.id='{article.id}'")

    return article


def cancel_endorsement(req):
    coar_req_id = req["object"]["id"]

    article = get_article_by_coar_req_id(coar_req_id)
    if not article:
        fail(f"no such offer: object.id='{coar_req_id}'")

    article.update_record(status="Cancelled")


def create_prefilled_submission(req, user):
    article_data = req["object"]
    author_data = req["actor"]
    coar_req_id = req["id"]

    doi = article_data["ietf:cite-as"]
    meta_data = get_signposting_metadata(doi)
    preprint_server = get_preprint_server(doi)
    guess_version(doi, meta_data)

    if not meta_data["authors"]:
        meta_data["authors"] = author_data["name"]

    return Article.create_prefilled_submission(user_id=user.id, 
                                               doi=doi, 
                                               coar_notification_id=coar_req_id,
                                               preprint_server=preprint_server,
                                               **meta_data)


def update_resubmitted_article(req, context):
    article = db(db.t_articles.doi == context) \
                    .select().first()
    if not article:
        return
    if article.status != "Awaiting revision":
        return article

    article.update_record(
        coar_notification_id = req["id"],
        coar_notification_closed = False,
        doi = req["object"]["ietf:cite-as"],
    )
    return article


def record_request(body):
    current.coar.record_notification(
            body=body,
            direction="Inbound",
    )


def get_article_by_coar_req_id(coar_req_id):
    return db(bool(coar_req_id) &
            (db.t_articles.coar_notification_id == coar_req_id)) \
                .select(db.t_articles.id, db.t_articles.status).first()


def get_preprint_server(doi):
    conf = map(str.split, db.cfg.coar_whitelist or [])
    conf = { e[0]: e[-1] for e in conf }

    return conf[request.env.remote_addr]


def get_signposting_metadata(doi):
    metadata = {}
    try:
        metadata_url = get_link(doi, rel="describedby", formats=DC_profile)
        # HAL currently uses "formats" but will eventually use "profile"
        if not metadata_url:
            metadata_url = get_link(doi, rel="describedby", profile=DC_profile)

        r = retry(requests.get, metadata_url)

        map_dc(metadata, r.text)
    except:
        pass

    return metadata

DC_profile = "http://purl.org/dc/elements/1.1/"


def map_dc(metadata, xml_str):
    from lxml import objectify
    c = objectify.fromstring(xml_str.encode("utf8"))

    def get(elt): return str(c.find("{"+DC_profile+"}"+elt))
    def get_all(elt): return map(str, c.findall("{"+DC_profile+"}"+elt))

    # map to db.t_article columns
    metadata["title"] = get("title")
    metadata["authors"] = "; ".join(get_all("creator"))
    metadata["article_year"] = get("date").split("-")[0]
    metadata["abstract"] = get("description")
    metadata["keywords"] = get("subject")


def map_HAL_json(metadata, content):
    c = content["response"]["docs"][0]

    # map to db.t_article columns
    metadata["title"] = c["title_s"][0]
    metadata["authors"] = ", ".join(c["authFullName_s"])
    metadata["ms_version"] = c["version_i"]
    metadata["article_year"] = c["publicationDateY_i"]
    metadata["abstract"] = grab_json_meta(c, "abstract_s", 0)
    metadata["keywords"] = ", ".join(grab_json_meta(c, "keyword_s"))


def grab_json_meta(c, *args):
    try:
        for k in args: c = c[k]
        return c
    except:
        return ""


def guess_version(doi, metadata):
    try:
        r = requests.get(doi, timeout=(1,4), allow_redirects=True)
        m = (
               re.match(r".*v(\d+)$", r.url)        # HAL
            or re.match(r".*\d+\.(\d+)$", r.url)    # DSpace
        )
        version = m[1]
    except:
        version = 1

    metadata["ms_version"] = version


def get_link(doi, **kv):
    r = retry(requests.head, doi)

    for h in r.headers["link"].split(','):
        h = [v.strip() for v in h.split(';')]
        if all([ f'{k}="{v}"' in h for k,v in kv.items()]):
            return h[0].strip('<>') # discard < and > in '<url>'


def retry(func, url):
    for _ in range(30):
        try:
            r = func(url, timeout=(1,4), allow_redirects=True,
                        headers={"user-agent":"curl"})
            r.raise_for_status()
            return r
        except:
            from time import sleep
            sleep(1)

    raise Exception(f"{func}: too many retries ({_})")


def fail(message=None, status=HTTPStatus.BAD_REQUEST, **headers):
    raise HTTP(status=status.value, body=message, **headers)


def add_location_header(response, coar_id):
    response.headers['Location'] = URL(
            "coar_notify", "show", vars={"coar_id":coar_id}, scheme=True)


##
## inbox/outbox display (page /coar_notify)
##

def show_coar_status():
    text = """
    coar notifications for pci (%s)

    inbound: %d
    outbound: %d

    """ % (

        "enabled" if current.coar.enabled else "disabled",
        db(db.t_coar_notification.direction == 'Inbound').count(),
        db(db.t_coar_notification.direction == 'Outbound').count(),
    )

    return text


def login_button():
    login_url = URL("default/user/logout", "?_next="+
                    "/default/user/login?_next="+URL(' '))
    return f"""
        <button style="
                    position: fixed; top: 0; right: 0;
                    border: 1px solid; border-radius: .5em;
                    margin: 1em; padding: .3em;
                "
        onclick="location.replace('{login_url}')">
            admin
        </button>
    """.replace("\n", "")


def show_coar_requests(per_page=100):
    page = paginator.page()

    text = "\n".join([ " / ".join([
            '<tt %s>[%s]</tt>',
            '<tt>%s</tt>',
            '<tt>%s</tt>',
            '<tt>%s</tt> <a href="%s">%s</a>',
            '<a href="%s">%s</a>',
            '<a href="%s">%s</a>',
            ]) % (
            get_status_display(x.http_status or 200),
            x.id,
            get_article_link(x),
            x.created,
            ["◀=", "=▶"][x.direction == "Outbound"],
            x.inbox_url,
            get_service_nick(x.article_id),
            URL("show?id=%d" % x.id),
            get_request_type(x.body),
            get_object_ref(x.body),
            get_person_name(x.body),
        )
        for x in db().select(
            orderby=~db.t_coar_notification.id,
            limitby=(page*per_page, (page+1)*per_page),
        )
    ])

    return text + paginator.controls(page, per_page)


class paginator:

    def page():
        try: return int(request.vars.page)
        except: return 0

    def controls(page, per_page):
        nb_pages = round(db(db.t_coar_notification).count() / per_page + .5)
        link = lambda txt, page: f'<a href="?page={page}">{txt}</a>'
        next_ = link(">>", (page + 1) % nb_pages)
        prev_ = link("<<", (page - 1 + nb_pages) % nb_pages)
        home_ = link("::", 0)

        return f"\n\n<tt>{prev_} {home_} {next_}</tt>"


def show():
    req_id = request.vars.id or request.vars.coar_id
    try:
        req = db(
            db.t_coar_notification.id == req_id   if req_id.isdigit() else
            db.t_coar_notification.coar_id == req_id
        ).select()
    except:
        raise HTTP(400, f"error: no such coar request, id={req_id}")

    req_body = req[0].body
    req_json = json.loads(req_body)
    response.headers['Content-Type'] = 'application/ld+json'
    return json.dumps(req_json, indent=4)


def get_status_display(status):
    return 'style="%s" title="%s"' % (
                "background-color:orange",
                f"error: {status} = {errors.get(status, '?')}",
        ) if status >= 400 else ""


def get_article_link(notif):
    article = get_article_by_coar_req_id(notif.coar_id)
    article_id = (
            article.id if article
            else guess_article_id(notif.body)
    )
    notif.article_id = article_id

    link = URL("manager", f"recommendations?articleId={article_id}")
    return f'<a href="{link}">#{article_id}</a>' if article_id else ""


def get_service_nick(article_id):
    article = db(db.t_articles.id == article_id) \
            .select(db.t_articles.preprint_server).first()
    return f'{article.preprint_server}' if article else ""


def guess_article_id(body):
    reply = re.match(r'.*"inReplyTo": "([^"]+)".*', body)
    if reply:
        article = get_article_by_coar_req_id(reply[1])
        return article.id if article else None

    pci_link = re.match(r'.*articleId=(\d+).*', body, re.S)
    if pci_link:
        return pci_link[1]


def get_type(body):
    coar_types = [
            "Endorsement", "Review",
            "Reject", "Accept",
            "Undo",
    ]
    for t in coar_types:
        if body.find("://purl.org/coar/notify_vocabulary/" + t) > 0:
            return t
        if body.find(f'"coar-notify:{t}Action"') > 0:
            return t
        if body.find(f'"type": "Tentative{t}"') > 0:
            return t
        if body.find(f'"type": "{t}"') > 0:
            return t


def get_request_type(body):
    req_type = get_type(body)

    return req_type.capitalize() if req_type else "UNKNOWN"


import re

def get_person_name(body):
    name = re.match(r'.*"actor": .* "name": ("[^"]+")', body)
    if name: return json.loads(name[1])

    name = re.match(r'.*"@type": "as:Person", "as:name": "([^"]*)".*', body)
    if name: return name[1]

    name = re.match(r'.*"@value": *"([^"]*)".*', body.replace('\n', ''))
    if name: return name[1]

    if re.match(r'.*(Accept|Reject)".*', body):
        return ""

    return "(anonymous)"

def get_object_ref(body):
    try: return json.loads(body)["object"]["object"]
    except: pass
    try: return json.loads(body)["object"]["id"]
    except: pass

    obj_ref = re.match(r'.*"as:object": {"@id": "([^"]+)".*', body)
    if obj_ref: return obj_ref[1]

    obj_ref = re.match(r'.*/activitystreams#object": *\[ *{ *"@id": *"([^"]+)".*', body.replace('\n', ''))
    if obj_ref: return obj_ref[1]

    return "(no object ref)"

errors = {
    400: "inbox said bad request",
    418: "no inbox provided by article server",
    520: "inbox returned Unknown Error",
    521: "inbox server is down",
    522: "inbox connection timeout",
    524: "inbox read timeout",
    525: "inbox ssl handshake failed",
}


##
## system description (proposal)
##

def system_description():
    response.headers['Content-Type'] = 'application/json'
    resp_json = {
        "takes": {
                "Offer.EndorsementAction": {
                        "yields": [
                                "TentativeAccept",
                                "Reject",
                        ],
                        "returns": [
                                "201:CREATED",
                                "400:BAD_REQUEST",
                        ],
                },
                "Undo": {
                        "yields": [
                        ],
                        "returns": [
                                "201:CREATED",
                                "400:BAD_REQUEST",
                        ],
                },
        },
        "gives": {
                "Announce.EndorsementAction": {
                        "after": [
                                "Offer.EndorsementAction",
                                "spontaneous",
                        ],
                        "time-frame": "1-2 months",
                },
                "Announce.ReviewAction": {
                        "after": [
                                "Offer.EndorsementAction",
                                "spontaneous",
                        ],
                        "time-frame": "1-2 months",
                },
        },
        "access-control": {
            "inbox.POST": "whitelisted IP",
            "inbox.READ": "none",
        },
    }
    return json.dumps(resp_json, indent=4)


def add_describedby_header(response):
    response.headers.update({
        "link": '<' + URL("coar_notify", "system_description", scheme=True) + '>' +
        '; rel="describedby"; type="application/json"'
    })
