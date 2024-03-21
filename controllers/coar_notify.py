import cgi
import http
import typing
import json
import requests

from app_modules.helper import *
from app_modules.coar_notify import COARNotifier
from app_modules import emailing
from gluon import current


if typing.TYPE_CHECKING:
    from gluon import HTTP, request, response

accepted_media_types = {
    "application/ld+json": "json-ld",
}


@auth.requires(auth.has_membership(role="administrator"))
def index():
    if not current.coar.enabled:
        return "COAR notifications for PCI (disabled)"

    ensure_trailing_slash()

    text = show_coar_status()
    text += "\n"
    text += show_coar_requests()

    return text .strip().replace('\n', '\n<br/>')


def inbox():
    coar_notifier = current.coar

    if not coar_notifier.enabled:
        raise HTTP(status=http.HTTPStatus.NOT_FOUND.value)

    if request.method == "OPTIONS":
        response.headers.update(
            {
                "Allow": ", ".join(["POST", "OPTIONS"]),
                "Accept-Post": ", ".join(accepted_media_types),
            }
        )
        return ""

    elif request.method == "GET":
        raise HTTP(status=http.HTTPStatus.FORBIDDEN.value)

    elif request.method == "POST":
        if current.isRR: raise HTTP(status=http.HTTPStatus.FORBIDDEN.value)

        if not is_coar_whitelisted(request.env.remote_addr):
            raise HTTP(
                    http.HTTPStatus.FORBIDDEN.value,
                    f"not whitelisted: {request.env.remote_addr}")

        content_type, content_type_options = cgi.parse_header(
            request.env.content_type or ""
        )
        if content_type not in accepted_media_types:
            raise HTTP(
                http.HTTPStatus.UNSUPPORTED_MEDIA_TYPE.value,
                f"Content-Type must be one of {', '.join(accepted_media_types)}",
            )

        request.body.seek(0)
        body = request.body.read()

        validate_request(body, content_type, coar_notifier)
        process_request(json.loads(body))

        db_id = get_db_id(json.loads(body)["id"])
        response.headers['Location'] = URL("coar_notify", f"show?id={db_id}", scheme=True)
        return HTTP(status=http.HTTPStatus.CREATED.value)

    else:
        raise HTTP(
            http.HTTPStatus.METHOD_NOT_ALLOWED.value,
            **{ "Allow": ", ".join(["POST", "OPTIONS"]) },
        )


def is_coar_whitelisted(host):
    for entry in db.cfg.coar_whitelist or []:
        if host == entry.split(" ")[0]:
            return True
    return False


def get_db_id(coar_id):
    return db(db.t_coar_notification.coar_id == coar_id).select(
            db.t_coar_notification.id).first().id


def process_request(req):
    request_handlers = {
        "Offer coar-notify:EndorsementAction": request_endorsement,
        "Undo": cancel_endorsement,
    }
    req_type = req["type"] if "type" in req.keys() else None

    if type(req_type) is list: req_type = " ".join(req_type)

    if req_type not in request_handlers:
        raise HTTP(
                status=http.HTTPStatus.BAD_REQUEST.value,
                body=f"request.type: unsupported type '{req_type}'")
    try:
        request_handlers[req_type](req)
    except HTTP as e:
        raise e
    except Exception as e:
        raise HTTP(
                status=http.HTTPStatus.BAD_REQUEST.value,
                body=f"exception: {e}")


def request_endorsement(req):
    user_email = req["actor"]["id"]
    user_name = req["actor"]["name"]
    coar_req_id = req["id"]

    if not user_email.startswith("mailto:"):
        raise HTTP(
                status=http.HTTPStatus.BAD_REQUEST.value,
                body="actor.id must be a 'mailto:' url")

    if get_article_by_coar_req_id(coar_req_id):
        raise HTTP(
                status=http.HTTPStatus.BAD_REQUEST.value,
                body=f"already exists: request .id='{coar_req_id}'")

    user_email = user_email.replace("mailto:", "")
    user = db(db.auth_user.email.lower() == user_email.lower()).select().first()

    if not user:
        user = create_new_user(user_email, user_name)
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
    if not "id" in context: raise HTTP(
            status=http.HTTPStatus.BAD_REQUEST.value,
            body=f"no context.id")

    context_id = context["id"]
    article = update_resubmitted_article(req, context_id)

    if not article: raise HTTP(
            status=http.HTTPStatus.BAD_REQUEST.value,
            body=f"no matching article for context.id='{context_id}'")
    if article.status != 'Awaiting revision': raise HTTP(
            status=http.HTTPStatus.BAD_REQUEST.value,
            body=f"not awaiting revision: article.id='{article.id}'")

    return article


