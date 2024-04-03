from datetime import datetime
from typing import Optional as _, cast
from models.article import Article
from pydal.objects import Row
from gluon import current

class ReportSurvey(Row):
    id: int
    article_id: int
    q1: _[str]
    q2: _[str]
    q3: _[str]
    q4: _[bool]
    q5: _[str]
    q6: _[str]
    q7: _[str]
    q8: _[str]
    q9: _[str]
    q10: _[datetime]
    q11: _[str]
    q11_details: _[str]
    q12: _[str]
    q12_details: _[str]
    q13: _[str]
    q13_details: _[str]
    q14: _[bool]
    q15: _[str]
    q16: _[str]
    q17: _[str]
    q18: _[bool]
    q19: _[bool]
    q20: _[str]
    q21: _[str]
    q22: _[str]
    q23: _[str]
    q24: _[datetime]
    q24_1: _[str]
    q25: _[bool]
    q26: _[str]
    q26_details: _[str]
    q27: _[str]
    q27_details: _[str]
    q28: _[str]
    q28_details: _[str]
    q29: _[bool]
    q30_details: _[str]
    q31: _[str]
    temp_art_stage_1_id: _[int]
    q32: _[bool]
    q1_1: _[str]
    q1_2: _[str]
    tracked_changes_url: _[str]
    q30: _[str]
    report_server: _[str]


    @staticmethod
    def get_by_article(article_id: int):
        db = current.db
        return cast(_[ReportSurvey], db(db.t_report_survey.article_id == article_id).select().last())
    

    @staticmethod
    def get_merged_report_survey(article: Article):
        db = current.db
        if not article.art_stage_1_id:
            return ReportSurvey.get_by_article(article.id)
        
        report_survey_stage_1 = ReportSurvey.get_by_article(article.art_stage_1_id)
        report_survey_stage_2 = ReportSurvey.get_by_article(article.id)

        for attr in vars(report_survey_stage_2):
            value_attr_report_survey_stage_1 = getattr(report_survey_stage_1, attr)
            value_attr_report_survey_stage_2 = getattr(report_survey_stage_2, attr)

            if value_attr_report_survey_stage_1 is not None and value_attr_report_survey_stage_2 is None:
                setattr(report_survey_stage_2, attr, value_attr_report_survey_stage_1)

        return report_survey_stage_2



