from conftest import test, select, login, logout, users
from conftest import config

import os
import time

from datetime import datetime, timedelta

submitter = users.user
recommender = users.recommender
reviewer = users.reviewer

class article:
    doi = "http://DOI"
    title = "Title [%s]" % time.strftime("%a %-d %b %Y %H:%M:%S")
    authors = "Author-1, Author-2"
    year = time.strftime("%Y")
    abstract = "Abstract"
    keywords = "Keywords"
    cover_letter = "Cover letter"

is_rr = config.is_rr

preprint = "preprint" if not is_rr else "report"
articles = "articles" if not is_rr else "reports"


@test
class User_submits:

 def login_as_user(_):
    login(submitter)

 def initiate_submit_preprint(_):
    select(".btn-success", f"Submit a {preprint}".upper()).click()
    select(".btn-success", f"Submit your {preprint}".upper()).click()

 def submit_submission_form(_):
    if is_rr:
      select("#no_table_report_stage").send_keys("STAGE 1")
      select("#no_table_title").send_keys(article.title)
      select("input[type=submit]").click()
    select("#t_articles_title").send_keys(article.title)
    select("#t_articles_authors").send_keys(article.authors)
    select("#t_articles_article_year").send_keys(article.year)
    select("#t_articles_doi").send_keys(article.doi)
    select("#t_articles_preprint_server").send_keys("Preprint server")

    art_version = "1" if not is_rr else "v1"
    select("#t_articles_ms_version").send_keys(art_version)

    if is_rr:
        select("#t_articles_sub_thematics").send_keys("sub-thematic")

    if not is_rr:
        select("#t_articles_uploaded_picture").send_keys(os.getcwd() + "/image.png")
        select("#t_articles_no_results_based_on_data").click()
        select("#t_articles_no_scripts_used_for_result").click()
        select("#t_articles_codes_used_in_study").click()
        select("#t_articles_codes_doi").send_keys("https://github.com/")
        select("#t_articles_funding").send_keys("The authors declare that they have received no specific funding for this study")

    with select("#t_articles_abstract_ifr").frame():
        select("body").send_keys(article.abstract)
    select("#t_articles_keywords").send_keys(article.keywords)
    with select("#t_articles_cover_letter_ifr").frame():
        select("body").send_keys(article.cover_letter)

    select('input[name="thematics"]')[0].click()
    select("#t_articles_i_am_an_author").click()
    select("#t_articles_is_not_reviewed_elsewhere").click()
    if not is_rr:
        select("#t_articles_guide_read").click()
        select("#t_articles_approvals_obtained").click()
        select("#t_articles_human_subject_consent_obtained").click()
        select("#t_articles_lines_numbered").click()
        select("#t_articles_conflicts_of_interest_indicated").click()
        select("#t_articles_no_financial_conflict_of_interest").click()
    select("input[type=submit]").click()

    if is_rr:
        fill_survey()
        select("input[type=submit]").click()

    article_submitted = "Article submitted" \
        if not is_rr else "Survey saved. Report NOT yet submitted"
    select.notif(article_submitted).wait_clickable()

 def search_and_suggest_recommender(_):
    select("a", "Suggest recommenders".upper()).click()
    select('#simple-search-input').clear()
    select('#simple-search-input').send_keys(recommender.name + "\n")
    select('#simple-search-btn').click()
    suggest_btn = "Suggest" if is_rr else "Suggest as recommender"
    select("a", suggest_btn.upper()).click()

 def mail_sent_to_recommender(_):
    select.notif().contains("Suggested recommender")
    select("a", "Done".upper()).click()

 def complete_submission(_):
    select("a", "Complete your submission".upper()).click()
    time.sleep(.1)
    select(".pci-status", "SUBMISSION PENDING VALIDATION")

 def logout_user(_):
    logout(submitter)


