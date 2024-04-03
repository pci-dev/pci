/**
 * Selector
 */

const langSelector = document.getElementById('lang-selector');

const generateTranslationButton = document.getElementById('generate-translation');
const writeTranslationButton = document.getElementById('write-translation');
const saveTranslationButton = document.getElementById('save-translation');

const saveAllTranslationButton = document.getElementById('save-all-translation');


/**
 * Listener
 */

generateTranslationButton?.addEventListener('click', generateTranslation);
saveTranslationButton?.addEventListener('click', saveTranslation);

saveAllTranslationButton?.addEventListener('click', saveAllTranslation);

langSelector.addEventListener('change', disableGenerateSaveButton);

writeTranslationButton.addEventListener('click', (e) => {
    e.preventDefault();
    toggleWriteBlock();
});


addListenerLangForm();
function addListenerLangForm() {
    const langFormSaveButtons = document.querySelectorAll('.lang-form-save-button');
    const langFormDeleteButtons = document.querySelectorAll('.lang-form-delete-button');

    const langFormSaveAllButtons = document.querySelectorAll('.lang-form-save-all-button');
    const langFormDeleteAllButtons = document.querySelectorAll('.lang-form-delete-all-button');

    const langForm = document.querySelectorAll('#lang-form-list form');

    langFormSaveButtons.forEach((saveButton) => {
        saveButton.addEventListener('click', editTranslation);
    });
    
    langFormDeleteButtons.forEach((deleteButton) => {
        deleteButton.addEventListener('click', deleteTranslation);
    });

    langFormSaveAllButtons.forEach((saveButton) => {
        saveButton.addEventListener('click', editAllTranslation);
    });

    langFormDeleteAllButtons.forEach((deleteButton) => {
        deleteButton.addEventListener('click', deleteAllTranslation);
    });

    langForm.forEach((form) => {
        toggleEditButton(form);
        addEventListenerToogleEditButton(null, form);
    });
}

function addEventListenerToogleEditButton(lang, form) {
    if (lang != null) {
        formId = `translation-${lang}`;
        form = document.getElementById(formId);
    }

    if (form == null) {
        return;
    }

    inputs = form.querySelectorAll('input, textarea');
    inputs.forEach((input) => {
        toggleEditButton(form);
        input.addEventListener('keyup', () => {
            toggleEditButton(form);
        });
        input.addEventListener('change', () => {
            toggleEditButton(form);
        });
    })

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

function saveAllTranslation(e) {
    e.preventDefault();
    
    const lang = langSelector.value;

    const url = new URL(saveAllTranslationButton.getAttribute('link'));
    url.searchParams.append('lang', lang);

    const translationTitleInputId = 'title-new-translation';
    const translationAbstractInputId = 'abstract-new-translation';
    const translationKeywordsInputId = 'keywords-new-translation';

    const translationTitleInput = document.getElementById(translationTitleInputId);
    const translationKeywordsInput = document.getElementById(translationKeywordsInputId);

    let title = translationTitleInput.value;
    let abstract = tinymce.get(translationAbstractInputId)?.getContent();
    let keywords = translationKeywordsInput.value;

    payload = {
        title,
        abstract,
        keywords
    }

    $.ajax({
        type: 'POST',
        contentType: 'application/json; charset=utf-8',
        url: url,
        data: JSON.stringify(payload),
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

    const publicCheckBox = document.getElementById(`checkboxpublic-${lang}`);

    payload = {
        'translation': translation,
        'public': publicCheckBox.checked
    }

    $.ajax({
        type: 'POST',
        contentType: 'application/json; charset=utf-8',
        url: url,
        data: JSON.stringify(payload),
    }).done((response) => {
        insertTranslationForm(response, lang, isTextarea);
    });
}

function editAllTranslation(e) {
    e.preventDefault();
    
    const url = new URL(e.target.getAttribute('link'));
    const lang = url.searchParams.get('lang');
    
    const translationTitleInputId = `title-${lang}`;
    const translationAbstractInputId = `abstract-${lang}`;
    const translationKeywordsInputId = `keywords-${lang}`;

    const title = document.getElementById(translationTitleInputId).value;
    const abstract = tinymce.get(translationAbstractInputId)?.getContent();
    const keywords = document.getElementById(translationKeywordsInputId).value;

    const publicCheckBox = document.getElementById(`checkboxpublic-${lang}`);

    payload = {
        title,
        abstract,
        keywords,
        'public': publicCheckBox.checked
    }

    $.ajax({
        type: 'POST',
        contentType: 'application/json; charset=utf-8',
        url: url,
        data: JSON.stringify(payload),
    }).done((response) => {
        insertTranslationForm(response, lang);
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

function deleteAllTranslation(e) {
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
    addEventListenerToogleEditButton(lang);
}


function toggleEditButton(form) {
    editButton = form.querySelector('.lang-form-save-all-button');
    if (editButton == null) {
        return;
    }
    editButton.disabled = !isModifiedForm(form);
    if (editButton.disabled) {
        editButton?.classList.add('disabled');
    } else {
        editButton?.classList.remove('disabled');
    }
}


function isModifiedForm(form) {
    inputs = form.querySelectorAll('input, textarea');

    let modified = false;
    inputs.forEach((input) => {
        if (isModifiedInput(input.id)) {
            modified = true;
        }
    });

    return modified;
}


function isModifiedInput(inputId) {
    if (inputId == null) {
        return;
    }

    const el = document.getElementById(inputId);

    const lang = getLangFromFieldId(inputId);
    let intialValue = el.getAttribute('initial');
    const editButton = document.querySelector(`#translation-${lang} .lang-form-save-all-button`);
    const isTextarea = el.tagName === 'TEXTAREA';
    const isCheckbox = el.type === 'checkbox';
    let newValue;

    if (isTextarea) {
        newValue = tinymce.get(inputId)?.getContent();
    }
    else if (isCheckbox) {
        intialValue = el?.hasAttribute('checked');
        newValue = el?.checked;
    } else {
        newValue = el.value;
    }

    return !isSameContent(intialValue, newValue)
}


function isSameContent(intialValue, newValue) {

    if (typeof intialValue !== 'string' || typeof newValue !== 'string') {
        return intialValue === newValue
    }

    let oldContent = intialValue?.replace('\r', '')
    ?.replace('&nbsp;', '')
    ?.replace(/(<([^>]+)>)/g, '');

    let newContent = newValue?.replace('\r', '')
    ?.replace('&nbsp;', '')
    ?.replace(/(<([^>]+)>)/g, '');

    return oldContent === newContent;
}


function getLangFromFieldId(id) {
    var lang = id.split('-');
    lang.shift();
    return lang.join('-');
}


function disableGenerateSaveButton() {
    const disabled = langSelector.value == null || langSelector.value.length === 0;

    generateTranslationButton.disabled = disabled;
    writeTranslationButton.disabled = disabled;

    if (saveTranslationButton != null) {
        saveTranslationButton.disabled = disabled;
    }
    if (saveAllTranslationButton != null) {
        saveAllTranslationButton.disabled = disabled;
    }
    if (!langSelector.selectedOptions[0].innerText.endsWith(' - Generation supported')) {
        generateTranslationButton.disabled = true;
    }

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
        if (saveTranslationButton != null) {
            saveTranslationButton.disabled = true;
        }
        if (saveAllTranslationButton != null) {
            saveAllTranslationButton.disabled = disabled;
        }
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
        toggleEditButton(editor.formElement);
        editor.on('keyup', () => {
            toggleEditButton(editor.formElement);
        });
        editor.on('change', () => {
            toggleEditButton(editor.formElement);
        });
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
