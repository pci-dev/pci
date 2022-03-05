update_reminders_config() {
	diff -u private/appconfig.ini private/sample.appconfig

	sed -i '/ReminderReviewerReview.*Due/ d' private/appconfig.ini
	touch modules/app_modules/reminders.py
}

set -x

update_reminders_config
