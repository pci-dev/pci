from pathlib import Path
import os
from typing import List

from gluon import current
from gluon.contrib.appconfig import AppConfig
from models.article import Article

from models.user import User
from app_modules import emailing
from app_modules.xml_jats_parser import XMLJATSArticleElement, XMLJATSParser, XMLJATSAuthorElement

myconf = AppConfig(reload=True)

XML_FOLDER = str(myconf.get("ftp.biorxiv"))

def main():
     application = str(current.request.application)

     for xml_file in os.listdir(XML_FOLDER):
          dest_app = get_destination_application(xml_file)
          if dest_app != application:
               continue
          
          xml_jats_parser = XMLJATSParser(f"{XML_FOLDER}/{xml_file}")
          
          user = add_author_in_db(xml_jats_parser.article.authors)
          if not user:
            raise(Exception("Unable to create user."))
          
          article = add_article_in_db(xml_jats_parser.article, user)     
          if not article:
               raise(Exception("Unable to create article"))

          emailing.send_to_coar_requester(current.session, current.auth, current.db, user, article)


def add_article_in_db(article_data: XMLJATSArticleElement, user: User):
     authors = f"{user.first_name} {user.last_name}"
     for author in article_data.authors:
          if author.email == user.email:
               continue

          authors += f", {author.first_name} {author.last_name}"

     article = Article.create_prefilled_submission(user.id, 
                                                   article_data.doi,
                                                   authors,
                                                   title=article_data.title,
                                                   abstract=article_data.abstract,
                                                   )
     return article


def add_author_in_db(authors: List[XMLJATSAuthorElement]):
        for author in authors:
            if not author.email or not author.first_name or not author.last_name:
                continue

            user = User.get_by_email(author.email)
            if not user:
                return User.create_new_user(author.first_name, 
                                            author.last_name, 
                                            author.email,
                                            institution=author.institution,
                                            country=author.country,
                                            orcid=author.orcid)


def get_destination_application(filepath: str):
        filename = Path(filepath).stem
        app_name = filename.split('_')[0]
        return app_name

if __name__ == '__main__':
    main()
