from conftest import test, select, login, logout, users
from conftest import config

users = config.users
manager = users.manager
recommender = users.recommender

is_rr = config.is_rr
preprint = "preprint" if not is_rr else "report"

@test
class Recommender_makes_decision:

 def login_as_recommender(_):
    login(recommender)

 def write_recommendation(_):
    select(".dropdown-toggle", contains="For recommenders").click()
    select("a", f"{preprint.capitalize()}(s) you are handling").click()

    row = select("tr", contains="HANDLING PROCESS UNDERWAY")
    row.select(".btn", contains="Write or Edit".upper()).click()

    select("#opinion_recommend").click()
    select("#t_recommendations_recommendation_title").send_keys("Recommendation")
    with select("#t_recommendations_recommendation_comments_ifr").frame():
        select("body").send_keys("Recommendation")
    select("input[type=submit]")[1].click()
    select('#confirm-change-modal .btn-info', 'Yes'.upper()).click()
    notif = select.notif()
    notif.contains("Recommendation saved and completed")

 def logout_recommender(_):
    logout(recommender)

@test
class Manager_validates_decision:

 def login_as_manager(_):
   login(manager)

 def validate_decision(_):
    select(".dropdown-toggle span", "For managers").click()
    select(".dropdown-menu span", contains="Pending validation").click()
    select(".pci-status", "RECOMMENDATION PENDING VALIDATION")

    select("a", "View / Edit".upper()).click()

    if not is_rr:
        select("#title_present").click()
        select("#recommendation_explains").click()
        select("#recommendation_cites").click()
        select("#format_ok").click()

    select("#do_recommend_article").click()
    select('#confirm-change-modal .btn-info', 'Yes'.upper()).click()

    select('.pci-status-big', 'Recommended'.upper())

 def logout_manager(_):
    logout(manager)

