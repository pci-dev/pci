var submit_btn_2 = document.querySelector('#submit_record__row input');
var unique = false;

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
    $.ajax({
        url: 'check_reviewer_name',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(name_json),
        success: function(response) {
            let success = response['success'];
            if (success) {
                create_question_modal(response);
            }
            else {
                unique = true;
                submit_btn_2.click();
            }
        },
        error: function(error) {
            console.log('uh oh: ', error);
        }
    })

}

function create_question_modal(user_json) {
    console.log(user_json);
    let container = document.createElement('div');
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
    span.innerHTML = 'We found that this name is already in our reviewer database. Is this the person you are looking for?<br><br>';
    span.innerHTML += String(user_json['first_name']) + ' ';
    span.innerHTML += String(user_json['last_name']) + ' ';
    span.innerHTML += '(' + String(user_json['email']) + '), ';
    if (String(user_json['institution']) != 'null') { span.innerHTML += 'institution: ' + String(user_json['institution']) + ', '; }
    if (String(user_json['laboratory']) != 'null') { span.innerHTML += 'laboratory: ' + String(user_json['laboratory']) + ', '; }
    if (String(user_json['country']) != 'null') { span.innerHTML += 'country: ' + String(user_json['country']); }

    let modal_footer = document.createElement('div');
    modal_footer.classList.add('modal-footer');
    let confirm_link = document.createElement('a');
    confirm_link.innerHTML = 'Yes, please add that reviewer';
    confirm_link.classList.add('btn');
    confirm_link.classList.add('btn-info');
    confirm_link.setAttribute('onclick', 'add_proposed('+ user_json['first_name'] + ', ' + user_json['last_name'] +')');
    let nofirm_link = document.createElement('a');
    nofirm_link.innerHTML = 'No, please add the exact reviewer I entered';
    nofirm_link.classList.add('btn');
    nofirm_link.classList.add('btn-info');
    nofirm_link.setAttribute('onclick', 'resume_invite()');
    modal_footer.appendChild(confirm_link);
    modal_footer.appendChild(nofirm_link);

    modal_body.appendChild(span);
    modal.appendChild(modal_body);
    modal.appendChild(modal_footer);
    container.appendChild(modal);
    document.body.appendChild(container);
}


function gather_name() {
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