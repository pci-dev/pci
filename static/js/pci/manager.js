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
                button = document.getElementById(`button-set-not-considered-${articleId}`);
                if (button != null) {
                    button.style.display = 'none';
                }
            })
        });
    });
}

function rdvDateInputChange(articleId, url) {
    const rdvInput = document.getElementById(`rdv_date_${articleId}`);
    if (rdvInput == null) {
        return;
    }

    payload = {
        'article_id': articleId,
        'new_date': rdvInput.value
    };

    $.ajax({
        type: 'POST',
        url: url,
        data: payload
    }).done((response) => {});
}

let remarksTimeoutId = null;
let initialColorRemarks = null;

function remarksInputChange(articleId, url) {
    const remarksInput = document.getElementById(`remarks_${articleId}`);
    if (remarksInput == null) {
        return;
    }

    if (initialColorRemarks == null) {
        initialColorRemarks = remarksInput.style.color;
    }
    remarksInput.style.color = '#6f6f6f';

    if (remarksTimeoutId != null) {
        clearTimeout(remarksTimeoutId);
    }
    remarksTimeoutId = setTimeout(sendRemarks, 1000, articleId, url, remarksInput)
}

function sendRemarks(articleId, url, remarksInput) {
    payload = {
        'article_id': articleId,
        'remarks': remarksInput.value
    };

    $.ajax({
        type: 'POST',
        url: url,
        data: payload
    }).done((response) => {
        remarksInput.style.color = initialColorRemarks;
    });
}