def cancel_endorsement(req):
    coar_req_id = req["object"]["id"]

    article = get_article_by_coar_req_id(coar_req_id)
    if not article:
        raise HTTP(
                status=http.HTTPStatus.BAD_REQUEST.value,
                body=f"no such offer: object.id='{coar_req_id}'")

    article.status = "Cancelled"
    article.update_record()


def create_new_user(user_email, user_name):
    my_crypt = CRYPT(key=auth.settings.hmac_key)
    crypt_pass = my_crypt(auth.random_password())[0]
    import time
    from gluon.utils import web2py_uuid
    reset_password_key = str((15 * 24 * 60 * 60) + int(time.time())) + "-" + web2py_uuid()
    new_user_id = db.auth_user.insert(
        email=user_email,
        password=crypt_pass,
        reset_password_key=reset_password_key,
        first_name=user_name.split()[0],
        last_name=user_name.split()[-1],
    )
    new_user = db.auth_user(new_user_id)
    return new_user


def create_prefilled_submission(req, user):
    article_data = req["object"]
    author_data = req["actor"]
    coar_req_id = req["id"]

    doi = article_data["ietf:cite-as"]
    meta_data = get_signposting_metadata(doi)
    preprint_server = get_preprint_server(doi)
    guess_version(doi, meta_data)

    return \
    db.t_articles.insert(
        doi=doi,
        user_id=user.id,
        status="Pre-submission",
        preprint_server=preprint_server,
        coar_notification_id=coar_req_id,
        **meta_data,
    )


def update_resubmitted_article(req, context):
    article = db(db.t_articles.doi == context) \
                    .select().first()
    if not article:
        return
    if article.status != "Awaiting revision":
        return article

    article.coar_notification_id = req["id"]
    article.coar_notification_closed = False
    article.doi = req["object"]["ietf:cite-as"]

    article.update_record()

    return article


def validate_request(body, content_type, coar_notifier):
        try:
            coar_notifier.record_notification(
                body=json.loads(body),
                direction="Inbound",
            )
        except Exception as e:
            raise HTTP(status=http.HTTPStatus.BAD_REQUEST.value,
                        body=f"{e.__class__.__name__}: {e}")


def get_article_by_coar_req_id(coar_req_id):
    return db(db.t_articles.coar_notification_id == coar_req_id) \
                .select().first()


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
    metadata["authors"] = ", ".join(get_all("creator"))
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


def show_coar_status():
    coar_notifier = current.coar

    text = """
    coar notifications for pci (%s)

    inbound: %d
    outbound: %d

    """ % (

        "enabled" if coar_notifier.enabled else "disabled",
        db(db.t_coar_notification.direction == 'Inbound').count(),
        db(db.t_coar_notification.direction == 'Outbound').count(),
    )

    return text


def show_coar_requests():
    text = "\n".join([(
            '<tt %s>[%s]</tt> <tt>%s</tt> = ' +
            '<a href="%s">%s</a> / ' +
            '<a href="%s">%s</a> / ' +
            '<a href="%s">%s</a>') % (
            get_status_display(x.http_status or 200),
            x.id,
            x.created,
            x.inbox_url,
            x.direction,
            "show?id=%d" % x.id,
            get_request_type(x.body),
            get_object_ref(x.body),
            get_person_name(x.body),
        )
        for x in db(
            #db.t_coar_notification.direction == "Outbound"
        ).select(orderby=~db.t_coar_notification.id)
    ])

    return text


def show():
    try:
        req_id = request.vars.id
        int(req_id)
    except:
        raise HTTP(400, "usage: ?id=&lt;coar request id (int)&gt;")

    req = db(
            db.t_coar_notification.id == req_id
    ).select()

    if not req:
        raise HTTP(400, "error: no such coar request. id=" + req_id)

    req_body = req[0].body
    req_json = json.loads(req_body)
    response.headers['Content-Type'] = 'application/ld+json'
    return json.dumps(req_json, indent=4)


def get_status_display(status):
    return 'style="%s" title="%s"' % (
                "background-color:orange",
                f"error: {status} = {errors.get(status, '?')}",
        ) if status >= 400 else ""


def ensure_trailing_slash():
    if not request.env.path_info.endswith("/"):
        redirect(URL(' '))


def get_type(body):
    coar_types = [
            "Endorsement", "Review",
            "Reject", "Accept",
    ]
    for t in coar_types:
        if body.find("://purl.org/coar/notify_vocabulary/" + t) > 0:
            return t
        if body.find(f'"coar-notify:{t}Action"') > 0:
            return t
        if body.find(f'"type": "Tentative{t}"') > 0:
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
    418: "no inbox provided by article server",
    520: "inbox returned Unknown Error",
    521: "inbox server is down",
    522: "inbox connection timeout",
    524: "inbox read timeout",
    525: "inbox ssl handshake failed",
}
