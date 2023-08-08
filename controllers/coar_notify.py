import cgi
import http
import typing
import json

from app_modules.helper import *
from app_modules.coar_notify import COARNotifyException, COARNotifier
from app_modules import emailing


from gluon import current


if typing.TYPE_CHECKING:
    from gluon import HTTP, request, response

# A mapping from media types to rdflib parser identifiers.
_rdflib_parser_media_types = {
    "text/turle": "turtle",
    "application/ld+json": "json-ld",
}

try:
 import rdflib
 ACTIVITYSTREAMS = rdflib.Namespace("https://www.w3.org/ns/activitystreams#")
except:
 rdflib = None


def index():
    if not COARNotifier(db).enabled or not rdflib:
        return "COAR notifications for PCI (disabled: %s)" % (
                "inbox_url not configured" if rdflib else "rdflib not installed")

    ensure_trailing_slash()

    text = show_coar_status()
    text += "\n"
    text += show_coar_requests()

    return text .strip().replace('\n', '\n<br/>')


def inbox():
    coar_notifier = COARNotifier(db)

    if not coar_notifier.enabled:
        raise HTTP(status=http.HTTPStatus.NOT_FOUND.value)

    if request.method == "OPTIONS":
        response.headers.update(
            {
                "Allow": ", ".join(["POST", "OPTIONS"]),
                "Accept-Post": ", ".join(sorted(_rdflib_parser_media_types)),
            }
        )
        return ""

    elif request.method == "GET":
        raise HTTP(status=http.HTTPStatus.FORBIDDEN.value)

    elif request.method == "POST":
        if current.isRR: raise HTTP(status=http.HTTPStatus.FORBIDDEN.value)

        content_type, content_type_options = cgi.parse_header(
            request.env.content_type or ""
        )
        if content_type not in _rdflib_parser_media_types:
            raise HTTP(
                http.HTTPStatus.UNSUPPORTED_MEDIA_TYPE.value,
                f"Content-Type must be one of {', '.join(sorted(_rdflib_parser_media_types))})",
            )

        request.body.seek(0)
        body = request.body.read()

        validate_request(body, content_type, coar_notifier)
        process_request(json.loads(body))

        return HTTP(status=http.HTTPStatus.ACCEPTED.value)

    else:
        raise HTTP(
            http.HTTPStatus.METHOD_NOT_ALLOWED.value,
            **{ "Allow": ", ".join(["POST", "OPTIONS"]) },
        )


def process_request(req):
    request_handlers = {
        "Offer coar-notify:EndorsementAction": request_endorsement,
    }
    req_type = req["type"] if "type" in req.keys() else None

    if type(req_type) is list: req_type = " ".join(req_type)

    if req_type in request_handlers:
        request_handlers[req_type](req)
    else:
        raise HTTP(
                status=http.HTTPStatus.BAD_REQUEST.value,
                body=f"request.type: unsupported type '{req_type}'")


def request_endorsement(req):
    user_email = req["actor"]["id"]
    user_name = req["actor"]["name"]

    if not user_email.startswith("mailto:"):
        raise HTTP(
                status=http.HTTPStatus.BAD_REQUEST.value,
                body="actor.id must be a 'mailto:' url")

    user_email = user_email.replace("mailto:", "")
    user = db(db.auth_user.email.lower() == user_email.lower()).select().first()

    if not user:
        user = create_new_user(user_email, user_name)
        emailing.send_to_reset_password(session, auth, db, user)


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


def validate_request(body, content_type, coar_notifier):
        try:
            coar_notifier.record_notification(
                body=body,
                body_format=_rdflib_parser_media_types[content_type],
                direction="Inbound",
                base=coar_notifier.base_url + 'coar_notify/inbox/',
            )
        except COARNotifyException as e:
            raise HTTP(status=http.HTTPStatus.BAD_REQUEST.value, body=e.message) from e


def show_coar_status():
    coar_notifier = COARNotifier(db)

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
            get_status_display(x.http_status),
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
            db.t_coar_notification.direction == "Outbound"
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
    coar_types = [ "Endorsement", "Review" ]
    for t in coar_types:
        if body.find("://purl.org/coar/notify_vocabulary/" + t) > 0:
            return t


def get_request_type(body):
    req_type = get_type(body)

    return req_type.capitalize() if req_type else "UNKNOWN"


import re

def get_person_name(body):
    name = re.match(r'.*"@value": *"([^"]*)".*', body.replace('\n', ''))

    return name[1] if name else "(anonymous)"

def get_object_ref(body):
    obj_ref = re.match(r'.*/activitystreams#object": *\[ *{ *"@id": *"([^"]+)".*', body.replace('\n', ''))

    return obj_ref[1] if obj_ref else "(no object ref)"

errors = {
    418: "no inbox provided by article server",
    520: "inbox returned Unknown Error",
    521: "inbox server is down",
    522: "inbox connection timeout",
    524: "inbox read timeout",
    525: "inbox ssl handshake failed",
}
