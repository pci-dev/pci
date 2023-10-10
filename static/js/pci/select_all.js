function update_parameter_for_selection() {
    let checkboxes = document.querySelectorAll('.multiple-choice-checks');
    let ids = '';
    for (let i = 0; i < checkboxes.length; i++) {
        let checkbox = checkboxes[i];
        if (checkbox.checked) {
            article_id = checkbox.id.split('_')[1];
            ids = ids + article_id + ',';
        }
    }

    let select_button = document.querySelector('.select-all-btn');
    let href = select_button.getAttribute('href');
    let new_href = update_parameter_in_url(href, 'recommenderIds', ids.substring(0,ids.length-1))
    
    select_button.setAttribute('href', new_href);
}


function update_parameter_in_url(url, paramName, paramValue) {
    var newUrl;
    var encodedParamName = encodeURIComponent(paramName);
    var encodedParamValue = encodeURIComponent(paramValue).replace(/%2C/g, ',');
    
    // check if parameter exists
    if (url.match(new RegExp("[?&]" + encodedParamName + "=([^&#]*)"))) {
        newUrl = url.replace(
            new RegExp("([?&]" + encodedParamName + "=)[^&#]*"),
            "$1" + encodedParamValue
        );
    } else {
        if (url.indexOf('?') > -1) {
            newUrl = url + '&' + encodedParamName + '=' + encodedParamValue;
        } else {
            newUrl = url + '?' + encodedParamName + '=' + encodedParamValue;
        }
    }
    return newUrl;
}