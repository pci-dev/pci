from gluon.contrib.appconfig import AppConfig

from gluon.custom_import import track_changes
track_changes(True)

myconf = AppConfig(reload=True)
pciRRactivated = myconf.get("config.registered_reports", default=False)

def getDefaultReviewDuration():
    return "Two weeks" if pciRRactivated else "Three weeks"


def getReviewDays(review):
    if review:
        duration = review.review_duration
    else:
        duration = getDefaultReviewDuration()

    return getReviewDaysFromDuration(duration)


def getReviewDaysFromDuration(duration):
    duration = duration.lower()
    days_dict = {
            "two weeks": 14,
            "three weeks": 21,
            "four weeks": 28,
            "five weeks": 35,
            "six weeks": 42,
            "seven weeks": 49,
            "eight weeks": 56,
    }
    for key, value in days_dict.items():
        if key in duration:
            return value
    return 21


def getReviewReminders(days):
    count = 0
    reminder_soon_due = []
    reminder_due = []
    reminder_over_due = []
    reminder_soon_due.extend([days-7, days-2])
    reminder_due.append(days)
    while count < 5:
        days+=4
        reminder_over_due.append(days)
        count+= 1
    return reminder_soon_due, reminder_due, reminder_over_due


def getReminderValues(review):
    days=getReviewDays(review)
    reminder_soon_due, reminder_due, reminder_over_due = getReviewReminders(days)
    reminder_values = {
        "reminder_soon_due" : reminder_soon_due,
        "reminder_due": reminder_due,
        "reminder_over_due": reminder_over_due
    }
    return reminder_values


import os
def get_reminders_from_config():
    reminders = []
    with open(os.path.join(os.path.dirname(__file__), "../../private", "reminders_config")) as f:
        # Remove empty lines
        non_empty_lines = [lin for lin in f if lin.strip() != ""]

        # Parse lines
        for line in non_empty_lines:
            # Remove whitechar
            line = line.strip()
            line = line.replace(" ", "")
            element = line.split("=")

            # Get hashtag_template
            hashtag = element[0]

            # Get elapsed_days
            # Remove array notation
            elapsed_days_str = element[1].replace("[", "")
            elapsed_days_str = elapsed_days_str.replace("]", "")
            elapsed_days_str = elapsed_days_str.split(",")

            # Convert elapsed_days from str to int
            elapsed_days_int = []
            for i in elapsed_days_str:
                elapsed_days_int.append(int(i))

            # Append item
            reminders.append(dict(hashtag=hashtag, elapsed_days=elapsed_days_int))

    return reminders


def getReminder(db, hashtag_template, review_id):
    REVIEW_REMINDERS = []
    field_hashtag = {
        "reminder_soon_due" : "#ReminderReviewerReviewSoonDue",
        "reminder_due": "#ReminderReviewerReviewDue",
        "reminder_over_due": "#ReminderReviewerReviewOverDue"
    }
    hash_temp = hashtag_template
    hash_temp = hash_temp.replace("Stage1", "")
    hash_temp = hash_temp.replace("Stage2", "")
    hash_temp = hash_temp.replace("ScheduledSubmission", "")

    if hash_temp in field_hashtag.values():
        rev = db.t_reviews[review_id]
        reminder_values = getReminderValues(rev)
        for key, value in field_hashtag.items():
            REVIEW_REMINDERS.append(dict(hashtag=value, elapsed_days=reminder_values[key]))
        reminder = list(filter(lambda item: item["hashtag"] == hash_temp, REVIEW_REMINDERS))
    else:
        reminder = list(filter(lambda item: item["hashtag"] == hash_temp, REMINDERS))

    return reminder


# the reminders conf file is implicitly cached
# to reload: touch modules/app_modules/reminders.py
REMINDERS = get_reminders_from_config()
