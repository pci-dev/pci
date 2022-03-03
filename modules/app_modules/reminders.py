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
