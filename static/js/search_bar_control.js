window.onload = function() {
    var add_btns = document.querySelectorAll('.add-btn');
    for (var i = 0; i < add_btns.length; i++) {
        add_btns[i].addEventListener('click', show_buttons);
    }

    var search_bar = document.querySelector('#w2p_keywords');
    if (search_bar.value != '') {
        show_buttons();
    }
}


function show_buttons() {
    /* when the ADD button is clicked, this function
    reveals the AND and OR buttons; then, it newly
    creates the NOT button, which does not come
    automatically from the Grid */
    var query_rows = document.querySelectorAll('.w2p_query_row');
    for (var i = 0; i < query_rows.length; i++) {
        var and_btn = query_rows[i].querySelector('.and-btn');
        and_btn.style.display = 'inline-block';
        var or_btn = query_rows[i].querySelector('.or-btn');
        or_btn.style.display = 'inline-block';
        var not_btn = document.createElement('input');
        not_btn.classList.add('not-btn');
        not_btn.classList.add('btn');
        not_btn.classList.add('btn-default');
        not_btn.setAttribute('onclick', 'add_not(this)');
        not_btn.setAttribute('type', 'button');
        not_btn.setAttribute('value', '+ NOT');
        or_btn.after(not_btn);
        var add_btn = query_rows[i].querySelector('.add-btn');
        add_btn.style.display = 'none';
    }

}


function add_not(not_field) {
    /* when the NOT button is clicked, take the argument
    from the input fields and add it to the search field
    with a regulator "not in" */
    var database_field = not_field.parentElement.previousSibling;
    var not_statement = ' and ' + database_field.value + ' != "';
    not_statement += not_field.parentElement.querySelector('input.string').value + '"';
    var search_bar = document.querySelector('#w2p_keywords');
    var current_keywords = search_bar.value;
    current_keywords += not_statement;
    search_bar.value = current_keywords;
}