import cgi
import http
import rdflib
import typing

from app_modules.helper import *
from app_modules.coar_notify import COARNotifyException, COARNotifier

if typing.TYPE_CHECKING:
    from gluon import HTTP, request, response

# A mapping from media types to rdflib parser identifiers.
_rdflib_parser_media_types = {
    "text/turle": "turtle",
    "application/ld+json": "json-ld",
}

ACTIVITYSTREAMS = rdflib.Namespace("https://www.w3.org/ns/activitystreams#")


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
