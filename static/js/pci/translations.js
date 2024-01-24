/**
 * Selector
 */

const langSelector = document.getElementById('lang-selector');

const generateTranslationButton = document.getElementById('generate-translation');
const writeTranslationButton = document.getElementById('write-translation');
const saveTranslationButton = document.getElementById('save-translation');


/**
 * Listener
 */

generateTranslationButton.addEventListener('click', generateTranslation);
saveTranslationButton.addEventListener('click', saveTranslation);

langSelector.addEventListener('change', disableGenerateSaveButton);

writeTranslationButton.addEventListener('click', (e) => {
    e.preventDefault();
    toggleWriteBlock();
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


/**
 * AJAX functions
 */

function generateTranslation(e) {
    e.preventDefault();
    generateTranslationButton.insertAdjacentHTML('afterend', '<span id="generate-status">Generation in progress...</span>');

    const lang = langSelector.value;
    
    const url = new URL(generateTranslationButton.getAttribute('link'));
    url.searchParams.append('lang', lang);

    $.ajax({
        type: 'POST',
        url: url
    }).done((response) => {
        insertTranslationForm(response, lang);
    }).always(() => {
        const el = document.getElementById('generate-status');
        if (el != null) {
            el.remove()
        }
    });
}


function saveTranslation(e) {
    e.preventDefault();

    const lang = langSelector.value;

    const url = new URL(saveTranslationButton.getAttribute('link'));
    url.searchParams.append('lang', lang);

    const translationInputId = 'new-translation'
    const translationInput = document.getElementById(translationInputId);
    const isTextarea = translationInput.tagName === 'TEXTAREA';

    let translation;
    if (isTextarea) {
        translation = tinymce.get('new-translation')?.getContent();
    } else {
        translation = translationInput.value;
    }

    $.ajax({
        type: 'POST',
        contentType: 'application/json; charset=utf-8',
        url: url,
        data: JSON.stringify({'translation': translation}),
    }).done((response) => {
        insertTranslationForm(response, lang);
    });
}


function editTranslation(e) {
    e.preventDefault();
    
    const url = new URL(e.target.getAttribute('link'));
    const lang = url.searchParams.get('lang');
    const isTextarea = url.searchParams.get('is_textarea') == 'true';
    let translation;

    if (isTextarea) {
        translation = tinymce.get(lang)?.getContent();
    } else {
        translation = document.getElementById(lang).value;
    }

    $.ajax({
        type: 'POST',
        contentType: 'application/json; charset=utf-8',
        url: url,
        data: JSON.stringify({'translation': translation}),
    }).done((response) => {
        insertTranslationForm(response, lang, isTextarea);
    });
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
                if (form != null) {
                    form.remove();
                }
                disableGenerateSaveButton();
            });
		});

	$('#cancel-dialog')
		.on('click',function(){ return; });
}


/**
 * Misc functions
 */

function insertTranslationForm(response, lang, isTextarea) {
    if (response === 'None') {
        return;
    }

    const langFormList = document.getElementById('lang-form-list');

    const forms = document.querySelectorAll('#lang-form-list form');
    let remplaced = false;
    forms.forEach((form) => {
        const id = `translation-${lang}`
        if (form.id === id) {
            if (isTextarea) {
                tinymce.remove(`#${lang}`);
            }
            form.outerHTML = response;
            remplaced = true;
        }
    });
    
    if (!remplaced) {
        langFormList.insertAdjacentHTML('afterbegin', response);
    }

    langSelector.value = '';
    addListenerLangForm();
    disableGenerateSaveButton();
}


function disableGenerateSaveButton() {
    const disabled = langSelector.value == null || langSelector.value.length === 0;

    generateTranslationButton.disabled = disabled;
    saveTranslationButton.disabled = disabled;
    writeTranslationButton.disabled = disabled;

    const lang = langSelector.value;
    const forms = document.querySelectorAll('#lang-form-list form');
    let translationAlreadyExists = false;
    forms.forEach((form) => {
        if (form.id === `translation-${lang}`) {
            translationAlreadyExists = true;
        }
    });

    if (translationAlreadyExists) {
        generateTranslationButton.disabled = true;
        saveTranslationButton.disabled = true;
        writeTranslationButton.disabled = true;

        if (document.getElementById('generate-status') == null) {
            generateTranslationButton.insertAdjacentHTML('afterend', '<div id="generate-status" class="alert alert-danger" role="alert">Translation already exists</div>');
        }
    } else {
        document.getElementById('generate-status')?.remove();
    }

    if (writeTranslationButton.disabled) {
        hideWriteBlock();
    }
}


function toggleWriteBlock() {
    const writeTranslationBlock = document.getElementById('write-tranlation-block');
    if (writeTranslationBlock.style.display === 'none') {
        writeTranslationBlock.style.display = 'block';
    } else {
        writeTranslationBlock.style.display = 'none';
    }
}


function hideWriteBlock() {
    const writeTranslationBlock = document.getElementById('write-tranlation-block');
    writeTranslationBlock.style.display = 'none';
}


/**
 * TinyMCE
 */

function buildTinyMCETextarea() {
    const textareas = document.querySelectorAll('textarea');
    if (textareas == null) {
        return;
    }

    textareas.forEach((textarea) => {
        addTinyMCEForm(textarea);
    });
}

function addTinyMCEForm(textarea) {
    selector = `#${textarea.id}`
    tinymce_options = generateTinyMCEOptions(selector, selector);
    tinymce.remove(selector);
    
    tinymce.init(tinymce_options).then((el) => {
        const editor = el[0]
        if (editor == null) {
            return;
        }

        const observer = new MutationObserver((changes) => {
        changes[0].target.style.overflowY = 'scroll';
        });
        
        editor.contentDocument.body.style.overflowY = 'scroll';
        observer.observe(editor.contentDocument.body, { attributeFilter: ['style'] });
    });
}

window.addEventListener('load', () => {
    buildTinyMCETextarea();
});


document.getElementById('lang-form-list').addEventListener('DOMNodeInserted', (e) => {
    if (e.target.tagName === 'FORM') {
        textarea = e.target.getElementsByTagName('TEXTAREA')[0]
        if (textarea != null) {
            addTinyMCEForm(textarea);
        }
    }
});
