let status_field = document.querySelector('#t_articles_status');
let status_field_value = status_field.value;

status_field.addEventListener("focus", function(event) {
    status_field_value = event.target.value;
  });

if (status_field) {
    // create confirmation modal
    let modal = document.createElement('div');
    modal.id = "confirm-change-modal";
    modal.classList.add('modal');
    modal.classList.add('fade');
    modal.classList.add('in');
    modal.setAttribute('role', 'dialog');
    modal.style.paddingRight = '0px';

    let modal_body = document.createElement('div');
    modal_body.classList.add('modal-body');
    modal_body.innerHTML = 'Are you sure you want to change the article status?';

    let modal_footer = document.createElement('div');
    modal_footer.classList.add('modal-footer');

    let button_yes = document.createElement('span');
    button_yes.classList.add('btn');
    button_yes.classList.add('btn-info');
    button_yes.setAttribute('data-dismiss', 'modal');
    button_yes.setAttribute('type', 'button');
    button_yes.innerHTML = 'Yes'

    let button_nope = document.createElement('span');
    button_nope.classList.add('btn');
    button_nope.classList.add('btn-default');
    button_nope.setAttribute('data-dismiss', 'modal');
    button_nope.setAttribute('type', 'button');
    button_nope.innerHTML = 'No';

    modal_footer.appendChild(button_yes);
    modal_footer.appendChild(button_nope);

    modal.appendChild(modal_body);
    modal.appendChild(modal_footer);

    let modal_backdrop = document.createElement('div');
    modal_backdrop.classList.add('modal-backdrop');
    modal_backdrop.classList.add('fade');
    modal_backdrop.classList.add('in');

    document.body.appendChild(modal);

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
