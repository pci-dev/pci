import os
from app_modules import crossref
from app_modules.clockss import send_to_clockss
from gluon import current
from models.article import Article, ArticleStatus
from models.user import User
import argparse
from gluon.contrib.appconfig import AppConfig # type: ignore

# To launch script:
# python web2py.py -M -S {APP_NAME} -R applications/{APP_NAME}/utils/generate_all_pdf.py -A manager_mail


def main():

    config = AppConfig(reload=True)

    parser = argparse.ArgumentParser()
    parser.add_argument("mail", help="PCI user email used to compile latex (must be manager)", type=str)
    args = parser.parse_args()

    login(args.mail)

    current.request.folder = f"{os.getcwd()}/{current.request.folder}"
    current.request.env.http_host = config.take("alerts.host")

    articles = Article.get_by_status([ArticleStatus.RECOMMENDED])

    for article in articles:
        recommendation = Article.get_last_recommendation(article.id)

        if not recommendation:
            print(f"Article {article.id}: No recommendation found")
            continue

        generated_xml = crossref.crossref_xml(recommendation)

        status = crossref.post_and_forget(recommendation, generated_xml)
        if status:
            print(f"Error to post to crossref: {status}")
            continue
        else:
            try:
                send_to_clockss(article, recommendation)
            except Exception as e:
                print(f"Error to send to clockss: {e}")

        current.db.commit()


def login(mail: str):
    user = User.get_by_email(mail)
    if user:
        current.auth.login_user(user)


if __name__ == "__main__":
    main()
