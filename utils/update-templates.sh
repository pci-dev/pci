#/bin/bash

DB=$1
TARGET=${2:-prod}

declare -A target=(
	[test]="psql -U postgres"
	[prod]="psql -U peercom -h mydb1 -p 33648"
)

main() {
	parse_args
	#list_templates
	#copy_templates
	insert_templates
}

parse_args() {
	PSQL=${target[$TARGET]}

	[ "$DB" ] && [ "$PSQL" ] || {
		echo "usage: $0 <pci_db> <test|prod>"
		exit 1
	}
}

copy_templates() {
	$PSQL $DB << EOT
	drop table if exists tmp_copy_templates;
	create table tmp_copy_templates as
	select * from mail_templates
	where hashtag in ( $(list_templates) );
EOT
}

insert_templates() {
	$PSQL $DB << EOT
	insert into mail_templates
		(hashtag, lang, subject, description, contents)
	select   hashtag, lang, subject, description, contents
	from tmp_copy_templates;
EOT
}


list_templates() {
	echo "'$(xargs | sed "s/ /', '/g")'"
} << EOT
#AdminArticleResubmitedStage1ScheduledSubmission
#AdminTwoReviewersInStage1ScheduledSubmission
#DefaultReviewAlreadyAcceptedCancellationStage1ScheduledSubmission
#DefaultReviewCancellationStage1ScheduledSubmission
#DefaultReviewInvitationNewUserStage1ScheduledSubmission
#DefaultReviewInvitationRegisteredUserStage1ScheduledSubmission
#ManagersArticleCancelledStage1ScheduledSubmission
#ManagersArticleConsideredForRecommendationStage1ScheduledSubmission
#ManagersArticleStatusChangedStage1ScheduledSubmission
#ManagersFullPreprintStage1ScheduledSubmission
#ManagersPreprintSubmissionStage1ScheduledSubmission
#ManagersRecommendationOrDecisionStage1ScheduledSubmission
#RecommenderArticleStatusChangedStage1ScheduledSubmission
#RecommenderPreprintSubmittedScheduledSubmission
#RecommenderReviewConsideredStage1ScheduledSubmission
#RecommenderReviewDeclinedStage1ScheduledSubmission
#RecommenderStatusChangedToUnderConsiderationStage1ScheduledSubmission
#RecommenderSuggestedArticleStage1ScheduledSubmission
#RecommenderSuggestedReviewersStage1ScheduledSubmission
#RecommenderSuggestionNotNeededAnymoreStage1ScheduledSubmission
#RecommenderThankForPreprintStage1ScheduledSubmission
#ReminderRecommenderNewReviewersNeededStage1ScheduledSubmission
#ReminderRecommenderReviewersNeededStage1ScheduledSubmission
#ReminderRecommenderRevisedDecisionDueStage1ScheduledSubmission
#ReminderRecommenderRevisedDecisionOverDueStage1ScheduledSubmission
#ReminderRecommenderRevisedDecisionSoonDueStage1ScheduledSubmission
#ReminderReviewerReviewInvitationNewUserStage1ScheduledSubmission
#ReminderReviewerReviewInvitationRegisteredUserStage1ScheduledSubmission
#ReminderScheduledReviewComingSoon
#ReminderSubmitterNewSuggestedRecommenderNeededStage1ScheduledSubmission
#ReminderSubmitterRevisedVersionNeededStage1ScheduledSubmission
#ReminderSubmitterRevisedVersionWarningStage1ScheduledSubmission
#ReminderSubmitterScheduledSubmissionDue
#ReminderSubmitterScheduledSubmissionOverDue
#ReminderSubmitterScheduledSubmissionSoonDue
#ReminderSubmitterSuggestedRecommenderNeededStage1ScheduledSubmission
#ReminderSuggestedRecommenderInvitationStage1ScheduledSubmission
#ReviewerFullPreprintStage1ScheduledSubmission
#ReviewersArticleCancellationStage1ScheduledSubmission
#ReviewerScheduledReviewCancelled
#ReviewerThankForReviewAcceptationStage1ScheduledSubmission
#SubmitterAcknowledgementFullPreprintStage1ScheduledSubmission
#SubmitterAcknowledgementSubmissionStage1ScheduledSubmission
#SubmitterAwaitingSubmissionStage1ScheduledSubmission
#SubmitterCancelledSubmissionStage1ScheduledSubmission
#SubmitterPreprintSubmittedStage1ScheduledSubmission
#SubmitterPreprintUnderConsiderationStage1ScheduledSubmission
#SubmitterScheduledSubmissionOpen
EOT

main "$@"
