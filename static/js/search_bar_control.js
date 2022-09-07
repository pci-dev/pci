// if there is an ongoing search, we need to change buttons and 
// input field visibility
var search_bar = document.querySelector('#w2p_keywords');
checkCookie();

user_type2field = {'reviewers': 'qy_reviewers', 'users': 'auth_user', 'recommenders': 'qy_recomm', 'articles': 'qy_art'}
if (search_bar != null) {
    // user_type on default/index cannot be determined in the same way
    try { 
        var user_type = get_user_type();
        setCookieUT(user_type); }
    catch {
        var user_type = getCookie('user_type');
    }
    if (search_bar.value != '') { ongoing_search(); }
    else { 
        result_counter_initial();
        initialise_simple_search();
     }
    remove_asterisks();
}


function get_user_type() {
    var first_column = document.querySelector('.web2py_htmltable > table col').id;
    return first_column.split('-')[0]
}


function initialise_simple_search() {
    // if the page is opened and no search is ongoing, initialise simple search
    var grid = document.querySelector('.web2py_grid');
    var advanced_search = grid.querySelector('#w2p_query_panel');
    var wconsole = grid.querySelector('.web2py_console');
    advanced_search.style.display = 'none';

    var simple_search_div = document.createElement('div');
    simple_search_div.id = 'simple-search';
    var input_field = document.createElement('input');
    input_field.classList.add('simple');
    input_field.classList.add('form-control');
    input_field.setAttribute('type', 'text');
    input_field.id = 'simple-search-input';

    var search_btn = document.createElement('input');
    search_btn.classList.add('btn');
    search_btn.classList.add('btn-default');
    search_btn.classList.add('add-btn');
    search_btn.id = 'simple-search-btn';
    search_btn.style.backgroundColor = '#93c54b';
    search_btn.setAttribute('type', 'button');
    search_btn.setAttribute('onclick', 'simple_search()');
    search_btn.setAttribute('value', 'SEARCH');
    
    var clear_btn = document.createElement('input');
    clear_btn.classList.add('btn');
    clear_btn.classList.add('btn-default');
    clear_btn.style.backgroundColor = '#393a35';
    clear_btn.setAttribute('type', 'button');
    clear_btn.id = 'simple-clear-btn';
    clear_btn.setAttribute('onclick', 'clear_simple_search()');
    clear_btn.setAttribute('value', 'Reset');

    simple_search_div.appendChild(input_field);
    simple_search_div.appendChild(clear_btn);    
    simple_search_div.appendChild(search_btn);
    grid.insertBefore(simple_search_div, wconsole);

    var switch_search_btn = document.querySelector('#switch-search-btn');
    if (switch_search_btn == null) {
        switch_search_btn = create_switch_search_btn('advanced');
        insertAfter(switch_search_btn, wconsole);
    }
    // also show the current search query in the simple search bar to avoid confusion
    //var simple_search_bar = document.querySelector('#simple-search-input');
    //simple_search_bar.value = search_bar.value;
    search_bar.value = '';

    setCookieST('simple');
}


function create_switch_search_btn(modus) {
    var switch_search_btn = document.createElement('input');
    switch_search_btn.classList.add('btn');
    switch_search_btn.classList.add('btn-default');
    switch_search_btn.id = 'switch-search-btn';
    switch_search_btn.style.backgroundColor = '#393a35';
    switch_search_btn.style.color = 'white';
    switch_search_btn.setAttribute('type', 'button');
    switch_search_btn.setAttribute('onclick', 'switch_search()');
    if (modus == 'advanced') { switch_search_btn.setAttribute('value', 'Advanced Search'); }
    else { switch_search_btn.setAttribute('value', 'Simple Search'); }

    return switch_search_btn
}


function removeURLParameter(url, parameter) {
    var urlparts = url.split('?');
    if (urlparts.length >= 2) {

        var prefix = encodeURIComponent(parameter) + '=';
        var pars = urlparts[1].split(/[&;]/g);

        for (var i = pars.length; i-- > 0;) {    
            if (pars[i].lastIndexOf(prefix, 0) !== -1) {  
                pars.splice(i, 1);
            }
        }

        return urlparts[0] + (pars.length > 0 ? '?' + pars.join('&') : '');
    }
    return url;
}


