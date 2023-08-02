let initNotConsideredDialog = false

function showSetNotConsideredDialog(articleId, url) {
    $.ajax({
        url: url
    }).done(function (response) {
        if (!initNotConsideredDialog) {
            initNotConsideredDialog = true;
            document.getElementById('not-considered-dialog').innerHTML = response;
            initTinyMCE();
        }
        
        $('#mail-dialog').modal('show').on('click', '#confirm-mail-dialog', function () {
            const submitUrl = document.getElementById('confirm-mail-dialog').getAttribute('href');
            const subject = document.getElementById('mail-dialog-title').getAttribute('value');
            const textareaValue = tinymce.get('mail_templates_contents').getContent();
            
            $.post({
                url: submitUrl,
                data: { subject: subject, message: textareaValue }
            }).done(function () {
                document.getElementById(`button-set-not-considered-${articleId}`).style.display = 'none';
            })
        });
    });
}
