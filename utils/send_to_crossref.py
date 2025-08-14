import argparse

from app_modules.crossref import post_to_crossref
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

    post_response = post_to_crossref(article)
    if post_response:
        print(post_response)
        return

    print("Send!")


if __name__ == "__main__":
    main()