function insertAfter(newNode, existingNode) {
    existingNode.parentNode.insertBefore(newNode, existingNode.nextSibling);
}


function switch_search() {
    /* switch search (simple/advanced) and change switch button accordingly */
    var switch_search_btn = document.querySelector('#switch-search-btn');
    var advanced_search = document.querySelector('#w2p_query_panel');
    var simple_search_div = document.querySelector('#simple-search');
    if (switch_search_btn.value == 'Advanced Search') {
        switch_search_btn.setAttribute('value', 'Simple Search');
        advanced_search.style.display = 'flex';
        simple_search_div.style.display = 'none';
        setCookieST('advanced');
    }
    else {
        setCookieST('simple');
        try {
            simple_search_div.style.display = 'flex';
            switch_search_btn.setAttribute('value', 'Advanced Search');
        }
        catch {
            clear_simple_search();
        }
        advanced_search.style.display = 'none';
    }
}


function clear_simple_search() {
    var url = removeURLParameter(String(window.location), 'keywords');
    window.location = url;
}


function simple_search() {
    /* use hidden advanced search entities to perform simple search*/
    // get query
    setCookieST('simple');
    var search_term = document.querySelector('#simple-search-input').value;

    // create add all query 
    var search_statement = 'any contains "' + search_term + '"'

    // get the statement to the search field and trigger it
    var search_field = document.querySelector('#w2p_keywords');
    var search_form = document.querySelector('.web2py_console > form');
    search_form.style.display = 'none';
    search_field.value = search_statement;
    console.log('1');
    console.log(search_field.value);
    search_form.submit();
}


function ongoing_search() {
    // for an ongoing search, display the non-empty search bar
    var search_type = getCookie('search_type');
    if (search_type == 'simple') {
        initialise_simple_search();
        return
    }
    else {
        var search_bar = document.querySelector('.web2py_console > form');
        search_bar.style.display = 'flex';
        var simple_search_btn = create_switch_search_btn('simple');
        insertAfter(simple_search_btn, search_bar);
    }

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
    if (db_field == 'thematics') {
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


function add_all(field, regulator, search_name = false) {
    // get search term
    var search_field_all = document.querySelector('#w2p_value_all');
    var search_term = search_field_all.value;

    var regulator_field = field.parentElement.querySelector('select.form-control').value;
    if (regulator_field == 'not contains') {
        var prefix = 'not ';
    }
    else {
        var prefix = '';
    }

    var search_statement = prefix + 'any contains "' + search_term + '"';

    var search_field = document.querySelector('#w2p_keywords');

    if (regulator == 'new') {
        var search_form = document.querySelector('.web2py_console > form');
        search_form.style.display = 'flex';
        search_field.value = search_statement;
        console.log('2');
        console.log(search_field.value);
        search_form.submit();
    }
    else {
        search_field.value += ' ' + regulator + ' ' + search_statement;
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
        console.log('3');
        console.log(search_field.value);

        search_bar.submit();

    }
    var main_search_form = document.querySelector('.web2py_console > form');
    console.log('4');
    console.log(search_field.value);

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
    if (not_statement) {
        statement += 'not ' + select_field.value + ' contains "' + search_term + '"';
    }
    else {
        statement += select_field.value + ' contains "' + search_term + '"';
    }
    var main_search_input = main_search_form.querySelector('#w2p_keywords');
    main_search_input.value = statement;
    setCookieST('advanced');
    console.log('5');
    console.log(main_search_input.value);

    main_search_form.submit();
}


function getCookie(cname) {
    var name = cname + "=";
    var ca = document.cookie.split(';');
    for(var i = 0; i < ca.length; i++) {
      var c = ca[i];
      while (c.charAt(0) == ' ') {
        c = c.substring(1);
      }
      if (c.indexOf(name) == 0) {
        return c.substring(name.length, c.length);
      }
    }
    return "";
}


function setCookieST(cvalue) {
    document.cookie = 'search_type=' + cvalue + '; SameSite=None; Secure'
}


function setCookieUT(cvalue) {
    document.cookie = 'user_type=' + cvalue + '; SameSite=None; Secure'
}


function checkCookie() {
    var search_type = getCookie("search_type");
    if (search_type == "") { setCookieST('simple'); }
}
