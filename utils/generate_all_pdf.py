import os
from typing import List
from app_modules import crossref
from app_modules.clockss import send_to_clockss
from gluon import current
from models.article import Article, ArticleStage, ArticleStatus
from models.user import User
import argparse
from gluon.contrib.appconfig import AppConfig # type: ignore

# To launch script:
# python web2py.py -M -S {APP_NAME} -R applications/{APP_NAME}/utils/generate_all_pdf.py -A manager_mail


def main():

    config = AppConfig(reload=True)
    is_RR: bool = config.get("config.registered_reports", default=False)

    parser = argparse.ArgumentParser()
    parser.add_argument("mail", help="PCI user email used to compile latex (must be manager)", type=str)
    args = parser.parse_args()

    login(args.mail)

    current.request.folder = f"{os.getcwd()}/{current.request.folder}"
    current.request.env.http_host = config.take("alerts.host")

    articles = Article.get_by_status([ArticleStatus.RECOMMENDED])
    if is_RR:
        articles = list(filter(lambda a: a.report_stage == ArticleStage.STAGE_2.value, articles))

    count_ok = 0
    nok_crossref: List[int] = []
    nok_clockss: List[int] = []

    for article in articles:
        recommendation = Article.get_last_recommendation(article.id)

        if not recommendation:
            print(f"Article {article.id}: No recommendation found")
            continue

        status = crossref.async_post_to_crossref(article)
        if status:
            nok_crossref.append(article.id)
            print(f"Error to post to crossref: {status}")
            continue
        else:
            try:
                send_to_clockss(article, recommendation)
            except Exception as e:
                nok_clockss.append(article.id)
                print(f"Error to send to clockss: {e}")
                continue

        current.db.commit()
        count_ok += 1

    print("\n### RESULT ###\n")
    print(f"Total of recommended articles: {len(articles)}")
    if len(nok_crossref) > 0:
        print(f"{len(nok_crossref)} article(s) failed for crossref: {nok_crossref}")
    if len(nok_clockss) > 0:
        print(f"{len(nok_clockss)} article(s) failed for clockss: {nok_clockss}")
    print(f"Number of successes: {count_ok}")


def login(mail: str):
    user = User.get_by_email(mail)
    if user:
        current.auth.login_user(user)


if __name__ == "__main__":
    main()
