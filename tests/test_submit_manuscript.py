from conftest import test, select, login, logout, users


@test
class Author_submits_manuscript:

    def check_full_submission_not_yet_opened(_):
        _.login_to_submitted()
        select.fails("a", "CHECK / EDIT REPORT SURVEY")
        logout(users.user)

    def move_future_date_now(_):
        Cheat.set_report_due_date_this_week()

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

        select.notif(contains="Report NOT yet submitted")

    def submit_full_manuscript(_):
        select("#t_articles_ms_version").send_keys("v1-final")
        select("input[type=submit]").click()
        select.notif("Report submitted successfully")
        select(".pci-status-big", "SCHEDULED SUBMISSION PENDING VALIDATION")

    def logout(_):
        logout(users.user)

    def move_future_date_back(_):
        Cheat.reset_report_due_date()


@test
class Manager_non_recommender_cannot_validate:

    def login_to_pending_validation(_):
        login(users.manager)
        select(".dropdown-toggle span", "For managers").click()
        select.fails(".dropdown-menu span", contains="Pending validation(s)")
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
        select.notif("Submission validated")
        select(".pci-status-big", "SCHEDULED SUBMISSION UNDER CONSIDERATION")

    def open_submission_to_reviewers(_):
        select("a", contains="OPEN SUBMISSION TO REVIEWERS").click()
        select.notif("Submission now available to reviewers")
        select("a", contains="WRITE OR EDIT YOUR DECISION / RECOMMENDATION")

    def logout(_):
        logout(users.recommender)


class Cheat:

    def set_report_due_date_this_week():
        login(users.manager)
        manager_edit_report_survey("For managers", "Handling process(es) underway")
        set_report_due_date(weeks=1)
        save_report_survey()
        logout(users.manager)

    def reset_report_due_date():
        login(users.recommender)
        manager_edit_report_survey("For recommenders", "Pending validation(s)")
        select("#t_report_survey_q1").send_keys("RR SNAPSHOT")
        set_report_due_date(weeks=7)
        select("#t_report_survey_q1").send_keys("COMPLETE")
        save_report_survey()
        logout(users.recommender)

def manager_edit_report_survey(user_menu, menu_entry):
        select(".dropdown-toggle span", contains=user_menu).click()
        select(".dropdown-menu span", contains=menu_entry).click()
        status = "HANDLING PROCESS UNDERWAY" if "underway" in menu_entry \
                    else "PENDING VALIDATION"
        select("tr", contains=status).select("a", "VIEW / EDIT").click()
        select("a", "Edit report survey").click()

def save_report_survey():
        select("input[type=submit]").click()
        select.notif(contains="Survey saved")

def set_report_due_date(weeks):
        from datetime import datetime, timedelta
        report_due_date = datetime.now() + timedelta(weeks=weeks)
        report_due_date -= timedelta(days=report_due_date.weekday())
        date = select("#t_report_survey_q10")
        date.clear()
        date.send_keys(report_due_date.strftime("%Y-%m-%d"))
