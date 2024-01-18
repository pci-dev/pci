addTranslationButton = document.getElementById('add-translation');

addTranslationButton.addEventListener('click', addNewLanguage);

function addNewLanguage(e) {
    e.preventDefault();

    select = document.getElementById('lang-selector');
    lang = select.value;
    
    url = new URL(addTranslationButton.getAttribute('link'));
    url.searchParams.append('lang', lang);

    $.ajax({
        type: 'GET',
        url: url
    }).done(function(response) {
        langFormList = document.getElementById('lang-form-list');
        langFormList.insertAdjacentHTML('afterbegin', response);
    })
}
