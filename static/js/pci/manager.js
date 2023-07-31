function showSetNotConsideredDialog(articleId, url) {
    $.ajax({
        url: url
    }).done(function (response) {
        form = document.getElementById('not-considered-dialog').innerHTML = response;

        const preview = document.getElementById('text-preview');
        const textarea = document.getElementById('mail-dialog-form');
        preview.innerHTML = textarea.value;
        textarea.addEventListener('input', function () {
            preview.innerHTML = textarea.value;
        });

        $('#mail-dialog').modal('show').on('click', '#confirm-mail-dialog', function () {
            const submitUrl = document.getElementById('confirm-mail-dialog').getAttribute('href');
            const subject = document.getElementById('mail-dialog-title').getAttribute('value');

            $.post({
                url: submitUrl,
                data: { subject: subject, message: textarea.value }
            }).done(function () {
                document.getElementById(`button-set-not-considered-${articleId}`).style.display = 'none';
            })
        });
    })
}
