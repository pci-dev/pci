from conftest import test, select, login, logout, users


@test
class Author_submits_manuscript:

    def login_to_submitted(_):
        login(users.user)
        select(".dropdown-toggle span", "For contributors").click()
        select(".dropdown-menu span", contains="Your submitted ").click()
        select("tr", contains="HANDLING PROCESS UNDERWAY") \
                .select("a", "VIEW / EDIT").click()

    def check_edit_report_survey(_):
        select("a", "CHECK / EDIT REPORT SURVEY").click()
        report_type = "COMPLETE"
        select("#t_report_survey_q1").send_keys(report_type)
        select("input[type=submit]").click()

        select(".w2p_flash", contains="Report NOT yet submitted")

    def submit_full_manuscript(_):
        select("#t_articles_ms_version").send_keys("v1-final")
        select("input[type=submit]").click()
        select(".w2p_flash", "Report submitted successfully")
        select(".pci-status-big", "SCHEDULED SUBMISSION PENDING VALIDATION")

    def logout(_):
        logout(users.user)


@test
class Manager_non_recommender_cannot_validate:

    def login_to_pending_validation(_):
        login(users.manager)
        select(".dropdown-toggle span", "For managers").click()
        select(".dropdown-menu span", contains="Pending validation(s)").click()
        select("tr", contains="SCHEDULED SUBMISSION PENDING VALIDATION") \
                .select("a", "VIEW / EDIT").click()

    def assert_validates_not(_):
        select.fails("a", "VALIDATE THIS SCHEDULED SUBMISSION")
        logout(users.manager)


@test
class Recommender_validates:

    def login_to_pending_validation(_):
        login(users.recommender)
        select(".dropdown-toggle span", contains="For recommenders").click()
        select(".dropdown-menu span", contains="Pending validation(s)").click()
        select("tr", contains="SCHEDULED SUBMISSION PENDING VALIDATION") \
                .select("a", "VIEW / EDIT").click()

    def validate_submission(_):
        select("a", contains="VALIDATE THIS SCHEDULED SUBMISSION").click()
        select(".w2p_flash", "Request now available to recommenders")
        select(".pci-status-big", "SCHEDULED SUBMISSION UNDER CONSIDERATION")

    def open_submission_to_reviewers(_):
        select("a", contains="OPEN SUBMISSION TO REVIEWERS").click()
        select(".w2p_flash", "Submission now available to reviewers")
        select("a", contains="WRITE OR EDIT YOUR DECISION / RECOMMENDATION")

    def logout(_):
        logout(users.recommender)
