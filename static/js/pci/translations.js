const langSelector = document.getElementById('lang-selector');

const generateTranslationButton = document.getElementById('generate-translation');
const writeTranslationButton = document.getElementById('write-translation');
const saveTranslationButton = document.getElementById('save-translation');

generateTranslationButton.addEventListener('click', generateNewTranslation);
saveTranslationButton.addEventListener('click', saveNewTranslation);

langSelector.addEventListener('change', () => {
    const disabled = langSelector.value == null || langSelector.value.length === 0;

    generateTranslationButton.disabled = disabled;
    saveTranslationButton.disabled = disabled;

    const lang = langSelector.value;
    const forms = document.querySelectorAll('#lang-form-list form');
    forms.forEach((form) => {
        if (form.id === `translation-${lang}`) {
                generateTranslationButton.disabled = true;
        }
    });
});


writeTranslationButton.addEventListener('click', (e) => {
    e.preventDefault();

    const writeTranslationBlock = document.getElementById('write-tranlation-block');
    if (writeTranslationBlock.style.display === 'none') {
        writeTranslationBlock.style.display = 'block';
    } else {
        writeTranslationBlock.style.display = 'none';
    }
});

addListenerLangForm();
function addListenerLangForm() {
    const langFormSaveButtons = document.querySelectorAll('.lang-form-save-button');
    const langFormDeleteButtons = document.querySelectorAll('.lang-form-delete-button');

    langFormSaveButtons.forEach((saveButton) => {
        saveButton.addEventListener('click', editTranslation);
    });
    
    langFormDeleteButtons.forEach((deleteButton) => {
        deleteButton.addEventListener('click', deleteTranslation);
    });
}


function generateNewTranslation(e) {
    e.preventDefault();
    generateTranslationButton.insertAdjacentHTML('afterend', '<span id="generate-status">Generation in progress...</span>');

    const lang = langSelector.value;
    
    const url = new URL(generateTranslationButton.getAttribute('link'));
    url.searchParams.append('lang', lang);

    $.ajax({
        type: 'POST',
        url: url
    }).done((response) => {
        addNewTranslationForm(response, lang);
    }).always(() => {
        const el = document.getElementById('generate-status');
        if (el != null) {
            el.remove()
        }
    });
}


function saveNewTranslation(e) {
    e.preventDefault();

    const lang = langSelector.value;
    
    const url = new URL(saveTranslationButton.getAttribute('link'));
    url.searchParams.append('lang', lang);

    const translation = document.getElementById('new-translation').value;

    $.ajax({
        type: 'POST',
        contentType: 'application/json; charset=utf-8',
        url: url,
        data: JSON.stringify({'translation': translation}),
    }).done((response) => {
        addNewTranslationForm(response, lang);
    });
}


function editTranslation(e) {
    e.preventDefault();
    
    const url = new URL(e.target.getAttribute('link'));
    const lang = url.searchParams.get('lang');

    const translation = document.getElementById(lang).value;

    $.ajax({
        type: 'POST',
        contentType: 'application/json; charset=utf-8',
        url: url,
        data: JSON.stringify({'translation': translation}),
    }).done((response) => {
        addNewTranslationForm(response, lang);
    });
}


function addNewTranslationForm(response, lang) {
    if (response === 'None') {
        return;
    }

    const langFormList = document.getElementById('lang-form-list');

    const forms = document.querySelectorAll('#lang-form-list form');
    let remplaced = false;
    forms.forEach((form) => {
        if (form.id === `translation-${lang}`) {
            form.insertAdjacentHTML('beforebegin', response);
            form.remove();
            remplaced = true;
        }
    });
    
    if (!remplaced) {
        langFormList.insertAdjacentHTML('afterbegin', response);
    }

    addListenerLangForm();
}

function deleteTranslation(e) {
    e.preventDefault();
    
    const url = new URL(e.target.getAttribute('link'));
    const lang = url.searchParams.get('lang');

    $('#confirmation-modal').modal('show')
		.on('click', '#confirm-dialog', function(){
			$.ajax({
                type: 'GET',
                url: url,
            }).done(() => {
                const form = document.getElementById(`translation-${lang}`);
                form.remove();
            });
		});

	$('#cancel-dialog')
		.on('click',function(){ return; });
}
