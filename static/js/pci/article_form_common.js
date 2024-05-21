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
    saveUploadedPictureInStorage(e.target.files[0], 't_articles_uploaded_picture', sessionStorage);
});


initUploadedPictureField('t_articles_uploaded_picture', sessionStorage);

////

document.getElementById('save-article-form-button').addEventListener('click', saveForm);
document.getElementById('clean-save-article-form-button').addEventListener('click', cleanFormSaved);

function getSaveFormUploadedPictureLabel() {
    return `save-form-${window.location.pathname}-t_articles_uploaded_picture`;
}


async function saveForm(e) {
    const values = {
        data_doi: []
    };

    const data_doi_ul = document.getElementById('t_articles_data_doi_grow_input');
    const data_doi_inputs = data_doi_ul.getElementsByTagName('input');
    for (const input of data_doi_inputs) {
      values.data_doi.push(input.value)
    }

    localStorage.setItem(`save-form-${window.location.pathname}`, JSON.stringify(values));

    const uploadedPicture = document.getElementById('t_articles_uploaded_picture')?.files[0];
    saveUploadedPictureInStorage(uploadedPicture, getSaveFormUploadedPictureLabel(), localStorage);
}


function loadFormSaved() {
    const values = JSON.parse(localStorage.getItem(`save-form-${window.location.pathname}`));
    if (values == null) {
        return;
    }

    const data_doi_ul = document.getElementById('t_articles_data_doi_grow_input');
    if (values.data_doi.length > 0) {
        data_doi_ul.innerHTML = ''
    }

    for (const value of values.data_doi) {
        data_doi_ul.innerHTML += `
        <li>
            <div class="input-group" style="width: 100%">
                <input class="string form-control" id="t_articles_data_doi" name="data_doi" type="text" value="${value}">
            </div>
        </li>`;
    }

    const uploadedPicture = document.getElementById('t_articles_uploaded_picture');
    initUploadedPictureField(getSaveFormUploadedPictureLabel(), localStorage);

    document.getElementById('clean-save-article-form-button').style.display = 'inline-block';
}
loadFormSaved();
