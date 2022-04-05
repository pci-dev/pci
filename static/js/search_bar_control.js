window.onload = function() {
    var add_btn = document.querySelector('#add-btn');
    add_btn.addEventListener('click', show_buttons);
}


function show_buttons() {
    /* when the ADD button is clicked, this function
    reveals the AND and OR buttons; then, it newly
    creates the NOT button, which does not come
    automatically from the Grid */
    var and_btn = document.querySelector('#and-btn');
    and_btn.style.display = 'inline-block';
    var or_btn = document.querySelector('#or-btn');
    or_btn.style.display = 'inline-block';
    var not_btn = document.createElement('input');
    not_btn.id = 'not-btn';
    not_btn.classList.add('btn');
    not_btn.classList.add('btn-default');
    not_btn.setAttribute('onclick', 'add_not(this)');
    not_btn.setAttribute('type', 'button');
    not_btn.setAttribute('value', 'NOT');
    or_btn.after(not_btn);
}


function add_not(not_field) {
    /* when the NOT button is clicked, take the argument
    from the input fields and add it to the search field
    with a regulator "not in" */
    console.log('NOT')
}