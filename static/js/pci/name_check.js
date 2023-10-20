var submit_btn_2 = document.querySelector('#submit_record__row input');
var unique = false;
var user_json = false;
var choose_note = false;

submit_btn_2.addEventListener('click', function(evt) {
    if (!unique) {
        evt.preventDefault();
        let firstname = '';
        let lastname = '';
        name_json = gather_name();
        check_database(name_json);
    }
    else {
        evt.click();
    }
});

function check_database(name_json) {
    // check if the entered name exists in the DB
    $.ajax({
        url: 'check_reviewer_name',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(name_json),
        success: function(response) {
            let success = response['success'];
            if (success) {
                user_json = response;
                create_question_modal(user_json);
            }
            else {
                unique = true;
                submit_btn_2.click();
            }
        },
        error: function(error) {
            console.log('Error: ', error);
        }
    })
}

function create_question_modal(user_json) {
    // create and open the modal with the proposed users from the DB
    let container = document.createElement('div');
    container.id = 'modal-container';
    let backdrop = document.createElement('div');
    backdrop.classList.add('modal-backdrop');
    backdrop.classList.add('fade');
    backdrop.classList.add('in');
    container.appendChild(backdrop);

    let modal = document.createElement('div');
    modal.classList.add('modal');
    modal.classList.add('fade');
    modal.classList.add('in');
    modal.id = 'find-reviewer-modal';
    modal.style.display = 'block';
    modal.style.paddingRight = '0px';

    let modal_body = document.createElement('div');
    modal_body.classList.add('modal-body');
    let span = document.createElement('span');
    span.innerHTML = 'The name you entered corresponds to reviewer/s in our database. Is either of these persons the reviewer you are looking for?<br><br>';
    let users = user_json['users'];
    for (let i = 0; i < users.length; i++) {
        span.innerHTML += '<input type="checkbox" class="user-checkbox" onclick="only_one(this)" id="checkbox_' + String(i) + '">'
        span.innerHTML += String(users[i]['first_name']) + ' ';
        span.innerHTML += String(users[i]['last_name']) + ' ';
        span.innerHTML += '(' + String(users[i]['email']) + '), ';
        if (String(users[i]['institution']) != 'null') { span.innerHTML += 'institution: ' + String(users[i]['institution']) + ', '; }
        if (String(users[i]['laboratory']) != 'null') { span.innerHTML += 'laboratory: ' + String(users[i]['laboratory']) + ', '; }
        if (String(users[i]['country']) != 'null') { span.innerHTML += 'country: ' + String(users[i]['country']); }
        span.innerHTML += '<hr>';
    }

    let modal_footer = document.createElement('div');
    modal_footer.classList.add('modal-footer');
    modal_footer.classList.add('modal-footer2');
    let confirm_link = document.createElement('a');
    confirm_link.innerHTML = 'Yes, add the selected reviewer';
    confirm_link.id = 'confirm-btn';
    confirm_link.classList.add('btn');
    confirm_link.classList.add('btn-info');
    confirm_link.setAttribute('onclick', 'add_proposed()');
    let nofirm_link = document.createElement('a');
    nofirm_link.innerHTML = 'No, add the exact reviewer I entered';
    nofirm_link.classList.add('btn');
    nofirm_link.classList.add('btn-info');
    nofirm_link.setAttribute('onclick', 'resume_invite()');
    let return_link = document.createElement('a');
    return_link.innerHTML = 'No, I want to return to the form';
    return_link.classList.add('btn');
    return_link.classList.add('btn-info');
    return_link.setAttribute('onclick', 'return_to_form()');

    modal_footer.appendChild(confirm_link);
    modal_footer.appendChild(nofirm_link);
    modal_footer.appendChild(return_link);

    modal_body.appendChild(span);
    modal.appendChild(modal_body);
    modal.appendChild(modal_footer);
    container.appendChild(modal);
    document.body.appendChild(container);
}


function gather_name() {
    // extract name from from for JSON
    let firstname_field = document.querySelector('#no_table_reviewer_first_name');
    let lastname_field = document.querySelector('#no_table_reviewer_last_name');
    let field_json = {'first_name': firstname_field.value, 'last_name': lastname_field.value};
    return field_json
}


function resume_invite() {
    // the proposed name was not the one the recommender wants. So proceed with the entered data
    unique = true;
    submit_btn_2.click();
}


function add_proposed() {
    // if the proposed name is the one the recommender wants, add it via AJAX call
    let checkboxes = document.querySelectorAll('.user-checkbox');
    let user_index = false;
    let user = 'false'; // this string is required, because index 0 equals false
    for (let i = 0; i < checkboxes.length; i++) {
        if (checkboxes[i].checked) {
            user_index = i;
        }
    }

    if (user_index != 'false') { user = user_json['users'][user_index]; }
    else {
        add_choose_note();
        return
    }

    let name_json = {'first_name': user['first_name'], 'last_name': user['last_name']};
    let review_duration_field = document.querySelector('#no_table_review_duration');
    let subject_field = document.querySelector('#no_table_subject');
    let message_field = document.querySelector('#no_table_message_ifr');
    let cc_field = document.querySelector('#no_table_cc');
    name_json['review_duration'] = review_duration_field.value;
    name_json['subject'] = subject_field.value;
    name_json['message'] = message_field.contentWindow.document.body.innerText;
    name_json['cc'] = cc_field.value;
    let queryString = window.location.search;
    let urlParams = new URLSearchParams(queryString);
    let recommId = urlParams.get('recommId');
    let new_stage = urlParams.get('new_stage');
    name_json['recommId'] = recommId;
    name_json['new_stage'] = new_stage;
    $.ajax({
        url: 'add_proposed_reviewer',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(name_json),
        success: function(response) {
            let current_url_stem = window.location.href.split('/recommender')[0];
            window.location.href = current_url_stem + '/recommender/reviewers?recommId=' + String(recommId);
        },
        error: function(error) {
            console.log('Error: ', error);
        }
    })
}


function return_to_form() {
    // close modal, return to form
    let modal_container = document.querySelector('#modal-container');
    modal_container.remove();
}


function only_one(checkbox) {
    // assures that only one checkbox is checked
    let checkboxes = document.querySelectorAll('.user-checkbox');
    for (let i = 0; i < checkboxes.length; i++) {
        if (checkboxes[i] != checkbox) {
            checkboxes[i].checked = false;
        }
    }
}


function add_choose_note() {
    // adds notification to make a choice before hitting add button
    let modal_footer = document.querySelector('.modal-footer2');
    let confirm_btn = modal_footer.querySelector('#confirm-btn');
    let note = document.createElement('div');
    note.classList.add('red');
    note.innerHTML = 'Please make a selection first.';
    if (!choose_note) {
        modal_footer.insertBefore(note, confirm_btn);
        choose_note = true;
    }
}