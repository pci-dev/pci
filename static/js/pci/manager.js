function showSetNotConsideredDialog(articleId, url) {
    $.ajax({
        url: url
    }).done(function (response) {
        if (window['initNotConsideredDialog' + articleId]) {
            $('#mail-dialog-' + articleId).modal('show');
            return;
        }

        window['initNotConsideredDialog' + articleId] = true;
        div = document.createElement('div', { 'id': 'not-considered-dialog-' + articleId });
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
    }).done((response) => {
        const rdvContainer = document.getElementById(`container-rdv-date-${articleId}`);
        const newRdvContainer = document.createElement('div');
        newRdvContainer.innerHTML = response;
        rdvContainer.parentNode.replaceChild(newRdvContainer.firstChild, rdvContainer)

    });
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
    const payload = {
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

initStyle();
function initStyle() {
    const searchBtn = document.querySelector('input.btn-default[value="New Search"]')
    searchBtn.classList.add('btn');
    searchBtn.classList.add('btn-default');
    searchBtn.classList.add('add-btn');
    searchBtn.onclick = '';
    searchBtn.type = 'submit';

    document.querySelectorAll('btn[value="New search"]').forEach((el) => {
        el.value = 'SEARCH';
        el.style.backgroundColor = '#93c54b';
        el.type = 'submit';
    });

    document.querySelectorAll('#w2p_query_panel .btn').forEach((el) => {
            if (el.value.toLowerCase() !== 'new search') {
                el.style.display = 'none';
            }
            else if (el.value.toLowerCase() === 'clear') {
                el.value = 'Reset';
            }
            else if (el.value.toLowerCase() === 'reset') {

            } else {
                console.log(el);
                el.value = 'SEARCH';
                el.style.backgroundColor = '#93c54b';
                el.addEventListener('click', (e) => {
                    new_search(e);
                });
            }
    });

    const articleIdOption = document.querySelector('option[value="t_articles.id"]');
    articleIdOption.textContent = 'Article ID';
    articleIdOption.classList.add('integer-field');
}
