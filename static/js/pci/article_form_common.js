var userId = getCookie('user_id');

//////////////

function getBase64(file) {
    return new Promise((resolve,reject)=>{
        var reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = function () {
        resolve(reader.result)
        };
        reader.onerror = reject;
    });
}
  

function dataURItoBlob(base64Data, mimeType) {
    const binary = atob(base64Data.split(',')[1]);
    const array = [];

    for (let i = 0; i < binary.length; i++) {
        array.push(binary.charCodeAt(i));
    }
    return new Blob([new Uint8Array(array)], {type: mimeType});
}
  

function getMimeType(base64Data) {
    const mimeType = base64Data.match(/data:([a-zA-Z0-9]+\/[a-zA-Z0-9-.+]+).*,.*/);
    if (mimeType && mimeType.length > 0) {
        return mimeType[1];
    }
}
  

function initUploadedPictureField(storageKey, storage) {
    const uploadFileInput = document.getElementById('t_articles_uploaded_picture');
    if (!uploadFileInput || uploadFileInput.files.length > 0) {
        return;
    }

    const item = JSON.parse(storage.getItem(storageKey));
    if (item == null) {
        return;
    }

    const base64Data = item.base64;
    const mimeType = getMimeType(base64Data);
    const blob = dataURItoBlob(base64Data, mimeType);
    const file = new File([blob], item.filename, {type: mimeType, lastModified: new Date().getTime() });

    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    uploadFileInput.files = dataTransfer.files;
}


async function saveUploadedPictureInStorage(fileInput, storageKey, storage) {
    if (fileInput == null) {
        return;
    }

    const base64Data = await getBase64(fileInput);
    storage.setItem(storageKey, JSON.stringify({
        pathName: window.location.pathname,
        filename: fileInput.name,
        base64: base64Data}));
}

////

document.getElementById('t_articles_uploaded_picture')?.addEventListener('change', async(e) => {
    if (e.target.files.length === 0) {
        return;
    }
    saveUploadedPictureInStorage(e.target.files[0], `t_articles_uploaded_picture-${userId}`, sessionStorage);
});


initUploadedPictureField(`t_articles_uploaded_picture-${userId}`, sessionStorage);

////
document.getElementsByTagName('form')[0]?.addEventListener('submit', (e) => {
    if (e.submitter.id !== 'save-article-form-button') {
        return;
    }

    e.preventDefault();
    saveForm(e).then(() => {
        sendPostVar('save', 'save');
        HTMLFormElement.prototype.submit.call(e.target)
    });
});

document.getElementById('clean-save-article-form-button')?.addEventListener('click', () => {
    cleanFormSaved();
});

async function saveForm(e) {
    const values = {
        data_doi: Array(),
        scripts_doi: Array(),
        codes_doi: Array(),

        suggest_reviewers: Array(),
        competitors: Array()
    };

    const data_doi_ul = document.getElementById('t_articles_data_doi_grow_input');
    const scripts_doi_ul = document.getElementById('t_articles_scripts_doi_grow_input');
    const codes_doi_ul = document.getElementById('t_articles_codes_doi_grow_input');

    const sugg_reviewers_ul = document.getElementById('t_articles_suggest_reviewers_grow_input');
    const opp_reviewers_ul = document.getElementById('t_articles_competitors_grow_input');

    const data_doi_inputs = data_doi_ul?.getElementsByTagName('input');
    values.data_doi.push(...Array.from(data_doi_inputs || [], input => input.value));

    const scripts_doi_inputs = scripts_doi_ul?.getElementsByTagName('input');
    values.scripts_doi.push(...Array.from(scripts_doi_inputs || [], input => input.value));

    const codes_doi_inputs = codes_doi_ul?.getElementsByTagName('input');
    values.codes_doi.push(...Array.from(codes_doi_inputs || [], input => input.value));

    const sugg_reviewers_inputs = sugg_reviewers_ul?.getElementsByTagName('input');
    values.suggest_reviewers.push(...Array.from(sugg_reviewers_inputs || [], input => input.value));
    
    const opp_reviewers_inputs = opp_reviewers_ul?.getElementsByTagName('input');
    values.competitors.push(...Array.from(opp_reviewers_inputs || [], input => input.value));


    const uploadedPicture = document.getElementById('t_articles_uploaded_picture')?.files[0];
    if (uploadedPicture != null) {
        const base64Data = await getBase64(uploadedPicture);
        const img = { filename: uploadedPicture.name, base64: base64Data };
        sendPostVar('saved_picture', JSON.stringify(img));
    }
    
    sendPostVar('list_str', JSON.stringify(values));
}


