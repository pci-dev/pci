import os
from app_modules import crossref
from app_modules.clockss import send_to_clockss
from gluon import current
from models.article import Article, ArticleStatus


# To launch script:
# python web2py.py -M -S {APP_NAME} -R applications/pci/utils/generate_all_pdf.py


def main():
    current.request.folder = f"{os.getcwd()}/{current.request.folder}"

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


if __name__ == "__main__":
    main()
