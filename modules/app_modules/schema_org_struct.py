from datetime import date
from typing import List, Union

from serde import Optional, Untagged, dataclass, serde, field
from serde.json import to_json as serde_to_json

from app_modules.lang import Lang


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

    headline: Optional[str] = field(skip_if_false=True, default=None)
    author: Optional[List[Person]] = field(skip_if_false=True, default=None)
    date_created: Optional[date] = field(skip_if_false=True, default=None)
    date_published: Optional[date] = field(skip_if_false=True, default=None)
    identifier: Optional[str] = field(skip_if_false=True, default=None)
    abstract: Optional[str] = field(skip_if_false=True, default=None)
    is_part_of: Optional[Periodical] = field(skip_if_false=True, default=None)
    citation: Optional[List[Union["ScholarlyArticle", CreativeWork]]] = field(skip_if_false=True, default=None)
    about: Optional[str] = field(skip_if_false=True, default=None)
    is_based_on: Optional["ScholarlyArticle"] = field(skip_if_false=True, default=None)
    image: Optional[str] = field(skip_if_false=True, default=None)
    archived_at: Optional[str] = field(skip_if_false=True, default=None)
    version: Optional[str] = field(skip_if_false=True, default=None)
    associated_media: Optional[List[MediaObject]] = field(skip_if_false=True, default=None)
    keywords: Optional[str] = field(skip_if_default=True, default=None)
    funder: Optional[str] = field(skip_if_default=True, default=None)
    associated_review: Optional[List[Union[CriticReview, "Recommendation"]]] = field(skip_if_default=True, default=None)

    headline_fr: Optional[str] = field(skip_if_false=True, default=None)
    headline_es: Optional[str] = field(skip_if_false=True, default=None)
    headline_ar: Optional[str] = field(skip_if_false=True, default=None)
    headline_hi: Optional[str] = field(skip_if_false=True, default=None)
    headline_ja: Optional[str] = field(skip_if_false=True, default=None)
    headline_pt: Optional[str] = field(skip_if_false=True, default=None)
    headline_ru: Optional[str] = field(skip_if_false=True, default=None)
    headline_zh_cn: Optional[str] = field(skip_if_false=True, default=None)

    abstract_fr: Optional[str] = field(skip_if_false=True, default=None)
    abstract_es: Optional[str] = field(skip_if_false=True, default=None)
    abstract_ar: Optional[str] = field(skip_if_false=True, default=None)
    abstract_hi: Optional[str] = field(skip_if_false=True, default=None)
    abstract_ja: Optional[str] = field(skip_if_false=True, default=None)
    abstract_pt: Optional[str] = field(skip_if_false=True, default=None)
    abstract_ru: Optional[str] = field(skip_if_false=True, default=None)
    abstract_zh_cn: Optional[str] = field(skip_if_false=True, default=None)

    keywords_fr: Optional[str] = field(skip_if_false=True, default=None)
    keywords_es: Optional[str] = field(skip_if_false=True, default=None)
    keywords_ar: Optional[str] = field(skip_if_false=True, default=None)
    keywords_hi: Optional[str] = field(skip_if_false=True, default=None)
    keywords_ja: Optional[str] = field(skip_if_false=True, default=None)
    keywords_pt: Optional[str] = field(skip_if_false=True, default=None)
    keywords_ru: Optional[str] = field(skip_if_false=True, default=None)
    keywords_zh_cn: Optional[str] = field(skip_if_false=True, default=None)


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
class TranslatedField:
    id: str = field(rename="@id")
    language: str = field(rename="@language")


@serde(rename_all="camelcase")
class Context:
    schema: str = field(init=False, default="https://schema.org/")
    language: str = field(init=False, rename="@language", default="en")

    headline_fr: TranslatedField = field(init=False, default=TranslatedField("schema:headline", Lang.FR.value.code))
    headline_ar: TranslatedField = field(init=False, default=TranslatedField("schema:headline", Lang.AR.value.code))
    headline_es: TranslatedField = field(init=False, default=TranslatedField("schema:headline", Lang.ES.value.code))
    headline_hi: TranslatedField = field(init=False, default=TranslatedField("schema:headline", Lang.HI.value.code))
    headline_ja: TranslatedField = field(init=False, default=TranslatedField("schema:headline", Lang.JA.value.code))
    headline_pt: TranslatedField = field(init=False, default=TranslatedField("schema:headline", Lang.PT.value.code))
    headline_ru: TranslatedField = field(init=False, default=TranslatedField("schema:headline", Lang.RU.value.code))
    headline_zh_cn: TranslatedField = field(
        init=False, default=TranslatedField("schema:headline", Lang.ZH_CN.value.code)
    )

    abstract_fr: TranslatedField = field(init=False, default=TranslatedField("schema:abstract", Lang.FR.value.code))
    abstract_ar: TranslatedField = field(init=False, default=TranslatedField("schema:abstract", Lang.AR.value.code))
    abstract_es: TranslatedField = field(init=False, default=TranslatedField("schema:abstract", Lang.ES.value.code))
    abstract_hi: TranslatedField = field(init=False, default=TranslatedField("schema:abstract", Lang.HI.value.code))
    abstract_ja: TranslatedField = field(init=False, default=TranslatedField("schema:abstract", Lang.JA.value.code))
    abstract_pt: TranslatedField = field(init=False, default=TranslatedField("schema:abstract", Lang.PT.value.code))
    abstract_ru: TranslatedField = field(init=False, default=TranslatedField("schema:abstract", Lang.RU.value.code))
    abstract_zh_cn: TranslatedField = field(
        init=False, default=TranslatedField("schema:abstract", Lang.ZH_CN.value.code)
    )

    keywords_fr: TranslatedField = field(init=False, default=TranslatedField("schema:keywords", Lang.FR.value.code))
    keywords_ar: TranslatedField = field(init=False, default=TranslatedField("schema:keywords", Lang.AR.value.code))
    keywords_es: TranslatedField = field(init=False, default=TranslatedField("schema:keywords", Lang.ES.value.code))
    keywords_hi: TranslatedField = field(init=False, default=TranslatedField("schema:keywords", Lang.HI.value.code))
    keywords_ja: TranslatedField = field(init=False, default=TranslatedField("schema:keywords", Lang.JA.value.code))
    keywords_pt: TranslatedField = field(init=False, default=TranslatedField("schema:keywords", Lang.PT.value.code))
    keywords_ru: TranslatedField = field(init=False, default=TranslatedField("schema:keywords", Lang.RU.value.code))
    keywords_zh_cn: TranslatedField = field(
        init=False, default=TranslatedField("schema:keywords", Lang.ZH_CN.value.code)
    )


@serde(rename_all="camelcase")
class Root:
    graph: ScholarlyArticle = field(rename="@graph")
    context: Context = field(init=False, rename="@context", default=Context())

    def to_json(self):
        return serde_to_json(self)