function sendPostVar(key, value) {
    const form = document.getElementsByTagName('form')[0];

    let input = document.getElementById(key);
    let alreadyExistsInput = false;
    if (input == null) {
        input = document.createElement('input');
    } else {
        alreadyExistsInput = true;
    }

    input.name = key;
    input.id = key;
    input.type = 'hidden';
    input.value = value;

    if (!alreadyExistsInput) {
        form.appendChild(input);
    }
}

function addInnerHTMLInnerForListValue(formName) {
    const inputId = `t_articles_${formName}`;
    const ul_el = document.getElementById(`${inputId}_grow_input`);

    const values = savedListStr[formName];

    if (ul_el && values.length > 0) {
        ul_el.innerHTML = '';

        for (const value of values) {
            ul_el.innerHTML += `
            <li>
                <div class="input-group" style="width: 100%">
                    <input class="string form-control" id="${inputId}" name="${formName}" type="text" value="${value}">
                </div>
            </li>`;
        }
    }
}

function loadFormSaved() {
    if (typeof savedListStr !== 'undefined' && savedListStr != null) {
        addInnerHTMLInnerForListValue('data_doi');
        addInnerHTMLInnerForListValue('scripts_doi');
        addInnerHTMLInnerForListValue('codes_doi');
        addInnerHTMLInnerForListValue('suggest_reviewers');
        addInnerHTMLInnerForListValue('competitors');
    }

    if (typeof savedPicture !== 'undefined' && savedPicture != null) {
        initSavedUploadedPictureField();
        const uploadedPicture = document.getElementById('t_articles_uploaded_picture');
        saveUploadedPictureInStorage(uploadedPicture.files[0], `t_articles_uploaded_picture-${userId}`, sessionStorage)
    }
}
loadFormSaved();

function initSavedUploadedPictureField() {
        const uploadFileInput = document.getElementById('t_articles_uploaded_picture');
        if (!uploadFileInput) {
            return;
        }
    
        if (savedPicture == null) {
            return;
        }
    
        const base64Data = savedPicture.base64;
        const mimeType = getMimeType(base64Data);
        const blob = dataURItoBlob(base64Data, mimeType);
        const file = new File([blob], savedPicture.filename, {type: mimeType, lastModified: new Date().getTime() });
    
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        uploadFileInput.files = dataTransfer.files;
}


////////

var formHasModification = false;

document.getElementsByTagName('form')[0]?.addEventListener('input', () => {
    formHasModification = true;
});


var observerForTinyMce = new MutationObserver(() => {
    document.querySelectorAll('.tox-edit-area__iframe').forEach((tinymceForm) => {
        tinymceForm.contentWindow.document.addEventListener('input', () => {
            formHasModification = true;
        });
    });    
});
observerForTinyMce.observe(document.body, { childList: true, subtree: true });

window.addEventListener('beforeunload', (e) => {
    const thereAreValues = JSON.parse(localStorage.getItem(`save-form-${window.location.pathname}-${userId}`));

    const sumbitBtnIds = [
        'save-article-form-button',
        'submit-article-btn',
        'myModal',
        'bpt'
    ];

    const isSubmitAction = sumbitBtnIds.indexOf(e.target.activeElement.id) > -1;

    if (!formHasModification) {
        return;
    }

    if (formHasModification && isSubmitAction) {
        return;
    }

    return e.preventDefault();
});
