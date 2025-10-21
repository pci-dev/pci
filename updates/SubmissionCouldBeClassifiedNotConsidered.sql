INSERT INTO
    public.mail_templates (hashtag, lang, subject, description, contents)
VALUES
    (
        '#SubmissionCouldBeClassifiedNotConsidered',
        'default',
        '{{appName}}: Action Required - Cancel or find recommender for preprint {{articleTitle}}',
        'Mail to the managing board to let them know that a preprint is awaiting for a recommender for more than 20 days and that they can classify it as not considered.',
        '<p data-prosemirror-content-type="node" data-prosemirror-node-name="paragraph" data-prosemirror-node-block="true" data-pm-slice="1 1 []">Dear Members of the Managing Board,</p>
<p data-prosemirror-content-type="node" data-prosemirror-node-name="paragraph" data-prosemirror-node-block="true">None of the suggested recommenders has agreed to handle this submission. Submitting to a PCI does not guarantee evaluation: <strong data-prosemirror-content-type="mark" data-prosemirror-mark-name="strong">only preprints that recommenders volunteer to handle because they are genuinely interested in the content should be evaluated</strong> (it is better to cancel the article rather than to find a recommender who volunteers only to support PCI, and not out of academic interest). Therefore, <strong data-prosemirror-content-type="mark" data-prosemirror-mark-name="strong">you would normally now cancel this article</strong> by classifying it as “Not considered” using the Action button in your PCI dashboard. The <strong data-prosemirror-content-type="mark" data-prosemirror-mark-name="strong">exception</strong> is if you strongly believe this preprint is of high quality and will be of interest to recommenders, in which case you should ask the author to suggest new recommenders. However, this should not be the standard practice, and we expect most submitted preprints to be cancelled at this point without further delay.</p>
<p data-prosemirror-content-type="node" data-prosemirror-node-name="paragraph" data-prosemirror-node-block="true">Please follow this link to manage the submission: <a href="{{linkTarget}}">{{linkTarget}}</a></p>
<p data-prosemirror-content-type="node" data-prosemirror-node-name="paragraph" data-prosemirror-node-block="true">Thank you in advance.</p>
<p data-prosemirror-content-type="node" data-prosemirror-node-name="paragraph" data-prosemirror-node-block="true">Have a nice day!</p>'
    );
