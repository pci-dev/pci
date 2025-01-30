from typing import Iterable, List, Optional, Union
from gluon.contrib.appconfig import AppConfig # type: ignore
from models.review import Review, ReviewDuration
import datetime

from gluon.custom_import import track_changes
from models.review import Review
track_changes(True)

def case_sensitive_config():
    from configparser import ConfigParser
    ConfigParser.optionxform = str # type: ignore

case_sensitive_config()
myconf = AppConfig(reload=True)
pciRRactivated = myconf.get("config.registered_reports", default=False)

def daily(start: int, end: int): return every(1, start, end)
def weekly(start: int, end: int): return every(7, start, end)
def every(days: int, start: int, end: int): return [days*x for x in range(start, end+1)]

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
    "ReminderUserCompleteSubmission": [2, 10],
    "ReminderUserCompleteSubmissionCOAR": [2, 7],
    "ReminderUserCompleteSubmissionBiorxiv": [2, 7],

    "ReminderSuggestedRecommenderInvitation": [5, 9],
    "ReminderRecommender2ReviewsReceivedCouldMakeDecision": weekly(3, 15),

    "ManagersRecommenderAgreedAndNeedsToTakeAction": weekly(1, 15),
    "ManagersRecommenderReceivedAllReviewsNeedsToTakeAction": weekly(1, 15),
    "ManagersRecommenderReceivedRevisionNeedsToTakeAction": weekly(1, 15),
    "ManagersRecommenderNotEnoughReviewersNeedsToTakeAction": weekly(1, 15),

    "ReminderRevisionsRequiredToYourSubmission": [2, 10],
}

if pciRRactivated:
    _reminders[ "ReminderRecommenderReviewersNeeded"] = [7, 9, 11]

_review_reminders = {
    "ReminderReviewerReviewSoonDue":    "reminder_soon_due",
    "ReminderReviewerReviewDue":        "reminder_due",
    "ReminderReviewerReviewOverDue":    "reminder_over_due",
}

_avoid_weekend_reminders_RR = [
    'ReminderReviewerReviewInvitationNewUser',
    'ReminderReviewerReviewInvitationRegisteredUser',
    'ReminderReviewerInvitationNewRoundRegisteredUser',
    'ReminderReviewInvitationRegisteredUserNewReviewer',
    'ReminderReviewInvitationRegisteredUserReturningReviewer',
    'ReminderRecommenderAcceptationReview'
]


def getReviewDaysFromDuration(duration: str):
    dow = datetime.datetime.today().weekday()
    days_dict = {
            ReviewDuration.TWO_WEEK.value: 14,
            ReviewDuration.THREE_WEEK.value: 21,
            ReviewDuration.FOUR_WEEK.value: 28,
            ReviewDuration.FIVE_WEEK.value: 35,
            ReviewDuration.SIX_WEEK.value: 42,
            ReviewDuration.SEVEN_WEEK.value: 49,
            ReviewDuration.EIGHT_WEEK.value: 56,
            ReviewDuration.FIVE_WORKING_DAY.value: 7 if dow < 5 else (7 + (7-dow))
    }
    for key, value in days_dict.items():
        if key in duration:
            return value

    return 21


def getReviewReminders(days: int):
    reminder_due = [ days ]
    reminder_soon_due = [ days - 7 ]
    reminder_over_due = [ days + 5*x for x in range(1, 6) ]

    return reminder_soon_due, reminder_due, reminder_over_due


def getReminderValues(review: Review):
    days = Review.get_review_days_from_due_date(review)
    reminder_soon_due, reminder_due, reminder_over_due = getReviewReminders(days)
    reminder_values = {
        "reminder_soon_due" : reminder_soon_due,
        "reminder_due": reminder_due,
        "reminder_over_due": reminder_over_due
    }
    return reminder_values


def get_reminders_from_config():
    for hashtag in _reminders.keys():
        days: Optional[Union[Iterable[int], int]] = myconf.get("reminders." + hashtag)
        reminder_days: List[int] = []
        if not days:
            continue
        if type(days) == int: reminder_days = [ days ]
        if type(days) == map: reminder_days = [ int(x) for x in days ]
        _reminders[hashtag] = reminder_days


def getReminder(hashtag_template: str, review: Review):
    hash_temp = get_hashtag_corresponding_in_configured_reminders(hashtag_template)

    if hash_temp in _review_reminders:
        if review:
            reminder_values = getReminderValues(review)
            days = reminder_values[_review_reminders[hash_temp]]
        else:
            return None
    elif hash_temp in _reminders:
        days = _reminders[hash_temp]

        if pciRRactivated and hash_temp in _avoid_weekend_reminders_RR:
            days[0] = avoid_weekend(days[0], False)
    else:
        return None

    if not pciRRactivated:
        days = avoid_weekend_for_reminder(days)

    return dict(hashtag="#"+hash_temp, elapsed_days=days)


def get_hashtag_corresponding_in_configured_reminders(hashtag_template: str):
    hash_temp = hashtag_template
    hash_temp = hash_temp.replace("#", "")

    suffix = ["", "Stage1", "Stage2", "ScheduledSubmission", "COAR", "Biorxiv"]
    for s in suffix:
        hash_temp = hash_temp.replace(s, "")

        if hash_temp in _review_reminders:
            return hash_temp
    
        if hash_temp in _reminders:
            return hash_temp
        
    return hash_temp


# the reminders conf file is implicitly cached
# to reload: touch modules/app_modules/reminders.py
get_reminders_from_config()
