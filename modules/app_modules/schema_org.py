from copy import copy
from typing import Dict, List, Optional, Union
from app_modules import common_tools
from app_modules import common_small_html
from gluon import XML, current
from gluon.contrib.appconfig import AppConfig # type: ignore
from app_modules.lang import Lang
from models.article import Article, TranslatedFieldType
from models.recommendation import Recommendation
from models.review import Review, ReviewState
from models.user import User
from app_modules import schema_org_struct as so


conf = AppConfig()


class SchemaOrgException(Exception):

    _article: Article
    _message: str

    def __init__(self, article: Article, message: str):
        self._article = article
        self._message = message

    def __str__(self):
        return repr(f"Schema.org builder raise exception for article {self._article.id}: {self._message}")


class SchemaOrg:

    _periodical = so.Periodical(conf.get("app.description"))
    _scholarly_article: so.ScholarlyArticle
    _root_recommendation: so.ScholarlyArticle
    _schema: so.Root

    _authors: Dict[int, so.Person]

    _article: Article
    _final_recommendation: Recommendation
    _recommendations: List[Recommendation]

    def __init__(self, article: Article):
        self._article = article
        self._authors = {}

        recommendations = Article.get_last_recommendations(article.id, ~current.db.t_recommendations.id)
        recommendations = [r for r in recommendations]
        self._recommendations = recommendations

        self._final_recommendation = self._recommendations.pop(0)

        self._init_scholarly_article()
        self._init_root_recommendation()

        self._schema = so.Root(self._root_recommendation)


    def to_json(self):
        return self._schema.to_json()
    

    def to_script_tag(self):
        return XML(f'<script type="application/ld+json">{self.to_json()}</script>')


    def _init_root_recommendation(self):
        final_recommendation = self._final_recommendation

        if not final_recommendation:
            raise SchemaOrgException(self._article, "Final recommendation not found!")
        
        if not final_recommendation.recommendation_doi:
            raise SchemaOrgException(self._article, f"Recommendation {final_recommendation.id} doesn't have doi!")

        if not final_recommendation.validation_timestamp:
            raise SchemaOrgException(self._article, f"Recommendation {final_recommendation.id} doesn't have validation date!")
        
        if not final_recommendation.recommendation_comments:
            raise SchemaOrgException(self._article, f"Recommendation {final_recommendation.id} doesn't have decision!")

        self._root_recommendation = so.ScholarlyArticle(
            same_as=common_small_html.mkLinkDOI(final_recommendation.recommendation_doi),
            headline=final_recommendation.recommendation_title,
            author=[self._get_author(final_recommendation.recommender_id)],
            date_created=final_recommendation.last_change.date(),
            date_published=final_recommendation.validation_timestamp.date(),
            identifier=Recommendation.get_doi_id(final_recommendation),
            abstract=self._clean_text(Recommendation.recommendation_decision_without_references(final_recommendation.recommendation_comments)),
            citation=self._get_recommendation_body(final_recommendation),
            is_part_of=self._periodical,
            is_based_on=self._scholarly_article,
            associated_review=self._get_associated_recommendation_and_reviews(final_recommendation),
            associated_media=self._get_recommendation_medias(final_recommendation),
        )

    
    def _get_associated_recommendation_and_reviews(self, recommendation: Recommendation):
        if len(self._recommendations) == 0:
            last_reviews: List[Union[so.Recommendation, so.CriticReview]] = []
            last_reviews.extend(self._get_recommendation_reviews(recommendation))
            return last_reviews
        
        next_recommendation = self._recommendations.pop(0)

        if not next_recommendation.validation_timestamp:
            raise SchemaOrgException(self._article, f"Recommendation {next_recommendation.id} doesn't have validation date!")
        
        if not next_recommendation.recommendation_comments:
            raise SchemaOrgException(self._article, f"Recommendation {next_recommendation.id} doesn't have decision!")
        
        if not next_recommendation.recommendation_comments:
            raise SchemaOrgException(self._article, f"Recommendation {next_recommendation.id} doesn't have decision!")

        associated_article = copy(self._scholarly_article)
        associated_article.version = next_recommendation.ms_version
        associated_article.same_as = common_small_html.mkLinkDOI(next_recommendation.doi)

        reviews = self._get_recommendation_reviews(recommendation)

        so_recommendation = so.Recommendation(
            date_created=next_recommendation.last_change.date(),
            date_published=next_recommendation.validation_timestamp.date(),
            review_body=self._clean_text(next_recommendation.recommendation_comments),
            author=self._get_author(next_recommendation.recommender_id),
            comment=self._get_author_reply(next_recommendation),
            item_reviewed=associated_article,
            associated_media=self._get_recommendation_medias(next_recommendation),
            associated_review=self._get_associated_recommendation_and_reviews(next_recommendation)
        )
        
        elements: List[Union[so.Recommendation, so.CriticReview]] = []
        elements.append(so_recommendation)
        elements.extend(reviews)
        return elements


    def _get_recommendation_reviews(self, recommendation: Recommendation):
        critic_reviews : List[so.CriticReview] = []

        reviews = Review.get_by_recommendation_id(
            recommendation.id,
            order_by=current.db.t_reviews.id,
            review_states=[ReviewState.REVIEW_COMPLETED])
        
        count_anonymous = 0
        for review in reviews:
            if not review.last_change:
                raise SchemaOrgException(self._article, f"Missing review publish date for review {review.id}")

            if review.anonymously:
                count_anonymous += 1
                anonymous_reviewer_no = common_tools.find_reviewer_number(review, count_anonymous)
                author = so.Person(f"anonymous reviewer {anonymous_reviewer_no}")
            else:
                author = self._get_author(review.reviewer_id)

            media: Optional[so.MediaObject] = None
            if review.review_pdf:
                media = so.MediaObject(content_url=Review.get_review_pdf_url(review),
                                    name="Review pdf file")

            critic_reviews.append(so.CriticReview(
                author=author,
                review_body=self._clean_text(review.review) if review.review else None,
                date_published=review.last_change.date(),
                associated_media=media
            ))

        return critic_reviews


    
    def _get_author_reply(self, recommendation: Recommendation):
        media: Optional[so.MediaObject] = None
        if recommendation.reply_pdf:
            media = so.MediaObject(
                content_url=Recommendation.get_reply_pdf_url(recommendation),
                name="Author's reply"
            )

        return so.Answer(
            author=self._get_article_authors(),
            text=self._clean_text(recommendation.reply) if recommendation.reply else None,
            associated_media=media
        )


    def _get_recommendation_body(self, recommendation: Recommendation):
        references = Recommendation.get_references(recommendation, True)
        citations: List[Union[so.ScholarlyArticle, so.CreativeWork]] = []
        abstract = recommendation.recommendation_comments

        if not abstract:
            raise SchemaOrgException(self._article, f"No recommendation comment found for recommendation {recommendation.id}")

        for reference in references:
            dois = common_tools.extract_url(reference)
            if len(dois) > 0:
                doi = dois[-1]
            else:
                doi = None

            if not doi:
                citation = so.CreativeWork(headline=reference)
            else:
                citation_text = reference.replace(doi, '').strip()
                citation = so.ScholarlyArticle(same_as=doi, about=citation_text)

            citations.append(citation)
        return citations


    def _get_author(self, user_id: int):
        if user_id in self._authors:
            return self._authors[user_id]
        else:
            user = User.get_by_id(user_id)
            if not user:
                raise SchemaOrgException(self._article, f"User {user_id} doesn't exist!")
            
            name = " ".join((user.first_name or '', user.last_name or ''))
            
            author = so.Person(
                name=name,
                identifier=f"https://orcid.org/{user.orcid}" if user.orcid else None,
                url=User.get_public_page_url(user.id),
            )

            return self._authors.setdefault(user_id, author)


    def _init_scholarly_article(self):
        article = self._article

        if not article.doi:
            raise SchemaOrgException(article, "Article doesn't have doi!")

        if not article.upload_timestamp:
            raise SchemaOrgException(article, "Article doesn't have upload timestamp!")

        if not article.validation_timestamp:
            raise SchemaOrgException(article, "Article doesn'nt have validation timestamp!")

        all_headlines: List[so.TranslatedField] = []
        all_abstracts: List[so.TranslatedField] = []
        all_keywords: List[so.TranslatedField] = []

        if article.title:
            all_headlines.append(so.TranslatedField(value=article.title, language=Lang.EN.value.code))

        if article.abstract:
            all_abstracts.append(so.TranslatedField(value=self._clean_text(article.abstract), language=Lang.EN.value.code))

        if article.keywords:
            all_keywords.append(so.TranslatedField(value=article.keywords, language=Lang.EN.value.code))

        title_translations = Article.get_all_translations(article, TranslatedFieldType.TITLE)
        abstract_translations = Article.get_all_translations(article, TranslatedFieldType.ABSTRACT)
        keywords_translations = Article.get_all_translations(article, TranslatedFieldType.KEYWORDS)

        if title_translations:
            for title_translation in title_translations:
                title = title_translation["content"]
                lang = title_translation["lang"]
                all_headlines.append(so.TranslatedField(value=title, language=lang))
        
        if abstract_translations:
            for abstract_translation in abstract_translations:
                abstract = self._clean_text(abstract_translation["content"])
                lang = abstract_translation["lang"]
                all_abstracts.append(so.TranslatedField(value=abstract, language=lang))

        if keywords_translations:
            for keywords_translation in keywords_translations:
                keywords = keywords_translation["content"]
                lang = keywords_translation["lang"]
                all_keywords.append(so.TranslatedField(value=keywords, language=lang))


        self._scholarly_article = so.ScholarlyArticle(
            same_as=common_small_html.mkLinkDOI(article.doi),
            image=Article.get_image_url(article),
            headline=all_headlines,
            author=self._get_article_authors(),
            archived_at=article.preprint_server,
            version=article.ms_version,
            abstract=all_abstracts,
            keywords=all_keywords,
            date_created=article.upload_timestamp.date(),
            date_published=article.validation_timestamp.date(),
            funder=article.funding,
            associated_media=self._get_article_medias()
        )

    def _get_article_medias(self):
        medias: List[so.MediaObject] = []

        if self._article.codes_doi:
            for code_doi in self._article.codes_doi:
                media = so.MediaObject(description="Codes used in this study", archived_at=code_doi)
                medias.append(media)
        
        if self._article.scripts_doi:
            for script_doi in self._article.scripts_doi:
                media = so.MediaObject(description="Scripts used to obtain or analyze results", archived_at=script_doi)
                medias.append(media)

        if self._article.data_doi:
            for data_doi in self._article.data_doi:
                media = so.MediaObject(description="Data used for results", archived_at=data_doi)
                medias.append(media)

        return medias
    

    def _get_recommendation_medias(self, recommendation: Recommendation):
        medias: List[so.MediaObject] = []

        if recommendation.track_change:
            medias.append(so.MediaObject(
                content_url=Recommendation.get_track_change_url(recommendation),
                name="Tracked changes file"
            ))

        return medias


    def _get_article_authors(self):
        if not self._article.authors:
            raise SchemaOrgException(self._article, "Article doesn't have authors!")

        authors = self._article.authors.split(",")
        persons: List[so.Person] = []
        for author in authors:
            person = so.Person(name=author)
            persons.append(person)

        return persons


    def _clean_text(self, text: str):
        text = common_tools.remove_html_tag(text)
        return text.replace('\n', ' ').replace('\r', '').strip()
