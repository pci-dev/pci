var add_btns = document.querySelectorAll('.add-btn');
for (var i = 0; i < add_btns.length; i++) {
    add_btns[i].addEventListener('click', show_buttons);
}

var search_bar = document.querySelector('#w2p_keywords');

if (search_bar != null && search_bar.value != '') { show_buttons(); }
else { result_counter_initial(); }

remove_asterisks();
user_type2field = {'reviewers': 'qy_reviewers', 'users': 'auth_user'}


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
    var select_field = document.querySelector('#w2p_query_fields');
    if (select_field.value == 'all') {
        add_all(not_field, 'and', true);
    }
    else if (select_field.value == 'thematics') {
        add_thematics('and', true)
    }
    else {
        var not_statement = ' and ' + select_field.value + ' != "';
        not_statement += not_field.parentElement.querySelector('input.form-control').value + '"';
        var search_bar = document.querySelector('#w2p_keywords');
        var current_keywords = search_bar.value;
        current_keywords += not_statement;
        search_bar.value = current_keywords;
    }
}


function add_all(field, regulator, not_statement = false) {
    /* when All fields is chosen, take the argument
    from the input fields, concatenate all possible search fields,
    and add them to the search field with OR */
    // get search term
    var search_field_all = document.querySelector('#w2p_value_all');
    var search_term = search_field_all.value;

    // get all search options and create statement:
    var options = document.querySelectorAll('#w2p_query_fields option');
    if (not_statement) {
        var inner_regulator = '!=';
        var inner_logic = 'and';
    }
    else { 
        var inner_regulator = 'contains'; 
        var inner_logic = 'or';
    }
    var search_statement = '';
    for (var i = 0; i < options.length; i++) {
        if (options[i].value != 'all' && options[i].style.display != 'none') {
            search_statement += options[i].value + ' ' + inner_regulator + ' "' + search_term + '" ' + inner_logic + ' ';
        }
    }

    // get the statement to the search field
    var search_field = document.querySelector('#w2p_keywords');
    if (regulator == 'new') {
        search_field.value = search_statement.substring(0,search_statement.length-4);
    }
    else {
        search_field.value += ' ' + regulator + ' ' + search_statement.substring(0,search_statement.length-4);
    }
}


function result_counter_initial() {
    var result_count = document.querySelector('.web2py_counter').innerHTML;
    document.querySelector('.web2py_counter').innerHTML = result_count.replace(' found', '');
}


function remove_asterisks() {
    var options = document.querySelectorAll('#w2p_query_fields > option');
    if (options != null) {
        for (var i = 0; i < options.length; i++) {
            var label = options[i].innerHTML;
            if (label.includes('*')) {
                options[i].innerHTML = label.replace('*', '');
            }
        }
    }
}


function add_thematics(user_type, regulator, not_statement = false) {
    /* when Thematic Fields is chosen, choose the argument
    from the new dropdown, but not from the input field */
    // get thematic search term
    var drop_field_thematics = document.querySelector('#w2p_field_thematics > .form-control');
    var thematic = drop_field_thematics.value;

    var user_field = user_type2field[user_type];

    // special case of not statement
    if (not_statement) { var inner_regulator = '!='; }
    else { var inner_regulator = 'contains'}

    var search_statement = user_field + '.thematics ' + inner_regulator +' "' + thematic + '"';

    // get the statement to the search field
    var search_field = document.querySelector('#w2p_keywords');
    if (regulator == 'new') { search_field.value = search_statement; }
    else { search_field.value += ' ' + regulator + ' ' + search_statement; }
}