def fill_survey():
    report_type = "RR SNAPSHOT" if is_rr.scheduled_track else "COMPLETE"

    select("#t_report_survey_q1").send_keys(report_type)
    select("#t_report_survey_q2").send_keys("Regular RR")
    select("#t_report_survey_q3").send_keys("Fully public")
    select("input[id^='q6YES']")[0].click()
    select("input[id^='q7No']").click()
    select("#t_report_survey_q8").send_keys("a reviewer")
    select("#t_report_survey_q9").send_keys("an opposed reviewer")
    if is_rr.scheduled_track:
        report_due_date = datetime.now() + timedelta(weeks=7)
        report_due_date -= timedelta(days=report_due_date.weekday())
        select("#t_report_survey_q10").send_keys(report_due_date.strftime("%Y-%m-%d"))
        select("#t_report_survey_q1_1").send_keys("https://snapshot.URL")
        select("#t_report_survey_q4").click()
    select("#t_report_survey_q11").send_keys("yes")
    select("#t_report_survey_q12").send_keys("yes")
    select("#q13YES").click()
    select("#t_report_survey_q16").send_keys("make public")
    select("#t_report_survey_q20").send_keys("yes")
    select("#t_report_survey_q21").send_keys("publish")
    select("#t_report_survey_q22").send_keys("yes")
    select("#t_report_survey_q23").send_keys("6 months")
    select("#t_report_survey_q24").send_keys("2022-01-01")
    select("#t_report_survey_q24_1").send_keys("flexibility 2 months")


@test
class Manager_validates:

 def login_as_manager(_):
    login(users.manager)

 def check_article_shown_in_pending_validation(_):
    select(".dropdown-toggle span", "For managers").click()
    select(".dropdown-menu span", contains="Pending validation").click()
    select("tr", contains=article.title)
    select(".pci-status", "SUBMISSION PENDING VALIDATION")

 def validate_submission(_):
    #select("a", "View / Edit").first().click()  # select(css, text/contains=xxx) should return a list-ish
    select("a", "View / Edit".upper()).click()
    if not is_rr:
        select("#article_doi_correct").click()
        select("#data_ok").click()
        select("#code_and_scripts_ok").click()
        select("#scope_ok").click()
        select("#information_consistent").click()
        select("#no_plagiarism").click()
    select(".btn-success", "Validate this submission".upper()).click()
    select('#confirm-change-modal .btn-info', 'Yes'.upper()).click()
    select.notif("Request now available to recommenders").wait_clickable()

 def check_article_status_is_requiring_recommender(_):
    select(".dropdown-toggle", contains="For managers").click()
    select("a", f"All {articles}").click()
    select("tr", contains=article.title)
    select(".pci-status", f"{preprint} REQUIRING A RECOMMENDER".upper())

 def check_article_status_is_no_longer_pending_validation(_):
    select(".dropdown-toggle", contains="For managers").click()
    select("a", contains="Pending validation").click()
    select.fails("tr", contains=article.title)

 def logout_manager(_):
    logout(users.manager)


@test
class Recommender_handles:

 def login_as_recommender(_):
    login(users.recommender)

 def accept_to_recommend(_):
    select(".dropdown-toggle", contains="For recommenders").click()
    select("a", contains=f"Request(s) to handle a {preprint}").click()

    row = select("tr", contains=article.title)
    row.select(".pci-status", f"{preprint} REQUIRING A RECOMMENDER".upper())
    row.select("a", "VIEW").click()

    select(".btn-success.pci-recommender").click()
    assert select("input[type=submit]").get_attribute("disabled")
    for cb in select("input[type=checkbox]"):
        cb.click()
    select("input[type=submit]").click()

    notif = select.notif()
    notif.contains("e-mail sent to admin")
    notif.contains("e-mail sent to submitter")
    notif.contains("e-mail sent to " + recommender.name)

 def search_and_invite_registered_reviewer(_):
    select(".btn", contains= "Invite a reviewer".upper()).click()

    select("#no_table_reviewer_first_name").send_keys(reviewer.name)
    select("#no_table_reviewer_last_name").send_keys("dude")
    select("#no_table_reviewer_email").send_keys(reviewer.email)

    select("input[type=submit]").click()

    select.notif(contains="e-mail sent to " + reviewer.name)
    select("a", "Done".upper()).click()

 def invite_external_unregistered_reviewer(_):
    select(".dropdown-toggle", contains="For recommenders").click()
    select("a", f"{preprint.capitalize()}(s) you are handling").click()

    row = select("tr", contains=article.title)
    row.select(".btn", "Invite a reviewer".upper()).click()

    select(".btn", contains="Invite a reviewer".upper()).click()

    select("#no_table_reviewer_first_name").send_keys("Titi")
    select("#no_table_reviewer_last_name").send_keys("Toto")
    select("#no_table_reviewer_email").send_keys("ratalatapouet@toto.com")

    select("input[type=submit]").click()
    notif = select.notif()
    notif.contains("e-mail sent to Titi Toto")
    # message 'User "ratalatapouet@toto.com" created' shown only first time

 def logout_recommender(_):
    logout(users.recommender)
