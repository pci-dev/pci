from conftest import DEFAULT_SLEEP, test, select, login, logout, users, visit
from conftest import config
from pytest import mark


users = config.users
reviewer = users.reviewer
recommender = users.recommender

from conftest import store as article


@test
class Reviewer_reviews:

    def login_as_reviewer(_):
        login(reviewer)

    def accept_to_review(_, article):
        Reviewer.accept_to_review(article)

    def confirm_requirements(_):
        Reviewer.confirm_requirements()

    def send_suggestions(_):
        Reviewer.send_suggestion()

    @mark.skipif(config.is_rr and config.is_rr.scheduled_track,
            reason="scheduled track")
    def upload_review(_, article):
        Reviewer.upload_review(article)

    def logout(_):
        logout(users.reviewer)


@test
class External_user_reviews:

    class user:
        name = "Titi"
        password = "password"

    def accept_email_invitation(_):
        login(users.manager)
        select(".dropdown-toggle span", "For managers").click()
        select(".dropdown-menu span", contains="Handling process(es) underway").click()
        select("tr", contains="HANDLING PROCESS UNDERWAY") \
                .select("a", "VIEW / EDIT").click()
        select("a", "View e-mails").click()
        select("tr", contains="#DefaultReviewInvitationNewUser") \
                .select("a", "VIEW").click()
        accept_link = select("a", contains="I accept to review this").get_attribute("href")
        logout(users.manager)
        visit(accept_link)


    def accept_invitation_to_review(_, article):
        article.title = select('.pci2-article-row-short h3 span').wait_clickable().text
        Reviewer.confirm_requirements(reviewer=_.user)

    def send_suggestions(_):
        Reviewer.send_suggestion()

    def first_time_login(_):
        password = _.user.password
        select("input[name=new_password]").send_keys(password)
        select("input[name=new_password2]").send_keys(password)
        select("input[type=submit]").click()


    @mark.skipif(config.is_rr and config.is_rr.scheduled_track,
            reason="scheduled track")
    def upload_review(_, article):
        Reviewer.upload_review(article, _.user)

    def logout(_):
        logout(_.user)


class Reviewer:

    def accept_to_review(article):
        select(".dropdown-toggle", contains="For contributors").click()
        select("a", contains="Invitation(s) to review a ").click()

        awaiting_cue = "AWAITING RESPONSE"
        row = select("tr", contains=awaiting_cue) # or article.title)
        article.title = row.select(".article-title").text

        row.select(".pci-status", awaiting_cue)
        row.select("a", "ACCEPT OR DECLINE").click()

        select("a", contains="I ACCEPT TO REVIEW THIS").click()

    def confirm_requirements(reviewer=reviewer):
        assert select("input[type=submit]").get_attribute("disabled")

        for cb in select("input[type=checkbox]"):
            cb.click()
        select("input[type=submit]").click()

        Reviewer.check_notification(reviewer)

    def upload_review(article, reviewer=reviewer):
        import time; time.sleep(DEFAULT_SLEEP)
        select("a", contains="WRITE, EDIT OR UPLOAD YOUR REVIEW").wait_clickable().click()

        with select("#t_reviews_review_ifr").frame():
            select("body").send_keys("review text: luved it")
        select("input[type=submit][name=terminate]").click()

        select("#confirm-dialog").wait_clickable().click()

        Reviewer.check_notification(reviewer)

        row = select("tr", contains=article.title)
        row.select(".pci-status", "REVIEW COMPLETED")
        row.select("a", "VIEW")

    def send_suggestion():
        select(css="#suggestion-textbox").send_keys(users.test.email)
        select(css="#suggestion-submission").wait_clickable().click()

    def check_notification(reviewer=reviewer):
        notif = select.notif()
        notif.contains("e-mail sent to " + reviewer.name)
        notif.contains("e-mail sent to " + recommender.name)


class User:
    def agree_to_comply():
        select("input#ethics_approved").click()
        select("input[type=submit]").click()
