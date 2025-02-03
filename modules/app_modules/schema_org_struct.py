from datetime import datetime
from typing import List, Union

from serde import Optional, Untagged, dataclass, serde, field
from serde.json import to_json as serde_to_json


@serde(rename_all="camelcase")
class TranslatedField:
    value: str = field(rename="@value")
    language: str = field(rename="@language")


@serde(rename_all="camelcase")
class Id:
    id: str = field(rename="@id")


@serde(rename_all="camelcase")
class CreativeWork:
    type: str = field(init=False, rename="@type", default="CreativeWork")
    headline: str
    name: str


@serde(rename_all="camelcase")
class Person:
    type: str = field(init=False, rename="@type", default="Person")
    name: str
    identifier: Optional[str] = field(skip_if_false=True, default=None)
    url: Optional[str] = field(skip_if_false=True, default=None)


@serde(rename_all="camelcase")
class MediaObject:
    type: str = field(init=False, rename="@type", default="MediaObject")
    name: str
    content_url: Optional[str] = field(skip_if_false=True, default=None)
    archived_at: Optional[str] = field(skip_if_false=True, default=None)
    description: Optional[str] = field(skip_if_false=True, default=None)


@serde(rename_all="camelcase")
class Answer:
    type: str = field(init=False, rename="@type", default="Answer")
    name: str
    author: List[Person]
    text: Optional[str] = field(skip_if_false=True, default=None)
    content_url: Optional[str] = field(skip_if_false=True, default=None)
    associated_media: Optional[MediaObject] = field(skip_if_false=True, default=None)


@serde(rename_all="camelcase")
class Periodical:
    type: str = field(init=False, rename="@type", default="Periodical")
    name: str


@serde(rename_all="camelcase")
class Comment:
    type: str = field(init=False, rename="@type", default="Comment")
    name: str
    author: Person
    parent_item: Id
    date_published: datetime
    text: Optional[str] = field(skip_if_false=True, default=None)
    shared_content: Optional[MediaObject] = field(skip_if_false=True, default=None)


@dataclass
class ScholarlyArticle:
    id: str
    same_as: str
    name: str
    type: str = field(init=False, rename="@type", default="ScholarlyArticle")

    headline: Optional[Union[List[TranslatedField], str]] = field(skip_if_false=True, default=None)
    author: Optional[List[Person]] = field(skip_if_false=True, default=None)
    date_created: Optional[datetime] = field(skip_if_false=True, default=None)
    date_published: Optional[datetime] = field(skip_if_false=True, default=None)
    identifier: Optional[str] = field(skip_if_false=True, default=None)
    abstract: Optional[Union[List[TranslatedField], str]] = field(skip_if_false=True, default=None)
    article_body: Optional[Union[List[TranslatedField], str]] = field(skip_if_false=True, default=None)
    is_part_of: Optional[Periodical] = field(skip_if_false=True, default=None)
    citation: Optional[List[Union["ScholarlyArticle", CreativeWork]]] = field(skip_if_false=True, default=None)
    about: Optional[str] = field(skip_if_false=True, default=None)
    is_based_on: Optional[List[Union["ScholarlyArticle", Comment, "Recommendation"]]] = field(
        skip_if_false=True, default=None
    )
    image: Optional[str] = field(skip_if_false=True, default=None)
    archived_at: Optional[str] = field(skip_if_false=True, default=None)
    version: Optional[str] = field(skip_if_false=True, default=None)
    associated_media: Optional[List[MediaObject]] = field(skip_if_false=True, default=None)
    keywords: Optional[Union[List[TranslatedField], str]] = field(skip_if_default=True, default=None)
    funder: Optional[str] = field(skip_if_default=True, default=None)
    review: Optional["Recommendation"] = field(skip_if_default=True, default=None)
    comment: Optional[List[Comment]] = field(skip_if_default=True, default=None)


@dataclass
class Recommendation:
    date_created: datetime
    date_published: datetime
    article_body: str
    author: Person
    comment: Answer
    name: str
    headline: str

    type: str = field(init=False, rename="@type", default="ScholarlyArticle")
    associated_media: Optional[List[MediaObject]] = field(skip_if_false=True, default=None)
    associated_review: Optional["Recommendation"] = field(skip_if_false=True, default=None)
    is_based_on: Optional[List[Union[ScholarlyArticle, Comment, "Recommendation"]]] = field(
        skip_if_false=True, default=None
    )


serde(Recommendation, rename_all="camelcase", tagging=Untagged)
serde(ScholarlyArticle, rename_all="camelcase", tagging=Untagged)


@serde(rename_all="camelcase")
class LanguageContainer:
    id: str = field(rename="@id")
    container: str = field(init=False, rename="@container", default="@language")


@serde(rename_all="camelcase")
class Root:
    graph: ScholarlyArticle = field(rename="@graph")
    context: str = field(init=False, rename="@context", default="https://schema.org/")

    def to_json(self):
        return serde_to_json(self)
