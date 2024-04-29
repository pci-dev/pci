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
  

function initUploadedPictureField() {
    const uploadFileInput = document.getElementById('t_articles_uploaded_picture');
    if (!uploadFileInput || uploadFileInput.files.length > 0) {
        return;
    }

    const item = JSON.parse(sessionStorage.getItem('t_articles_uploaded_picture'));
    if (item == null) {
        return;
    }

    const base64Data = item.base64;
    const mimeType = getMimeType(base64Data)
    const blob = dataURItoBlob(base64Data, mimeType);
    const file = new File([blob], item.filename, {type: mimeType, lastModified: new Date().getTime() });

    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    uploadFileInput.files = dataTransfer.files;
}


document.getElementById('t_articles_uploaded_picture')?.addEventListener('change', async(e) => {
    if (e.target.files.length === 0) {
        return;
    }

    const file = e.target.files[0];
    const base64Data = await getBase64(file);
    sessionStorage.setItem('t_articles_uploaded_picture', JSON.stringify({
        pathName: window.location.pathname,
        filename: file.name,
        base64: base64Data}));
});


initUploadedPictureField();
