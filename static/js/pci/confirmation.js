let confirmation_change_fields = ['#t_articles_status', '#t_recommendations_recommendation_state'];
let field_to_message = {'#t_articles_status': 'Are you sure you want to change the article status?',
                        '#t_recommendations_recommendation_state': 'Are you sure you want the change the recommendation state?'}

let status_field = false;
let message_field = false;

for (let i=0; i<confirmation_change_fields.length; i++) {
    status_field = document.querySelector(confirmation_change_fields[i]);
    message_field = field_to_message[confirmation_change_fields[i]];
}

let confirmation_change_buttons = ['#submit_record__row .btn-success']
let button_to_message = {'#submit_record__row .btn-success': 'fork'}

let status_button = false;
let message_button = false;
for (let i=0; i<confirmation_change_buttons.length; i++) {
    status_button = document.querySelector(confirmation_change_buttons[i]);
    message_button = button_to_message[confirmation_change_buttons[i]];
}


if (status_field || status_button) {
    var modal = document.createElement('div');
    var modal_backdrop = document.createElement('div');
    var button_yes = document.createElement('span');
    var button_nope = document.createElement('span');
    var modal_body = document.createElement('div');
    var prevent_or_fire = 'prevent';
}



if (status_field) {
    let status_field_value = status_field.value;
    status_field.addEventListener("focus", function(event) {
        status_field_value = event.target.value;
    });
    
    create_modal('field', status_field);
    modal_body.innerHTML = message_field;

    status_field.addEventListener('change', function(event) {
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


if (status_button) {
    create_modal('button', status_button);

    status_button.addEventListener('click', function(event) {
        console.log('in the click')
        console.log(prevent_or_fire)
        if (prevent_or_fire == 'prevent') {
            event.preventDefault(); 
        
            message = message_button;
            if (message == 'fork') { multiple_choice_button(); }

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
        }
        else { prevent_or_fire == 'prevent'; }
    })
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
    
        let modal_footer = document.createElement('div');
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
    let revision = document.querySelector('#opinion_revise');
    let reject = document.querySelector('#opinion_reject');

    if (recommend.checked) { modal_body.innerHTML = 'Are you sure you want to recommend the preprint?'; }
    if (revision.checked) { modal_body.innerHTML = 'Are you sure you want to request a revision?'; }
    if (reject.checked) { modal_body.innerHTML = 'Are you sure you want to reject the preprint?'; }

    return
}