delete from mail_templates
where
        hashtag in ('#CommentPosted');

        

INSERT INTO
        mail_templates (hashtag, lang, subject, description, contents)
VALUES
        (
                '#CommentPosted',
                'default',
                'New comment posted',
                'New comment posted',
                '<p data-pm-slice="1 1 []">Dear managing board,</p>
<p data-pm-slice="1 1 []">A comment has been posted about the article "{{articleTitle}}" and its recommendation at the URL <a href="{{linkTarget}}">{{linkTarget}}</a>.</p>'
        );
