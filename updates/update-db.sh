#!/bin/bash

DB=$1

[ "$DB" ] || { echo "usage: $(basename "$0") <database>"; exit 1; }

# all_pci=$(grep psyco /var/www/peercommunityin/web2py/applications/PCI*/private/appconfig.ini | sed s:.*/::)


update() {
psql -h mydb1 -p 33648 -U peercom $DB << EOF

-- 06/09/2021
\set TEMPLATE_TEXT '<p>Dear {{destPerson}},</p>\n<p>The reviewer that just declined your invitation to review the preprint entitled <strong>{{articleTitle}}</strong> suggests the following reviewers:</p>\n<p>{{suggestedReviewersText}}</p>\n<p>You can invite these reviewers by following this link <a href="{{linkTarget}}">{{linkTarget}}</a> or by logging onto the {{appName}} website and going to \'For recommenders —&gt; Preprint(s) you are handling’ in the top menu.</p>\n<p>We thank you again for managing this evaluation.</p>\n<p>All the best,<br>The Managing Board of {{appName}}</p>'
\set DESCRIPTION 'Mail to recommender to notify reviewer declined invitation and suggests alternative reviewers'
\set SUBJECT '{{appName}}: suggested reviewers'

-- For other PCis
INSERT INTO "public"."mail_templates"("hashtag","lang","subject","description","contents")
VALUES
(E'#RecommenderSuggestedReviewers',E'default',:'SUBJECT',:'DESCRIPTION',:'TEMPLATE_TEXT');
EOF
}

update_rr() {
psql -h mydb1 -p 33648 -U peercom $DB << EOF

-- 06/09/2021
\set TEMPLATE_TEXT '<p>Dear {{destPerson}},</p>\n<p>The reviewer that just declined your invitation to review the report entitled <strong>{{articleTitle}}</strong> suggests the following reviewers:</p>\n<p>{{suggestedReviewersText}}</p>\n<p>You can invite these reviewers by following this link <a href="{{linkTarget}}">{{linkTarget}}</a> or by logging onto the {{appName}} website and going to \'For recommenders —&gt; Report(s) you are handling’ in the top menu.</p>\n<p>We thank you again for managing this evaluation.</p>\n<p>All the best,<br>The Managing Board of {{appName}}</p>'
\set DESCRIPTION 'Mail to recommender to notify reviewer declined invitation and suggests alternative reviewers'
\set SUBJECT '{{appName}}: suggested reviewers'

-- For PCi RR
-- note: replace preprint(s) with reports for RR

INSERT INTO "public"."mail_templates"("hashtag","lang","subject","description","contents")
VALUES
(E'#RecommenderSuggestedReviewersStage1',E'default',:'SUBJECT',:'DESCRIPTION',:'TEMPLATE_TEXT'),
(E'#RecommenderSuggestedReviewersStage2',E'default',:'SUBJECT',:'DESCRIPTION',:'TEMPLATE_TEXT'),
(E'#RecommenderSuggestedReviewersStage1ScheduledSubmission',E'default',:'SUBJECT',:'DESCRIPTION',:'TEMPLATE_TEXT'),
(E'#RecommenderSuggestedReviewersStage2ScheduledSubmission',E'default',:'SUBJECT',:'DESCRIPTION',:'TEMPLATE_TEXT');
EOF
}

#update_rr
update
