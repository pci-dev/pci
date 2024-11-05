from datetime import datetime
from pathlib import Path
import os
import secrets
import shutil
import time
from typing import List

from gluon import current
from gluon.contrib.appconfig import AppConfig  # type: ignore
from models.article import Article

from models.user import User
from app_modules import emailing
from app_modules.xml_jats_parser import (
    DestinationApp,
    XMLJATSArticleElement,
    XMLJATSParser,
    XMLJATSAuthorElement,
)

myconf = AppConfig(reload=True)

XML_FOLDER = Path(str(myconf.get("ftp.biorxiv")))
DONE_FOLDER = XML_FOLDER.joinpath("done")
FAILED_FOLDER = XML_FOLDER.joinpath("failed")


def main():
    create_done_folder()
    create_failed_folder()
    clean_folder(DONE_FOLDER)
    clean_folder(FAILED_FOLDER)

    try:
        application = DestinationApp(str(current.request.application))
    except:
        log(f"Application {current.request.application} not found")
        return

    for file_name in os.listdir(XML_FOLDER):
        if not file_name.endswith(".xml"):
            continue

        xml_file = os.path.join(XML_FOLDER, file_name)

        if os.path.getsize(xml_file) == 0:
            fail(f"File {xml_file} is empty", xml_file)
            continue

        try:
            xml_jats_parser = XMLJATSParser(xml_file)
        except Exception as e:
            fail(f"Error to parse {xml_file}: {e}", xml_file)
            continue

        if not application_supported(xml_jats_parser.destination):
            fail(
                f"Destination {xml_jats_parser.destination.value} exists, but not supported"
                , xml_file
            )
            continue

        if xml_jats_parser.destination != application:
            continue

        user = add_author_in_db(xml_jats_parser.article.authors)
        if not user:
            fail(f"Unable to create or find user from document {xml_file}", xml_file)
            continue

        dup_info = check_duplicate_submission(xml_jats_parser.article)
        if dup_info:
            fail(f"Duplicate submission: {dup_info} ({xml_file})", xml_file)
            continue

        article = add_article_in_db(xml_jats_parser.article, user)
        if not article:
            fail(f"Unable to create article from document {xml_file}", xml_file)
            continue

        emailing.send_to_biorxiv_requester(user, article)
        emailing.send_import_biorxiv_alert(xml_file, "Success")
        clean_xml(xml_file, failed=False)


def fail(msg: str, xml_file: str):
    log(msg)
    emailing.send_import_biorxiv_alert(xml_file, msg)
    clean_xml(xml_file, failed=True)


def check_duplicate_submission(article_data):
    same_title = db(db.t_articles.title.lower() == article_data.title.lower()).count()
    same_url = db(db.t_articles.doi.lower() == article_data.doi.lower()).count()

    dup_info = (
            "title" + (" and url" if same_url else "") if same_title else
            "url" if same_url else None
    )
    if same_title or same_url:
        return(f"an article with the same {dup_info} already exists")



def add_article_in_db(article_data: XMLJATSArticleElement, user: User):
    authors: List[str] = []
    for author in article_data.authors:
        if author.email == user.email:
            continue

        authors.append(f"{author.first_name} {author.last_name}")

    authors.append(f"{user.first_name} {user.last_name}")

    article = Article.create_prefilled_submission(
        user.id,
        article_data.doi,
        ", ".join(authors),
        title=article_data.title,
        abstract=article_data.abstract,
        ms_version=str(article_data.version),
        article_year=article_data.year,
        preprint_server=article_data.journal,
        pre_submission_token=secrets.token_urlsafe(64),
    )

    log(f"Article added in database: {article}")

    return article


def add_author_in_db(authors: List[XMLJATSAuthorElement]):
    for author in authors:
        if not author.email or not author.first_name or not author.last_name:
            log(f"Missing author information: {author}")
            continue

        user = User.get_by_email(author.email)
        if user:
            log(f"Author already exists in database: {author} corresponding to {user}")
            return user
        else:
            user = User.create_new_user(
                author.first_name,
                author.last_name,
                author.email,
                institution=author.institution,
                country=author.country,
                orcid=author.orcid,
            )
            log(f"Author {author} added in database: {user}")
            return user


def application_supported(destination: DestinationApp):
    app_dir = os.path.join("applications")
    for dir in os.listdir(app_dir):
        try:
            app = DestinationApp(dir)
            if app == destination:
                return True
        except:
            continue
    return False


def create_done_folder():
    if not os.path.exists(DONE_FOLDER):
        os.makedirs(DONE_FOLDER)
        log(f"{DONE_FOLDER} created")


def create_failed_folder():
    if not os.path.exists(FAILED_FOLDER):
        os.makedirs(FAILED_FOLDER)
        log(f"{FAILED_FOLDER} created")


def clean_xml(xml_file: str, failed: bool):
    base_name = Path(xml_file).stem
    archive_name = f"{base_name}.zip"
    archive_file = os.path.join(XML_FOLDER, archive_name)
    try:
        os.remove(archive_file)
    except OSError:
        log(f"No archive to clean found: {archive_file}")
        pass

    if failed:
        dest_folder = FAILED_FOLDER
    else:
        dest_folder = DONE_FOLDER
    move_file(xml_file, dest_folder)
    log(f"{xml_file} moved to {dest_folder}")


def clean_folder(folder_path: Path):
    max_life_time = time.time() - 30 * 24 * 60 * 60  # 30 days
    for file_name in os.listdir(folder_path):
        file = os.path.join(folder_path, file_name)
        if not os.path.isfile(file):
            continue

        file_age = os.path.getmtime(file)
        if file_age <= max_life_time:
            os.remove(file)
            log(f"{file} has been removed")


def move_file(file_path: str, dest_folder: Path):
    file_path_obj = Path(file_path)

    file_name = file_path_obj.name
    origin_folder = file_path_obj.resolve().parent
    base_name = file_path_obj.stem
    extension = file_path_obj.suffix

    if not os.path.exists(f"{dest_folder}/{file_name}"):
        return shutil.move(file_path, dest_folder)

    i = 1
    new_file_name = f"{base_name}-{i}{extension}"
    while os.path.exists(f"{dest_folder}/{new_file_name}"):
        i += 1
        new_file_name = f"{base_name}-{i}{extension}"

    return shutil.move(f"{origin_folder}/{file_name}", f"{dest_folder}/{new_file_name}")


def log(content: str):
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    script = "import_biorxiv_xml.py"
    app = str(current.request.application)

    print(f"{now} {app}:{script} {content}")


if __name__ == "__main__":
    main()
