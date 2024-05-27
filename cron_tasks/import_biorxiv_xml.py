from pathlib import Path
import os
import shutil
import time
from typing import List

from gluon import current
from gluon.contrib.appconfig import AppConfig
from models.article import Article

from models.user import User
from app_modules import emailing
from app_modules.xml_jats_parser import DestinationApp, XMLJATSArticleElement, XMLJATSParser, XMLJATSAuthorElement

myconf = AppConfig(reload=True)

XML_FOLDER = str(myconf.get("ftp.biorxiv"))
DONE_FOLDER = f"{XML_FOLDER}/done"

def main():
     create_done_folder()
     clean_done_folder()

     try:
          application = DestinationApp(str(current.request.application))
     except:
          print(f"No application in destination app list with name: {current.request.application}")
          return

     for file_name in os.listdir(XML_FOLDER):
          if not file_name.endswith('.xml'):
               continue

          xml_file = os.path.join(XML_FOLDER, file_name)
          
          try:
               xml_jats_parser = XMLJATSParser(xml_file)
          except Exception as e:
               print(f"Error to parse {xml_file}: {e}")
               emailing.send_import_biorxiv_alert(xml_file, True)
               clean_xml(xml_file)
               continue

          if xml_jats_parser.destination != application:
               continue

          emailing.send_import_biorxiv_alert(xml_file, False)
          clean_xml(xml_file)
          
          user = add_author_in_db(xml_jats_parser.article.authors)
          if not user:
               print(f"Unable to create or find user from document {xml_file}")
               continue
          
          article = add_article_in_db(xml_jats_parser.article, user)     
          if not article:
               print(f"Unable to create article from document {xml_file}")
               continue

          emailing.send_to_coar_requester(current.session, current.auth, current.db, user, article)


def add_article_in_db(article_data: XMLJATSArticleElement, user: User):
     authors: List[str] = []
     for author in article_data.authors:
          if author.email == user.email:
               continue

          authors.append(f"{author.first_name} {author.last_name}")

     authors.append(f"{user.first_name} {user.last_name}")

     article = Article.create_prefilled_submission(user.id, 
                                                   article_data.doi,
                                                   ", ".join(authors),
                                                   title=article_data.title,
                                                   abstract=article_data.abstract,
                                                   ms_version=article_data.version,
                                                   article_year=article_data.year,
                                                   preprint_server=article_data.journal)
     
     return article


def add_author_in_db(authors: List[XMLJATSAuthorElement]):
        for author in authors:
            if not author.email or not author.first_name or not author.last_name:
                continue

            user = User.get_by_email(author.email)
            if user:
                 return user
            else:
                return User.create_new_user(author.first_name, 
                                            author.last_name, 
                                            author.email,
                                            institution=author.institution,
                                            country=author.country,
                                            orcid=author.orcid)


     


def create_done_folder():
     if not os.path.exists(DONE_FOLDER):
          os.makedirs(DONE_FOLDER)
          print(f"{DONE_FOLDER} created")


def clean_xml(xml_file: str):
     base_name = Path(xml_file).stem
     archive_name = f"{base_name}.zip"
     archive_file = os.path.join(XML_FOLDER, archive_name)
     try:
          os.remove(archive_file)
     except OSError:
          print(f'No archive to clean found: {archive_file}')
          pass
     
     shutil.move(xml_file, DONE_FOLDER)


def clean_done_folder():
     max_life_time = time.time() - 30 * 24 * 60 * 60 # 30 days
     for file_name in os.listdir(DONE_FOLDER):
          file = os.path.join(DONE_FOLDER, file_name)
          if not os.path.isfile(file):
               continue
          
          file_age = os.path.getmtime(file)
          if file_age <= max_life_time:
               os.remove(file)
               print(f"{file} has been removed")


if __name__ == '__main__':
    main()
