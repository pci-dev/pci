import cgi
import http
import typing
import json

from app_modules.helper import *
from app_modules.coar_notify import COARNotifyException, COARNotifier

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

    text = show_coar_status()
    text += "\n"
    text += show_coar_requests()

    return text .strip().replace('\n', '\n<br/>')


def inbox():
    coar_notifier = COARNotifier(db)

    # There is no inbox if COAR Notify is not enabled.
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
        # The Linked Data Notifications specification requires that every inbox supports
        # GET, subject to access controls. As we don't support it, we instead say it is
        # forbidden for everybody.
        raise HTTP(status=http.HTTPStatus.FORBIDDEN.value)
    elif request.method == "POST":
        # The POST method is used for submitting notifications to the inbox.

        content_type, content_type_options = cgi.parse_header(
            request.env.content_type or ""
        )
        if content_type not in _rdflib_parser_media_types:
            return HTTP(
                http.HTTPStatus.UNSUPPORTED_MEDIA_TYPE.value,
                f"Content-Type must be one of {', '.join(sorted(_rdflib_parser_media_types))})",
            )

        try:
            coar_notifier.record_notification(
                body=request.body,
                body_format=_rdflib_parser_media_types[content_type],
                direction="Inbound",
                base=coar_notifier.base_url + 'coar_notify/inbox/',
            )
        except COARNotifyException as e:
            raise HTTP(status=http.HTTPStatus.BAD_REQUEST.value, body=e.message) from e
        else:
            raise HTTP(status=http.HTTPStatus.ACCEPTED.value, body='')
    else:
        raise HTTP(
            http.HTTPStatus.METHOD_NOT_ALLOWED.value,
            **{
                "Allow": ", ".join(["POST", "OPTIONS"]),
            },
        )


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
    text = "\n".join([
        "<tt>%s</tt> = %s / %s / <a href=\"%s\">%s</a>" % (
            x.id,
            x.direction,
            get_request_type(x.body),
            get_object_ref(x.body),
            get_person_name(x.body),
        )
        for x in db(
            db.t_coar_notification.direction == "Outbound"
        ).select(orderby=~db.t_coar_notification.id)
    ])

    return text


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
