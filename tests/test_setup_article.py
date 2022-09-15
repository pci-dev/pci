from conftest import config, select
from conftest import login, logout
from conftest import test

import time
import pytest


users = config.users

submitter = users.user
recommender = users.recommender
reviewer = users.reviewer

class article:
    doi = "http://DOI"
    title = "Article Title [%s]" % time.strftime("%a %-d %b %Y %H:%M:%S")
    authors = "Author-1, Author-2"
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
    select("#t_articles_title").send_keys(article.title)
    select("#t_articles_authors").send_keys(article.authors)
    select("#t_articles_doi").send_keys(article.doi)
    if is_rr:
        select("#t_articles_report_stage").send_keys("Stage 1")
        select("#t_articles_ms_version").send_keys("v1")
        select("#t_articles_sub_thematics").send_keys("sub-thematic")

    if not is_rr:
        select("#t_articles_no_results_based_on_data").click()
        select("#t_articles_no_scripts_used_for_result").click()
        select("#t_articles_codes_used_in_study").click()
        select("#t_articles_codes_doi").send_keys("https://github.com/")

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
        select("#t_articles_funding_sources_listed").click()
        select("#t_articles_conflicts_of_interest_indicated").click()
        select("#t_articles_no_financial_conflict_of_interest").click()
    select("input[type=submit]").click()

    if is_rr:
        fill_survey()
        select("input[type=submit]").click()

    select(".w2p_flash", "Article submitted").wait_clickable()

 def search_and_suggest_recommender(_):
    select("a", "Suggest recommenders".upper()).click()
    select('#simple-search-input').clear()
    select('#simple-search-input').send_keys(recommender.name + "\n")
    select("a", "Suggest as recommender".upper()).click()

 def mail_sent_to_recommender(_):
    select(".w2p_flash").contains("Suggested recommender")
    select("a", "Done".upper()).click()

 def complete_submission(_):
    select("a", "Complete your submission".upper()).click()

    select(".pci-status", "SUBMISSION PENDING VALIDATION")

 def logout_user(_):
    logout(submitter)


def fill_survey():
    select("#t_report_survey_q1").send_keys("Complete Stage 1")
    select("#t_report_survey_q2").send_keys("Regular RR")
    select("#t_report_survey_q3").send_keys("Fully public")
    select("input[id^='q6YES']")[0].click()
    select("input[id^='q7No']").click()
    select("#t_report_survey_q8").send_keys("a reviewer")
    select("#t_report_survey_q9").send_keys("an opposed reviewer")
    select("#t_report_survey_q11").send_keys("yes")
    select("#t_report_survey_q12").send_keys("yes")
    select("#q13YES").click()
    select("#t_report_survey_q16").send_keys("make public")
    select("#t_report_survey_q17").send_keys("no embargo")
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
    select(".btn-success", "Validate this submission".upper()).click()
    select(".w2p_flash", "Request now available to recommenders").wait_clickable()

 def check_article_status_is_requiring_recommender(_):
    select(".dropdown-toggle", contains="For managers").click()
    select("a", f"All {articles}").click()
    select("tr", contains=article.title)
    select(".pci-status", f"{preprint} REQUIRING A RECOMMENDER".upper())

 def check_article_status_is_no_longer_pending_validation(_):
    select(".dropdown-toggle", contains="For managers").click()
    select("a", contains="Pending validation").click()
    with pytest.raises(KeyError):
        select("tr", contains=article.title)

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

    notif = select(".w2p_flash")
    notif.contains("e-mail sent to manager")
    notif.contains("e-mail sent to submitter")
    notif.contains("e-mail sent to " + recommender.name)

 def search_and_invite_registered_reviewer(_):
    select(".btn", contains="Choose a reviewer from the".upper()).click()
    select('#simple-search-input').send_keys(reviewer.name + "\n")

    select("a", "Prepare an invitation".upper()).click()
    select("input[type=submit]").click()

    select(".w2p_flash", contains="e-mail sent to " + reviewer.name)
    select("a", "Done".upper()).click()

 def invite_external_unregistered_reviewer(_):
    select(".dropdown-toggle", contains="For recommenders").click()
    select("a", f"{preprint.capitalize()}(s) you are handling").click()

    row = select("tr", contains=article.title)
    row.select(".btn", "Invite a reviewer".upper()).click()

    select(".btn", contains="Choose a reviewer outside".upper()).click()

    select("#no_table_reviewer_first_name").send_keys("Titi")
    select("#no_table_reviewer_last_name").send_keys("Toto")
    select("#no_table_reviewer_email").send_keys("ratalatapouet@toto.com")

    select("input[type=submit]").click()
    notif = select(".w2p_flash")
    notif.contains("e-mail sent to Titi Toto")
    # message 'User "ratalatapouet@toto.com" created' shown only first time

 def logout_recommender(_):
    logout(users.recommender)
