from conftest import config, select
from conftest import login, logout
from conftest import test
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
        select("a", "ACCEPT").click()

    def first_time_login(_):
        password = _.user.password
        select("input[name=new_password]").send_keys(password)
        select("input[name=new_password2]").send_keys(password)
        select("input[type=submit]").click()

    def accept_to_review(_, article):
        Reviewer.accept_to_review(article)
        User.agree_to_comply()

    def confirm_requirements(_):
        Reviewer.confirm_requirements(_.user)

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

        notif = select(".w2p_flash")
        notif.contains("e-mail sent to " + reviewer.name)
        notif.contains("e-mail sent to " + recommender.name)

    def upload_review(article, reviewer=reviewer):
        select("a", contains="WRITE, EDIT OR UPLOAD YOUR REVIEW").click()

        with select("#t_reviews_review_ifr").frame():
            select("body").send_keys("review text: luved it")
        select("input[type=submit][name=terminate]").click()

        notif = select(".w2p_flash")
        notif.contains("e-mail sent to " + reviewer.name)
        notif.contains("e-mail sent to " + recommender.name)

        row = select("tr", contains=article.title)
        row.select(".pci-status", "REVIEW COMPLETED")
        row.select("a", "VIEW / EDIT")


class User:
    def agree_to_comply():
        select("input#ethics_approved").click()
        select("input[type=submit]").click()
