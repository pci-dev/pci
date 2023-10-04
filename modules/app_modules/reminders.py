from typing import List, Optional
from gluon.contrib.appconfig import AppConfig
import datetime

from gluon.custom_import import track_changes
from models.review import Review
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

def avoid_weekend(nb_day: int, simple_avoid: bool):
    current_week_day =  datetime.datetime.now().weekday()
    planned_week_day = (current_week_day + nb_day) % 7

    if planned_week_day == 5:
            return nb_day + 2

    if simple_avoid:
        if planned_week_day == 6:
            return nb_day + 1
    else:
        if planned_week_day == 6:
            return nb_day + 2
        elif planned_week_day == 0:
            return nb_day + 2
        elif planned_week_day == 1:
            return nb_day + 1
        
    return nb_day


def avoid_weekend_for_reminder(days: List[int]):
    simple_avoid = True
    days_avoid_weekend: List[int] = []

    for i in range(len(days)):
        day = days[i]
        before_day: Optional[int] = None

        if i > 0:
            before_day = days[i - 1]

        if not before_day:
            simple_avoid = day >= 5
        else:
            simple_avoid = day - before_day >= 5
        
        day_avoid_weekend = avoid_weekend(day, simple_avoid)
        days_avoid_weekend.append(day_avoid_weekend)
    
    return days_avoid_weekend


_reminders = {
    "ReminderRecommenderReviewersNeeded": [1, 3, 5],
    "ReminderRecommenderNewReviewersNeeded": [7],
    "ReminderRecommenderDecisionSoonDue": [8],
    "ReminderRecommenderDecisionDue": [10],
    "ReminderRecommenderDecisionOverDue": [14, 18, 22],
    "ReminderRecommenderRevisedDecisionSoonDue": [7],
    "ReminderRecommenderRevisedDecisionDue": [10],
    "ReminderRecommenderRevisedDecisionOverDue": [14, 18, 22],

    "ReminderReviewerReviewInvitationNewUser": [2, 9],
    "ReminderReviewerReviewInvitationRegisteredUser": [2, 9],
    "ReminderReviewerInvitationNewRoundRegisteredUser": [2, 9],

    "ReminderReviewInvitationRegisteredUserNewReviewer": [2, 9],
    "ReminderReviewInvitationRegisteredUserReturningReviewer": [2, 9],

    "ReminderRecommenderAcceptationReview": [2, 9],

    "ReminderSubmitterCancelSubmission": [20],
    "ReminderSubmitterSuggestedRecommenderNeeded": daily(1, 9),
    "ReminderSubmitterNewSuggestedRecommenderNeeded": [10],
    "ReminderSubmitterRevisedVersionWarning": [7],
    "ReminderSubmitterRevisedVersionNeeded": [60, 90],

    "ReminderSuggestedRecommenderInvitation": [5, 9],
    "ReminderRecommender2ReviewsReceivedCouldMakeDecision": weekly(3, 15),

    "ManagersRecommenderAgreedAndNeedsToTakeAction": weekly(1, 15),
    "ManagersRecommenderReceivedAllReviewsNeedsToTakeAction": weekly(1, 15),
    "ManagersRecommenderReceivedRevisionNeedsToTakeAction": weekly(1, 15),
    "ManagersRecommenderNotEnoughReviewersNeedsToTakeAction": weekly(1, 15),
}

if pciRRactivated:
    _reminders[ "ReminderRecommenderReviewersNeeded"] = [7, 9, 11]

_review_reminders = {
    "ReminderReviewerReviewSoonDue":    "reminder_soon_due",
    "ReminderReviewerReviewDue":        "reminder_due",
    "ReminderReviewerReviewOverDue":    "reminder_over_due",
}


def getReviewReminders(days):
    reminder_due = [ days ]
    reminder_soon_due = [ days - 7 ]
    reminder_over_due = [ days + 5*x for x in range(1, 6) ]

    return reminder_soon_due, reminder_due, reminder_over_due


def getReminderValues(review: Review):
    days=Review.get_review_days_from_due_date(review)
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
        days = avoid_weekend_for_reminder(_reminders[hash_temp])
    else:
        return None

    return dict(hashtag="#"+hash_temp, elapsed_days=days)


# the reminders conf file is implicitly cached
# to reload: touch modules/app_modules/reminders.py
get_reminders_from_config()
