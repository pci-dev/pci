from datetime import date
from typing import List, Union

from serde import Optional, Untagged, dataclass, serde, field
from serde.json import to_json as serde_to_json


@serde(rename_all="camelcase")
class TranslatedField:
    value: str = field(rename="@value")
    language: str = field(rename="@language")


@serde(rename_all="camelcase")
class CreativeWork:
    type: str = field(init=False, rename="@type", default="schema:CreativeWork")
    headline: str


@serde(rename_all="camelcase")
class Person:
    type: str = field(init=False, rename="@type", default="schema:Person")
    name: str
    identifier: Optional[str] = field(skip_if_false=True, default=None)
    url: Optional[str] = field(skip_if_false=True, default=None)


@serde(rename_all="camelcase")
class MediaObject:
    type: str = field(init=False, rename="@type", default="schema:MediaObject")
    content_url: Optional[str] = field(skip_if_false=True, default=None)
    name: Optional[str] = field(skip_if_false=True, default=None)
    archived_at: Optional[str] = field(skip_if_false=True, default=None)
    description: Optional[str] = field(skip_if_false=True, default=None)


@serde(rename_all="camelcase")
class Answer:
    type: str = field(init=False, rename="@type", default="schema:Answer")
    author: List[Person]
    text: Optional[str] = field(skip_if_false=True, default=None)
    content_url: Optional[str] = field(skip_if_false=True, default=None)
    name: Optional[str] = field(skip_if_false=True, default=None)
    associated_media: Optional[MediaObject] = field(skip_if_false=True, default=None)


@serde(rename_all="camelcase")
class CriticReview:
    type: str = field(init=False, rename="@type", default="schema:CriticReview")
    author: Person
    review_body: str
    date_published: date


@serde(rename_all="camelcase")
class Periodical:
    type: str = field(init=False, rename="@type", default="schema:Periodical")
    name: str


@dataclass
class ScholarlyArticle:
    same_as: str

    type: str = field(init=False, rename="@type", default="schema:ScholarlyArticle")

    headline: Optional[Union[List[TranslatedField], str]] = field(skip_if_false=True, default=None)
    author: Optional[List[Person]] = field(skip_if_false=True, default=None)
    date_created: Optional[date] = field(skip_if_false=True, default=None)
    date_published: Optional[date] = field(skip_if_false=True, default=None)
    identifier: Optional[str] = field(skip_if_false=True, default=None)
    abstract: Optional[Union[List[TranslatedField], str]] = field(skip_if_false=True, default=None)
    is_part_of: Optional[Periodical] = field(skip_if_false=True, default=None)
    citation: Optional[List[Union["ScholarlyArticle", CreativeWork]]] = field(skip_if_false=True, default=None)
    about: Optional[str] = field(skip_if_false=True, default=None)
    is_based_on: Optional["ScholarlyArticle"] = field(skip_if_false=True, default=None)
    image: Optional[str] = field(skip_if_false=True, default=None)
    archived_at: Optional[str] = field(skip_if_false=True, default=None)
    version: Optional[str] = field(skip_if_false=True, default=None)
    associated_media: Optional[List[MediaObject]] = field(skip_if_false=True, default=None)
    keywords: Optional[Union[List[TranslatedField], str]] = field(skip_if_default=True, default=None)
    funder: Optional[str] = field(skip_if_default=True, default=None)
    associated_review: Optional[List[Union[CriticReview, "Recommendation"]]] = field(skip_if_default=True, default=None)


@dataclass
class Recommendation:
    date_created: date
    date_published: date
    review_body: str
    author: Person
    comment: Answer
    item_reviewed: ScholarlyArticle

    type: str = field(init=False, rename="@type", default="schema:Recommendation")
    associated_media: Optional[List[MediaObject]] = field(skip_if_false=True, default=None)
    associated_review: Optional[List[Union[CriticReview, "Recommendation"]]] = field(skip_if_false=True, default=None)


serde(Recommendation, rename_all="camelcase", tagging=Untagged)
serde(ScholarlyArticle, rename_all="camelcase", tagging=Untagged)


@serde(rename_all="camelcase")
class Context:
    schema: str = field(init=False, default="https://schema.org/")
    language: str = field(init=False, rename="@language", default="en")


@serde(rename_all="camelcase")
class Root:
    graph: ScholarlyArticle = field(rename="@graph")
    context: Context = field(init=False, rename="@context", default=Context())

    def to_json(self):
        return serde_to_json(self)
