update help_texts set contents = '
<p>All preprints must be reviewed by at least two referees. To find reviewers we advise you to invite between 5 and 10 putative reviewers (you could then cancel some of your invitations when you have the desired number of active reviewers). You can invite:</p>
<p>1. any recommender or scientist who are already registered at {{appname}}</p>
<p>2. any other scientist, provided you have their email address: click ''Invite new reviewer'' in the search page.</p>
<p>When inviting referees for a preprint, keep in mind that a large gender, career stage and geographic diversity is desirable.</p>
<p>In case of any problems or difficulties, please contact us at <a href="mailto:{{contact}}">{{contact}}</a></p>
' where hashtag = '#RecommenderAddReviewersText';
