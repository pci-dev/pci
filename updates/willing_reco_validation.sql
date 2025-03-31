INSERT INTO public.mail_templates (hashtag,lang,subject,description,contents) VALUES
	 ('#WillingRecommenderValidation','default','{{appName}}: New willing recommender pending validation','New willing recommender pending validation','<div>Dear members of the Managing Board,</div>
<div>&nbsp;</div>
<div><span class="HwtZe" lang="en"><span class="jCAhz ChMk0b"><span class="ryNqvb">Recommender <strong>{{recommenderPerson}}</strong> is willing to become the recommender in charge of the preprint entitled <strong>{{articleTitle}}</strong> - via the "<strong>Preprints in need of a recommender</strong>" page.</span></span></span></div>
<div>&nbsp;</div>
<div>If you want them to handle the preprint, you must accept the suggestion so that they will receive an invitation email.</div>
<div>&nbsp;</div>
<div><span class="HwtZe" lang="en"><span class="jCAhz ChMk0b">Please follow this link <a href="{{linkTarget}}">{{linkTarget}}</a> to accept or decline this suggestion.<br></span></span></div>
<div>&nbsp;</div>
<div><span class="HwtZe" lang="en"><span class="jCAhz ChMk0b">Thanks in advance.</span></span></div>
<div><span class="HwtZe" lang="en"><span class="jCAhz ChMk0b"><br>Have a nice day!</span></span></div>');

ALTER TABLE t_suggested_recommenders drop column if exists willing;
ALTER TABLE t_suggested_recommenders ADD column IF NOT EXISTS suggested_by varchar(50) DEFAULT NULL;

delete from mail_templates where hashtag = '#RecommenderSuggestedArticle';
INSERT INTO public.mail_templates (hashtag,lang,subject,description,contents) VALUES
	 ('#RecommenderSuggestedArticle','default','{{appName}}: Request to act as a recommender for a preprint','Mail to suggested recommenders to ask them to act as recommender of a submitted preprint','<p>Dear {{destPerson}},</p>
<p>You are invited to act as a recommender for the preprint entitled <strong>{{articleTitle}}</strong> by {{articleAuthors}} (<a href="{{articleDoi}}">{{articleDoi}}</a>).</p>
<p><strong>Very important: </strong></p>
<p><strong>You should agree to become the recommender for this preprint only if, after reading it, you think that it is interesting and merits evaluation</strong> (relevant research question, quality of the methods/data/analysis, etc.).</p>
<p>You can obtain information about this request and accept or decline this invitation by following this link&nbsp;<a href="{{linkTarget}}">{{linkTarget}}</a>&nbsp;or by logging on to the {{appName}} website and going to ''For recommenders —&gt; Request(s) to handle a preprint'' in the tool bar.</p>
<p>This article is considered to lie within the scope of the PCI, but there has been no scientific filtering by the managing board. The article may, therefore, be of poor scientific quality and, if this is the case, it would be better to reject it directly, without peer review. So, <strong>if you feel that this preprint is of insufficient quality, please decline this request to handle it.</strong></p>
<p><strong>Important information before you agree to become the recommender for this preprint:</strong>&nbsp;</p>
<p>The role of a recommender is very similar to that of a journal editor (finding reviewers, collecting reviews, taking editorial decisions based on reviews). The decision to ‘Revise’, ‘Recommend’ or ‘Reject’ the preprint is based on the recommender’s evaluation. A preprint recommended by {{appName}} is an article that may be used and cited like the ‘classic’ articles published in peer-reviewed journals. Recommended preprints are valid, citable and final articles. The normal outcome is therefore to leave them on preprint servers or open repositories. However, the authors of a PCI-recommended article may prefer:</p>
<ul>
<li>To publish their article in the Peer Community journal as is, immediately and at no cost</li>
<li>To submit it to a PCI-friendly journal (acceptance with no further peer review OR response within 5 days OR use of the PCI evaluation if appropriate).</li>
<li>To submit it to another journal.</li>
</ul>
<p>Details about the recommendation process can be found&nbsp;<a href="https://pci_adminmunityin.org/2020/10/28/pci-recommender-guide/">here</a>.</p>
<p>By agreeing to become the recommender for this preprint, you agree to do your best to handle the peer-review process within as short a time period as possible for the authors. Indeed, this rapid turnaround time is a key factor for the success of PCI as a credible alternative to journals.</p>
<p>To this end, we need you:</p>
<p>1-&nbsp;<strong>To send invitations to 5-10 potential reviewers within 24 hours of agreeing to become the recommender for this preprint</strong><strong> </strong>and to continue sending out new invitations until you find at least two reviewers willing to review the preprint. Sending multiple invitations increases the chances of finding available reviewers and keeping turnaround times short. You may, of course, use whichever strategy you prefer to invite reviewers. The key thing is avoiding situations in which only a couple of invitations have been sent out in 20 days, with only one reply after 30 days.<br>2-&nbsp;<strong>To post your decision,</strong>&nbsp;ideally <strong>within 10 days</strong>&nbsp;of receiving the reviews. <br>3-&nbsp;<strong>To write a recommendation text </strong><strong>(i.e. a text of 300 to 1,500 words describing the context and explaining why</strong> the preprint is particularly interesting)&nbsp;if you decide to recommend this preprint for {{appName}} at the end of the evaluation process, and to submit it as soon as possible after deciding to recommend the article.<br>4-&nbsp;<strong>To declare that you have no conflict of interest with the authors or the content of the article.</strong>&nbsp; See the <a href="https://pci_adminmunityin.org/">code of conduct</a>.</p>
<p>Details about the recommendation process can be found <a href="https://pci_adminmunityin.org/2020/10/28/pci-recommender-guide/">here</a>.</p>
<p>Thank you for your help.</p>
<p>Yours sincerely,</p>
<p>The Managing Board of {{appName}}</p>');
