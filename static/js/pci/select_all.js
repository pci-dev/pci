relocate_select_btn();


function relocate_select_btn() {
    let first_sort_btn = document.querySelector('.select-all-btn');
    let grid = document.querySelector('.web2py_grid');
    let table = grid.querySelector('.web2py_table');
    let counter = grid.querySelector('.web2py_counter');
    counter.style.marginBottom = '0';
    grid.insertBefore(first_sort_btn, table);
}


function update_parameter_for_selection(checkbox_clicked) {
    // checkbox is clicked, uncheck partner box of the same row and add ID to button referral
    // first uncheck row complementary button
    let modus = checkbox_clicked.id.split('_')[1];
    let recommender_row = false;
    if (modus == 'suggest') {
        recommender_row = checkbox_clicked.parentNode.parentNode.parentNode;
        let exclude_btn = recommender_row.querySelector('.exclude');
        exclude_btn.checked = false;
     }
    else {
        recommender_row = checkbox_clicked.parentNode.parentNode.parentNode.parentNode;
        let suggest_btn = recommender_row.querySelector('.suggest');
        suggest_btn.checked = false;
    }

    // collect IDs of suggestions and exclusions
    let checkboxes = document.querySelectorAll('.multiple-choice-checks');
    let suggest_ids = '';
    let exclude_ids = '';
    for (let i = 0; i < checkboxes.length; i++) {
        let checkbox = checkboxes[i];
        if (checkbox.checked) {
            let id_fragments = checkbox.id.split('_');
            let single_modus = id_fragments[1];
            let article_id = id_fragments[2];
            if (single_modus == 'suggest') {
                suggest_ids = suggest_ids + article_id + ',';
            }
            else if (single_modus == 'exclude') {
                exclude_ids = exclude_ids + article_id + ',';
            }
        }
    }

    // hook IDs to button referral
    let select_buttons = document.querySelectorAll('.select-all-btn');
    for (let i = 0; i < select_buttons.length; i++) {
        let href = select_buttons[i].getAttribute('href');
        let new_href = update_parameters_in_url(href, ['recommenderIds', 'exclusionIds'], [suggest_ids.substring(0,suggest_ids.length-1), exclude_ids.substring(0,exclude_ids.length-1)])
        select_buttons[i].setAttribute('href', new_href);
    }
}


function update_parameters_in_url(url, paramNames, paramValues) {
    var newUrl;

    for (let i = 0; i < paramNames.length; i++) {
        if (paramValues[i] == '') { continue }
        var encodedParamName = encodeURIComponent(paramNames[i]);
        var encodedParamValue = encodeURIComponent(paramValues[i]).replace(/%2C/g, ',');

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
        url = newUrl;
    }

    return newUrl;
}
