relocate_btns();
let select_buttons = document.querySelectorAll('.select-all-btn');
var exclude_checked = 0;

if (select_buttons.length > 0) {
    // prepare modal creation for confirmation of multiple recommender exclusions
    var modal = document.createElement('div');
    var modal_backdrop = document.createElement('div');
    var button_yes = document.createElement('span');
    var button_nope = document.createElement('span');
    var modal_body = document.createElement('div');
    var modal_footer = document.createElement('div');
    var prevent_or_fire = 'prevent';

    for (let i = 0; i < select_buttons.length; i++) {
        let status_button = select_buttons[i];
        create_modal('button', status_button[i]);
        status_button.addEventListener('click', function(event) {
        if (prevent_or_fire == 'prevent') {
            event.preventDefault();
            var exclude_checkboxes = document.querySelectorAll('.exclude');
            for (let i = 0; i < exclude_checkboxes.length; i++) {
                if (exclude_checkboxes[i].checked) { exclude_checked += 1; }
            }
            if (exclude_checked < 2) {
                exclude_checked = 0;
                prevent_or_fire = 'fire';
                status_button.click();
                return
            }
            modal_body.innerHTML = 'Are you sure you want to EXCLUDE all of these potential recommenders?';

            // if status field is changed, show modal and hook listeners to the buttons
            let body = document.querySelector('body');
            body.style.overflow = 'hidden';

            modal.style.display = 'block';
            document.body.appendChild(modal_backdrop);
            modal_backdrop.style.display = 'block';

            button_yes.addEventListener('click', function() {
                // allow change and remove modal
                modal.style.display = 'none';
                modal_backdrop.style.display = 'none';
                body.style.overflow = 'scroll';
                prevent_or_fire = 'fire';
                status_button.click();
            })

            button_nope.addEventListener('click', function() {
                // reject change and remove modal
                modal.style.display = 'none';
                modal_backdrop.style.display = 'none';
                body.style.overflow = 'scroll';
            })
            exclude_checked = 0;
        }
        else { prevent_or_fire == 'prevent'; }
        })
    }
}


function create_modal() {
    // create confirmation modal
    modal.id = "confirm-change-modal";
    modal.classList.add('modal');
    modal.classList.add('fade');
    modal.classList.add('in');
    modal.setAttribute('role', 'dialog');
    modal.style.paddingRight = '0px';

    modal_body.classList.add('modal-body');
    modal_footer.classList.add('modal-footer');

    button_yes.classList.add('btn');
    button_yes.classList.add('btn-info');
    button_yes.setAttribute('data-dismiss', 'modal');
    button_yes.setAttribute('type', 'button');
    button_yes.innerHTML = 'Yes'

    button_nope.classList.add('btn');
    button_nope.classList.add('btn-default');
    button_nope.setAttribute('data-dismiss', 'modal');
    button_nope.setAttribute('type', 'button');
    button_nope.innerHTML = 'No';

    modal_footer.appendChild(button_yes);
    modal_footer.appendChild(button_nope);

    modal.appendChild(modal_body);
    modal.appendChild(modal_footer);

    modal_backdrop.classList.add('modal-backdrop');
    modal_backdrop.classList.add('fade');
    modal_backdrop.classList.add('in');

    document.body.appendChild(modal);
}


function relocate_btns() {
    let first_select_btn = document.querySelector('.select-all-btn');
    let first_accept_btn = document.querySelector('.done-btn');
    let grid = document.querySelector('.web2py_grid');
    let table = grid.querySelector('.web2py_table');
    let counter = grid.querySelector('.web2py_counter');
    counter.style.marginBottom = '0';
    grid.insertBefore(first_select_btn, table);
    if (first_accept_btn) {
        grid.insertBefore(first_accept_btn, table);
    }
}

function update_parameter_for_selection(checkbox_clicked) {
    // checkbox is clicked, uncheck partner box of the same row and add ID to button referral
    // first uncheck row complementary button
    let modus = checkbox_clicked.id.split('_')[1];
    let recommender_row = false;
    if (modus == 'suggest') {
        recommender_row = checkbox_clicked.parentNode.parentNode.parentNode;
        let exclude_btn = recommender_row.querySelector('.exclude');
        if (exclude_btn) { exclude_btn.checked = false; }
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
