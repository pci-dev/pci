import csv
import datetime
from enum import Enum
import os
import argparse
from typing import Dict, List

from gluon import current
from gluon.contrib.appconfig import AppConfig # type: ignore

from models.article import Article
from models.recommendation import Recommendation, RecommendationState
from models.user import User

"""
Script to extract data in PCI database and create CSV.
To launch this script : 
./web2py.py --no-banner -M -S $pci -R applications/$pci/utils/extract_data.py -A $filepath --start-year 2023 --end-year 2025"
"""


myconf = AppConfig(reload=True)
db = current.db


class Header(Enum):
    PCI_NAME = "Nom de la PCI"
    REF_ARTICLE = "Référence de l'article recommendé"
    SUBMITTER_NAME = "Nom du submitter"
    RECOMMENDATION_DATE = "Date de la recommendation"
    PUBLISHED_ARTICLE_DOI = "DOI du published now in"
    SUBMITTER_MAIL = "Mail du submitter"


parser = argparse.ArgumentParser()
parser.add_argument('file_path', help='Export file path', type=str)
parser.add_argument('--start-year', help='Start request year', type=int, required=True)
parser.add_argument('--end-year', help='End request year', type=int, required=True)

args = parser.parse_args()


def main():
    file_path = str(args.file_path)
    start_year = int(args.start_year)
    end_year = int(args.end_year)

    lines = get_data(start_year, end_year)
    write_in_csv(lines, file_path)


def get_data(start_year: int, end_year: int):
    start_date = datetime.datetime(year=start_year, month=1, day=1)
    end_date = datetime.datetime(year=end_year, month=12, day=31)

    result = db(
          (db.t_articles.id == db.t_recommendations.article_id)
        & (db.auth_user.id == db.t_articles.user_id)
        & (db.t_recommendations.validation_timestamp >= start_date)
        & (db.t_recommendations.validation_timestamp <= end_date)
        & (db.t_recommendations.recommendation_state == RecommendationState.RECOMMENDED.value)
    ).select(distinct=True)

    lines: List[Dict[str, str]] = []

    for r in result:
        article: Article = r.t_articles
        recommendation: Recommendation = r.t_recommendations
        submitter: User = r.auth_user

        line: Dict[str, str] = {
            Header.PCI_NAME.value: myconf.get("app.longname"),
            Header.REF_ARTICLE.value: Article.get_article_reference(article, False).strip(),
            Header.SUBMITTER_NAME.value: User.get_name(submitter),
            Header.RECOMMENDATION_DATE.value: recommendation.validation_timestamp.strftime("%Y-%m-%d") if recommendation.validation_timestamp else "",
            Header.PUBLISHED_ARTICLE_DOI.value: article.doi_of_published_article or "",
            Header.SUBMITTER_MAIL.value: submitter.email or ""
        }

        lines.append(line)
    return lines


def write_in_csv(lines: List[Dict[str, str]], file_path: str):
    creation = not os.path.isfile(file_path)

    with open(file_path, 'a') as file:
        csv_writer = csv.DictWriter(file, [h.value for h in Header])

        if creation:
            csv_writer.writeheader()

        csv_writer.writerows(lines)


if __name__ == '__main__':
    main()
