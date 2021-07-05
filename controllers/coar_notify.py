import datetime
from json import JSONDecodeError

import cgi
import http
import rdflib
import typing
from rdflib import RDF

from app_modules.helper import *

if typing.TYPE_CHECKING:
    from gluon import HTTP, request, response

# A mapping from media types to rdflib parser identifiers.
_rdflib_parser_media_types = {
    "text/turle": "turtle",
    "application/ld+json": "json-ld",
}

ACTIVITYSTREAMS = rdflib.Namespace("https://www.w3.org/ns/activitystreams#")


def inbox():
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

        graph = rdflib.Graph()

        try:
            graph.parse(request.body, format=_rdflib_parser_media_types[content_type])
        except Exception:
            raise HTTP(
                http.HTTPStatus.BAD_REQUEST.value, "Couldn't parse message body."
            )

        subjects = list(graph.subjects(RDF.type, ACTIVITYSTREAMS.Announce))
        if len(subjects) != 1:
            raise HTTP(
                http.HTTPStatus.BAD_REQUEST.value,
                "Exactly one resource in notification body must be an Activity Streams Announce instance.",
            )
        subject = subjects[0]

        db.t_coar_notification.insert(
            created=datetime.datetime.now(tz=datetime.timezone.utc),
            rdf_type=" ".join(
                str(type)
                for type in graph.objects(subject, RDF.type)
                if type != ACTIVITYSTREAMS.Announce
            ),
            body=graph.serialize(format="json-ld"),
        )

        raise HTTP(status=http.HTTPStatus.ACCEPTED.value, body='')
    else:
        raise HTTP(
            http.HTTPStatus.METHOD_NOT_ALLOWED.value,
            **{
                "Allow": ", ".join(["POST", "OPTIONS"]),
            },
        )
