function cleanFormSaved(pathName = window.location.pathname) {
    localStorage.removeItem(`save-form-${pathName}`);
    localStorage.removeItem(`save-form-${pathName}-t_articles_uploaded_picture`);
}


function callCleanFormSaved() {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('clean_form_saved')) {
        const pathName = urlParams.get('clean_form_saved');
        cleanFormSaved(pathName)
    }
}
callCleanFormSaved();
