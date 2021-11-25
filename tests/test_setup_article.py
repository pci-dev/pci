from conftest import config, select
from conftest import login, logout
from conftest import test

import time
import configparser
import pytest


users = config.users


from argparse import Namespace

articleTitle = "Article Title [%s]" % time.asctime()

submitter = Namespace(
    firstname="Submitter",
    lastname="Dude",
    )
recommender = Namespace(
    firstname="Recommender",
    lastname="Dude",
    )
data = Namespace(
    doi = "DOI",
    abstract = "Abstract",
    keywords = "Keywords",
    cover_letter = "Cover letter",
    )


def is_RR():
    config = configparser.ConfigParser()
    config.read("../private/appconfig.ini")
    return bool(config["config"]["registered_reports"])

is_rr = is_RR()

preprint = "preprint" if not is_rr else "report"
article = "article" if not is_rr else "report"


@test
class User_submits:

 def login_as_user(_):
    login(users.user)

 def initiate_submit_preprint(_):
    select(".btn-success", f"Submit a {preprint}".upper()).click()
    select(".btn-success", f"Submit your {preprint}".upper()).click()

 def submit_submission_form(_):
    select("#t_articles_title").send_keys(articleTitle)
    select("#t_articles_authors").send_keys(submitter.firstname + " " + submitter.lastname)
    select("#t_articles_doi").send_keys(data.doi)
    if is_rr:
        select("#t_articles_report_stage").send_keys("Stage 1")
        select("#t_articles_ms_version").send_keys("v1")
        select("#t_articles_sub_thematics").send_keys("sub-thematic")

    with select("#t_articles_abstract_ifr").frame():
        select("body").send_keys(data.abstract)
    select("#t_articles_keywords").send_keys(data.keywords)
    with select("#t_articles_cover_letter_ifr").frame():
        select("body").send_keys(data.cover_letter)

    select('input[name="thematics"]')[0].click()
    select("#t_articles_i_am_an_author").click()
    select("#t_articles_is_not_reviewed_elsewhere").click()
    select("input[type=submit]").click()

    select(".w2p_flash", "Article submitted").wait_clickable()

    if is_rr:
        fill_survey()
        select("input[type=submit]").click()

 def search_and_suggest_recommender(_):
    select("a", "Suggest recommenders".upper()).click()
    select('input[name="qyKeywords"]').clear()
    select('input[name="qyKeywords"]').send_keys(recommender.firstname + "\n")
    select("a", "Suggest as recommender".upper()).click()

 def mail_sent_to_recommender(_):
    select(".w2p_flash").contains("Suggested recommender")
    select("a", "Done".upper()).click()

 def complete_submission(_):
    select("a", "Complete your submission".upper()).click()

    select(".pci-status", "SUBMISSION PENDING VALIDATION")

 def logout_user(_):
    logout(users.user)


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
    select("tr", contains=articleTitle)
    select(".pci-status", "SUBMISSION PENDING VALIDATION")

 def validate_submission(_):
    #select("a", "View / Edit").first().click()  # select(css, text/contains=xxx) should return a list-ish
    select("a", "View / Edit".upper()).click()
    select(".btn-success", "Validate this submission".upper()).click()
    select(".w2p_flash", "Request now available to recommenders").wait_clickable()

 def check_article_status_is_requiring_recommender(_):
    select(".dropdown-toggle", contains="For managers").click()
    select("a", f"All {article}s").click()
    select("tr", contains=articleTitle)
    select(".pci-status", f"{preprint} REQUIRING A RECOMMENDER".upper())

 def check_article_status_is_no_longer_pending_validation(_):
    select(".dropdown-toggle", contains="For managers").click()
    select("a", contains="Pending validation").click()
    with pytest.raises(KeyError):
        select("tr", contains=articleTitle)

 def logout_manager(_):
    logout(users.manager)


@test
class Recommender_handles:

 def login_as_recommender(_):
    login(users.recommender)

 """

    it("Should show 'Request(s) to handle a preprint' enhanced menu", () => {
      select(".dropdown-toggle", "For recommenders").click();
      select("a", "Request(s) to handle a preprint").click();

    it("Should show article in 'Request(s) to handle a preprint' page", () => {
      select("tr", articleTitle).should("exist");
      select(".pci-status", "PREPRINT REQUIRING A RECOMMENDER").should("exist");

    it("Should accept to recommend the preprint", () => {
      select("a", "View").first().click();
      select(".btn-success.pci-recommender").click();

      select("input[type=submit]").should("have.attr", "disabled");
      select("input[type=checkbox]").each(($el) => {
        $el.click();
      });
      select("input[type=submit]").should("not.have.attr", "disabled");
      select("input[type=submit]").click();

    it("=> mail sent to manager, submitter and recommender", () => {
      cy.wait(500);
      select(".w2p_flash", "e-mail sent to manager").should("exist");
      select(".w2p_flash", "e-mail sent to submitter").should("exist");
      select(".w2p_flash", "e-mail sent to " + recommender.firstname).should("exist");

    it("Should search for reviewer (developer user)", () => {
      select(".btn", "Choose a reviewer from the PCI Evol Biol DEV database").click();

      select('input[name="qyKeywords"]').send_keys(reviewer.firstname);
      select(".pci2-search-button").click();

      select("a", "Prepare an invitation").should("exist");

    it("Should invite reviewer", () => {
      select("a", "Prepare an invitation").click();
      select("input[type=submit]").click();

    it("=> mail sent to reviewer", () => {
      cy.wait(500);
      select(".w2p_flash", "e-mail sent to " + reviewer.firstname).should("exist");
      select("a", "Done").click();

    it("Should show article in list of articles", () => {
      select("tr", articleTitle).should("exist");


  describe("Recommender :  invite external un-registered reviewer", () => {

    it("Should show article in recommender dashboard", () => {
      select(".dropdown-toggle", "For recommenders").click();
      select("a", "Preprint(s) you are handling").click();
      select(".doi_url", data.doi).should("exist");

    it("Should invite reviewer outside PCI database", () => {
      select(".btn", "Invite a reviewer").first().click();
      select(".btn", "Choose a reviewer outside PCI Evol Biol DEV database").click();

      select("#no_table_reviewer_first_name").send_keys("Titi");
      select("#no_table_reviewer_last_name").send_keys("Toto");
      select("#no_table_reviewer_email").send_keys("ratalatapouet@toto.com");

      select("input[type=submit]").click();

    it("=> mail sent to reviewer outside PCI db", () => {
      cy.wait(500);
      select(".w2p_flash", "e-mail sent to Titi Toto").should("exist");
 """

 def logout_recommender(_):
    logout(users.recommender)
