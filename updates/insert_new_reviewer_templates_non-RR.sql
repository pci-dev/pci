INSERT INTO "mail_templates"("hashtag","lang","subject","description","contents")
VALUES
(
E'#DefaultReviewInvitationNewRoundNewReviewerNewUser',
E'default',
E'{{appName}}: Invitation from {{senderName}} to review a manuscript',
E'Mail to user not yet registered to indicate them that they are invited to review a preprint',
E'<p>Dear Dr. {{LastName}},</p><p>This is an invitation to review for <a href="https://peercommunityin.org/">Peer Community In</a> (PCI), a non-profit, non-commercial initiative, bolstered by the support of more than <a href="https://peercommunityin.org/pci-network/">150 respected research organizations from over 20 countries</a>.</p><p>A manuscript, titled “{{art_title}}” by {{authors}}, has been submitted to {{longname}} and is available here: <a href="{{art_doi}}">{{art_doi}}</a>.</p><p><strong>One or several previous versions of this preprint have already been evaluated and appeared interesting</strong>. To strengthen the evaluation process, I would like to have your expert opinion on it. Would you agree to review it, possibly within {{reviewDuration}}? Extensions are possible if required, but please let us know if you need one.</p><p>If you accept the invitation, you can choose to sign your review or remain anonymous.</p><p>Should the manuscript be accepted, your review will be published by {{longname}}, and I will write a short text explaining the article’s quality. If the manuscript is rejected, reviews are simply conveyed to the authors.</p><p>Once accepted, the authors can then leave it on the preprint server as a PCI-recommended preprint. They can also decide to publish it directly in the <a href="https://peercommunityjournal.org">Peer Community Journal</a> (Diamond Open Access) or submit it for publication to one of the <a href="https://peercommunityin.org/pci-friendly-journals/">PCI-friendly journals</a>.</p><p>Importantly, you should not accept this invitation if you have any conflict of interest with the authors (i.e., if you were part of the same research team, regularly co-published, or shared joint funding during the last four years).</p><p>Note that your login to {{longname}} is the email address that we used to contact you.</p><p>It’s possible that reviewing for PCI might not align with your current priorities or time constraints. Should this be the case, please rest assured that I fully comprehend your choice.</p><p>Thank you in advance for your help.</p><p>Best wishes,</p><p>{{sender}}, {{Institution}}, {{country}}</p>'
);

INSERT INTO "mail_templates"("hashtag","lang","subject","description","contents")
VALUES
( 
E'#DefaultReviewInvitationNewRoundNewReviewerRegisteredUser',
E'default',
E'{{appName}}: Invitation from {{senderName}} to review a manuscript',
E'Mail to registered user to invite them as new reviewer to make a new round of review of a preprint',
E'<p>Dear Dr. {{LastName}},</p><p>This is an invitation to review for <a href="https://peercommunityin.org/">Peer Community In</a> (PCI), a non-profit, non-commercial initiative, bolstered by the support of more than <a href="https://peercommunityin.org/pci-network/">150 respected research organizations from over 20 countries</a>.</p><p>A manuscript, titled “{{art_title}}” by {{authors}}, has been submitted to {{longname}} and is available here: <a href="{{art_doi}}">{{art_doi}}</a>.</p><p><strong>One or several previous versions of this preprint have already been evaluated and appeared interesting</strong>. To strengthen the evaluation process, I would like to have your expert opinion on it. Would you agree to review it, possibly within {{reviewDuration}}? Extensions are possible if required, but please let us know if you need one.</p><p>If you accept the invitation, you can choose to sign your review or remain anonymous.</p><p>Should the manuscript be accepted, your review will be published by {{longname}}, and I will write a short text explaining the article’s quality. If the manuscript is rejected, reviews are simply conveyed to the authors.</p><p>Once accepted, the authors can then leave it on the preprint server as a PCI-recommended preprint. They can also decide to publish it directly in the <a href="https://peercommunityjournal.org"> Peer Community Journal</a> (Diamond Open Access) or submit it for publication to one of the <a href="https://peercommunityin.org/pci-friendly-journals/">PCI-friendly journals</a>.</p><p>Importantly, you should not accept this invitation if you have any conflict of interest with the authors (i.e., if you were part of the same research team, regularly co-published, or shared joint funding during the last four years).</p><p>Note that your login to {{longname}} is the email address that we used to contact you.</p><p>It’s possible that reviewing for PCI might not align with your current priorities or time constraints. Should this be the case, please rest assured that I fully comprehend your choice.</p><p>Thank you in advance for your help.</p><p>Best wishes,</p><p>{{sender}}, {{Institution}}, {{country}}</p>'
);