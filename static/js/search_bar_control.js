// if there is an ongoing search, we need to change buttons and 
// input field visibility
var search_bar = document.querySelector('#w2p_keywords');
if (search_bar.value != '') { ongoing_search(); }
else { result_counter_initial(); }

remove_asterisks();
user_type2field = {'reviewers': 'qy_reviewers', 'users': 'auth_user'}


function ongoing_search() {
    // for an ongoing search, display the non-empty search bar
    var search_bar = document.querySelector('.web2py_console > form');
    search_bar.style.display = 'flex';

    // adapt buttons and form controls for ongoing search
    var query_rows = document.querySelectorAll('.w2p_query_row');
    for (var i = 0; i < query_rows.length; i++) {
        // change display/behaviour of add button
        var and_btn = query_rows[i].querySelector('.add-btn');
        and_btn.style.display = 'inline-block';
        and_btn.style.backgroundColor = 'black';
        and_btn.style.color = 'white';
        and_btn.value = 'ADD';
        if (query_rows[i].id == 'w2p_field_thematics') {
            and_btn.setAttribute('onclick', 'add_thematics("' + and_btn.getAttribute('onclick').split('"')[1] + '", "and", false)');
            continue;
        }
        and_btn.setAttribute('onclick', 'add_to_search(this)');
        // add new options to form control (not for thematics)
        var form_controls = query_rows[i].querySelector('select.form-control');
        form_controls.innerHTML = '';
        var and_contains = document.createElement('option');
        and_contains.value = 'and contains';
        and_contains.innerHTML = 'and contains';
        form_controls.appendChild(and_contains);
        var or_contains = document.createElement('option');
        or_contains.value = 'or contains';
        or_contains.innerHTML = 'or contains';
        form_controls.appendChild(or_contains);
        var not_contains = document.createElement('option');
        not_contains.value = 'not contains';
        not_contains.innerHTML = 'not contains';
        form_controls.appendChild(not_contains);
    }
}


function add_to_search(input_field) {
    // first get db field
    var db_field = document.querySelector('#w2p_query_fields').value;

    // then get regulator
    var regulator_whole = input_field.parentElement.querySelector('select.form-control').value;
    var regulator = regulator_whole.split(' ')[0];

    // lastly get search term
    var search_term = input_field.parentElement.querySelector('input.form-control').value;

    if (db_field == 'all') {
        add_all(input_field, regulator);
        return
    }
    else if (db_field == 'thematics') {
        add_thematics();
    }

    // create statement
    if (regulator == 'not') { var statement = ' and not '; }
    else { var statement = ' ' + regulator + ' '; }
    statement += db_field;
    if (regulator == 'not') { statement += ' contains "'; }
    else { statement += ' contains "'; }
    statement += search_term + '"';

    // add statement to search bar
    var search_bar = document.querySelector('#w2p_keywords');
    search_bar.value += statement;

}


function add_all(field, regulator) {
    /* when All fields is chosen, take the argument
    from the input fields, concatenate all possible search fields,
    and add them to the search field with OR */
    // get search term
    var search_field_all = document.querySelector('#w2p_value_all');
    var search_term = search_field_all.value;

    // get all search options and create statement:
    var search_statement = '';
    var regulator_field = field.parentElement.querySelector('select.form-control').value;
    if (regulator_field == 'not contains') {
        var prefix = 'not ';
        var inner_regulator = 'contains';
        var inner_logic = 'and';
    }
    else {
        var prefix = '';
        var inner_regulator = 'contains';
        var inner_logic = 'or';
    }

    var options = document.querySelectorAll('#w2p_query_fields option');
    
    for (var i = 0; i < options.length; i++) {
        if (options[i].value != 'all' && options[i].value != 'thematics' && options[i].style.display != 'none') {
            search_statement += prefix + options[i].value + ' ' + inner_regulator + ' "' + search_term + '" ' + inner_logic + ' ';
        }
    }

    // get the statement to the search field
    var search_field = document.querySelector('#w2p_keywords');
    if (regulator == 'new') {
        var search_form = document.querySelector('.web2py_console > form');
        search_form.style.display = 'flex';
        search_field.value = search_statement.substring(0,search_statement.length-4);
        var main_search_form = document.querySelector('.web2py_console > form');
        main_search_form.submit();
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

    if (regulator == 'new') {
        var search_bar = document.querySelector('.web2py_console > form');
        search_bar.style.display = 'flex';
    }
    var main_search_form = document.querySelector('.web2py_console > form');
    main_search_form.submit();
}


function new_search(input_field) {
    // make search bar visible
    var main_search_form = document.querySelector('.web2py_console > form');
    main_search_form.style.display = 'flex';

    // get regulator (contains/not contains)
    var regulator = input_field.parentElement.querySelector('select.form-control').value;
    if (regulator == 'contains') { var not_statement = false; }
    else { var not_statement = true; }

    // get search term
    var search_term = input_field.parentElement.querySelector('input.form-control').value;

    var statement = '';
    var select_field = document.querySelector('#w2p_query_fields');
    if (select_field.value == 'all') {
        add_all(input_field, 'new');
    }
    else {
        if (not_statement) {
            statement += 'not ' + select_field.value + ' contains "' + search_term + '"';
        }
        else {
            statement += select_field.value + ' contains "' + search_term + '"';
        }
        var main_search_input = main_search_form.querySelector('#w2p_keywords');
        main_search_input.value = statement;
        main_search_form.submit();
    }
}