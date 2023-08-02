function showSetNotConsideredDialog(articleId, url) {
    $.ajax({
        url: url
    }).done(function (response) {
        if (window['initNotConsideredDialog' + articleId]) {
            $('#mail-dialog-' + articleId).modal('show');
            return;
        }

        window['initNotConsideredDialog' + articleId] = true;
        div = document.createElement('div', {'id': 'not-considered-dialog-' + articleId});
        div.innerHTML = response;
        document.body.appendChild(div);
        initTinyMCE('#mail_templates_contents_' + articleId, '#mail_templates_contents');

        $('#mail-dialog-' + articleId).modal('show').on('click', '#confirm-mail-dialog-' + articleId, function () {
            const submitUrl = document.getElementById('confirm-mail-dialog-' + articleId).getAttribute('href');
            const subject = document.getElementById('mail-dialog-title-' + articleId).getAttribute('value');
            const textareaValue = tinymce.get('mail_templates_contents_' + articleId).getContent();

            $.post({
                url: submitUrl,
                data: { subject: subject, message: textareaValue }
            }).done(function () {
                document.getElementById(`button-set-not-considered-${articleId}`).style.display = 'none';
            })
        });
    });
}
