from gluon.contrib.appconfig import AppConfig

from gluon.custom_import import track_changes
track_changes(True)

def case_sensitive_config():
    from configparser import ConfigParser
    ConfigParser.optionxform = str

case_sensitive_config()
myconf = AppConfig(reload=True)
pciRRactivated = myconf.get("config.registered_reports", default=False)

def daily(start, end): return every(1, start, end)
def weekly(start, end): return every(7, start, end)
def every(days, start, end): return [days*x for x in range(start, end+1)]

_reminders = {
    "ReminderRecommenderReviewersNeeded": [1, 3, 5],
    "ReminderRecommenderNewReviewersNeeded": [7],
    "ReminderRecommenderDecisionSoonDue": [8],
    "ReminderRecommenderDecisionDue": [10],
    "ReminderRecommenderDecisionOverDue": [14, 18, 22],
    "ReminderRecommenderRevisedDecisionSoonDue": [7],
    "ReminderRecommenderRevisedDecisionDue": [10],
    "ReminderRecommenderRevisedDecisionOverDue": [14, 18, 22],

    "ReminderReviewerReviewInvitationNewUser": [5, 8],
    "ReminderReviewerReviewInvitationRegisteredUser": [5, 8],
    "ReminderReviewerInvitationNewRoundRegisteredUser": [5, 8],

    "ReminderSubmitterCancelSubmission": [20],
    "ReminderSubmitterSuggestedRecommenderNeeded": daily(1, 9),
    "ReminderSubmitterNewSuggestedRecommenderNeeded": [10],
    "ReminderSubmitterRevisedVersionWarning": [7],
    "ReminderSubmitterRevisedVersionNeeded": [60, 90],

    "ReminderSuggestedRecommenderInvitation": [5, 9],
    "ReminderRecommender2ReviewsReceivedCouldMakeDecision": weekly(3, 15),
}

if pciRRactivated:
    _reminders[ "ReminderRecommenderReviewersNeeded"] = [7, 9, 11]

_review_reminders = {
    "ReminderReviewerReviewSoonDue":    "reminder_soon_due",
    "ReminderReviewerReviewDue":        "reminder_due",
    "ReminderReviewerReviewOverDue":    "reminder_over_due",
}


def getDefaultReviewDuration():
    return "Two weeks" if pciRRactivated else "Three weeks"


def getReviewDays(review):
    if review:
        duration = review.review_duration
    else:
        duration = getDefaultReviewDuration()

    return getReviewDaysFromDuration(duration)


import datetime

def getReviewDaysFromDuration(duration):
    dow = datetime.datetime.today().weekday()
    duration = duration.lower()
    days_dict = {
            "two weeks": 14,
            "three weeks": 21,
            "four weeks": 28,
            "five weeks": 35,
            "six weeks": 42,
            "seven weeks": 49,
            "eight weeks": 56,
            "five working days": 7 if dow < 5 else (7 + (7-dow))
    }
    for key, value in days_dict.items():
        if key in duration:
            return value

    return 21


def getReviewReminders(days):
    reminder_due = [ days ]
    reminder_soon_due = [ days - 7 ]
    reminder_over_due = [ days + 5*x for x in range(1, 6) ]

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


def get_reminders_from_config():
    for hashtag, days_default in _reminders.items():
        days = myconf.get("reminders." + hashtag)
        if not days:
            continue
        if type(days) == int: days = [ days ]
        if type(days) == map: days = [ int(x) for x in days ]
        _reminders[hashtag] = days


def getReminder(db, hashtag_template, review_id):
    hash_temp = hashtag_template
    hash_temp = hash_temp.replace("#", "")
    hash_temp = hash_temp.replace("Stage1", "")
    hash_temp = hash_temp.replace("Stage2", "")
    hash_temp = hash_temp.replace("ScheduledSubmission", "")

    if hash_temp in _review_reminders:
        rev = db.t_reviews[review_id]
        reminder_values = getReminderValues(rev)
        days = reminder_values[_review_reminders[hash_temp]]

    elif hash_temp in _reminders:
        days = _reminders[hash_temp]
    else:
        return None

    return dict(hashtag="#"+hash_temp, elapsed_days=days)


# the reminders conf file is implicitly cached
# to reload: touch modules/app_modules/reminders.py
get_reminders_from_config()
