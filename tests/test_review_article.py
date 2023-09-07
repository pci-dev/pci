from conftest import test, select, login, logout, users, visit
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
        logout(reviewer)


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
        accept_link = select("a", "ACCEPT").get_attribute("href")
        logout(users.manager)
        visit(accept_link)


    def accept_invitation_to_review(_, article):
        article.title = select('.pci2-article-row-short h3').text
        select('#no_conflict_of_interest').click()
        select('#due_time').click()
        select('#anonymous_agreement').click()
        select('#cgu-checkbox').click()
        select("input[type=submit]").click()

    def first_time_login(_):
        password = _.user.password
        select("input[name=new_password]").send_keys(password)
        select("input[name=new_password2]").send_keys(password)
        select("input[type=submit]").click()

    def send_suggestions(_):
        Reviewer.send_suggestion()

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

        select("a", contains="YES, I WOULD LIKE TO REVIEW").click()

    def confirm_requirements(reviewer=reviewer):
        assert select("input[type=submit]").get_attribute("disabled")

        for cb in select("input[type=checkbox]"):
            cb.click()
        select("input[type=submit]").click()

        notif = select.notif()
        notif.contains("e-mail sent to " + reviewer.name)
        notif.contains("e-mail sent to " + recommender.name)

    def upload_review(article, reviewer=reviewer):
        select("a", contains="WRITE, EDIT OR UPLOAD YOUR REVIEW").click()

        with select("#t_reviews_review_ifr").frame():
            select("body").send_keys("review text: luved it")
        select("input[type=submit][name=terminate]").click()

        select("#confirm-dialog").wait_clickable().click()

        notif = select.notif()
        notif.contains("e-mail sent to " + reviewer.name)
        notif.contains("e-mail sent to " + recommender.name)

        row = select("tr", contains=article.title)
        row.select(".pci-status", "REVIEW COMPLETED")
        row.select("a", "VIEW")

    def send_suggestion():
        select(css="#suggestion-textbox").send_keys(users.test.email)
        select(css="#suggestion-submission").wait_clickable().click()


class User:
    def agree_to_comply():
        select("input#ethics_approved").click()
        select("input[type=submit]").click()
