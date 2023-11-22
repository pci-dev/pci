let confirmation_change_fields = ['#t_articles_status', '#t_recommendations_recommendation_state'];
let field_to_message = {'#t_articles_status': 'Are you sure you want to change the article status?',
                        '#t_recommendations_recommendation_state': 'Are you sure you want the change the recommendation state?'}

let status_fields = [];
let message_fields = [];

for (let i=0; i<confirmation_change_fields.length; i++) {
    one_button = document.querySelectorAll(confirmation_change_fields[i]);
    if (one_button.length > 0) {
        status_fields.push(one_button);
        message_fields.push(field_to_message[confirmation_change_fields[i]]);
    }
}

let confirmation_change_buttons = ['#submit_record__row .btn-success', '#do_recommend_article .btn-success',
                                   '#do_revise_article .btn-info', '#do_reject_article .btn-info',
                                   '#btn-send-back-decision', '#do_validate_article .btn-success',
                                   '#preprint-btn', '#remove-preprint-btn', '.modal-footer .confirm-mail-dialog', '#pre_submission_list']
let button_to_message = {'#submit_record__row .btn-success': 'fork',
                        '#do_recommend_article .btn-success': 'Are you sure you want to validate this recommendation?',
                        '#do_revise_article .btn-info': 'Are you sure you want to validate this request for revision?',
                        '#do_reject_article .btn-info': 'Are you sure you want to validate to reject this preprint?',
                        '#btn-send-back-decision': 'Are you sure you want to send back this decision to the recommender?', 
                        '#do_validate_article .btn-success': 'Are you sure you want to validate this submission?', 
                        '#preprint-btn': 'Are you sure you want to put the preprint in the "In need of reviewers" list"?',
                        '#remove-preprint-btn': 'Are you sure you want to remove the preprint from the "In need of reviewers" list"?',
                        '.modal-footer .confirm-mail-dialog': 'Are you sure you want to send this message and set the article as "not considered"?',
                        '#pre_submission_list': 'Are you sure you want to put the article in the presubmission list?'}

let status_buttons = [];
let message_buttons = [];
for (let i=0; i<confirmation_change_buttons.length; i++) {
    one_button = document.querySelectorAll(confirmation_change_buttons[i]);
    if (one_button.length > 0) {
        status_buttons.push(one_button);
        message_buttons.push(button_to_message[confirmation_change_buttons[i]]);
    }
}


if (status_fields.length > 0 || status_buttons.length > 0) {
    var modal = document.createElement('div');
    var modal_backdrop = document.createElement('div');
    var button_yes = document.createElement('span');
    var button_nope = document.createElement('span');
    var modal_body = document.createElement('div');
    var modal_footer = document.createElement('div');
    var prevent_or_fire = 'prevent';
}


if (status_fields.length > 0) {
    for (let i=0; i<status_fields.length; i++) {
        let status_field = status_fields[i];
        for (let j=0; j<status_field.length; j++) {
            let status_field_value = status_field[j].value;
            status_field[j].addEventListener("focus", function(event) {
                status_field_value = event.target.value;
            });
            
            create_modal('field', status_field[j]);
            modal_body.innerHTML = message_fields[i];

            status_field[j].addEventListener('change', function(event) {
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
                    status_field_value = event.target.value;
                })

                button_nope.addEventListener('click', function() {
                    // reject change and remove modal
                    modal.style.display = 'none';
                    modal_backdrop.style.display = 'none';
                    body.style.overflow = 'scroll';
                    event.target.value = status_field_value;
                })
            })
        }
    }
}


if (status_buttons.length > 0) {
    for (let i=0; i<status_buttons.length; i++) {
        let status_button = status_buttons[i];
        for (let j=0; j<status_button.length; j++) {
            create_modal('button', status_button[j]);

            status_button[j].addEventListener('click', function(event) {
                if (prevent_or_fire == 'prevent') {
                    event.preventDefault();

                    message = message_buttons[i];
                    if (message == 'fork') { multiple_choice_button(); }
                    else { modal_body.innerHTML = message; }

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
                        status_button[j].click();
                    })

                    button_nope.addEventListener('click', function() {
                        // reject change and remove modal
                        modal.style.display = 'none';
                        modal_backdrop.style.display = 'none';
                        body.style.overflow = 'scroll';
                    })
                }
                else { prevent_or_fire == 'prevent'; }
            })
        }
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


function multiple_choice_button() {
    let recommend = document.querySelector('#opinion_recommend');
    let recommend_private = document.querySelector('#opinion_recommend_private');
    let revision = document.querySelector('#opinion_revise');
    let reject = document.querySelector('#opinion_reject');

    if (recommend?.checked || recommend_private?.checked) { modal_body.innerHTML = 'Are you sure you want to recommend the preprint?'; }
    if (revision.checked) { modal_body.innerHTML = 'Are you sure you want to request a revision?'; }
    if (reject.checked) { modal_body.innerHTML = 'Are you sure you want to reject the preprint?'; }

    return
}
