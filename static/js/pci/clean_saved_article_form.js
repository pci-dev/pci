function cleanFormSaved(pathName = window.location.pathname) {
    const userId = getCookie('user_id');

    localStorage.removeItem(`save-form-${pathName}-${userId}`);
    localStorage.removeItem(`save-form-${pathName}-t_articles_uploaded_picture-${userId}`);
    sessionStorage.removeItem(`t_articles_uploaded_picture-${userId}`);
}


function callCleanFormSaved() {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('clean_form_saved')) {
        const pathName = urlParams.get('clean_form_saved');
        cleanFormSaved(pathName)
    }
}
callCleanFormSaved();
