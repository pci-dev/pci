import argparse
from time import sleep
from typing import Optional

from app_modules.crossref import CrossrefXML, XMLException, post_to_crossref
from models.article import Article


def main():
    parser = argparse.ArgumentParser(
        prog="To send XML to Crossref", description="Generate XML and send to Crossref"
    )

    parser.add_argument("article_id", type=str)

    args = parser.parse_args()

    article_id = int(args.article_id)

    article = Article.get_by_id(article_id)
    if not article:
        print("Article not found")
        return

    xml: Optional[CrossrefXML] = None
    count = 0
    while xml is None and count <= 10:
        count += 1
        xml = CrossrefXML.build(article)
        try:
            xml.raise_error()
        except XMLException:
            xml = None
            sleep(3)

    if not xml:
        return

    post_response = post_to_crossref(article, xml)
    if post_response:
        print(post_response)
        return

    print("Send!")
if __name__ == "__main__":
    main()
