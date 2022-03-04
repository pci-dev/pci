update_reminders_config() {
	diff -u private/reminders_config private/sample.reminders_config

	sed -i '/ReminderReviewerReview.*Due/ d' private/reminders_config
	touch modules/app_modules/reminders.py
}

set -x

update_reminders_config
