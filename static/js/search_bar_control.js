// if there is an ongoing search, we need to change buttons and 
// input field visibility
var search_bar = document.querySelector('#w2p_keywords');
var user_types_without_any = ['auth_user', 'mail_templates', 't_articles', 'qy_art', 'mail_queue', 'v_article']

if (search_bar != null) {
    var user_type = get_user_type();
    if (user_type != undefined) {
        setCookieUT(user_type);
    }
    else {
        var user_type = getCookie('user_type');
    }

    if (search_bar.value != '') {
        ongoing_search();
    } else {
        result_counter_initial();
        initialise_simple_search();
        let search_type = getSearchType().value;
        if (search_type == 'advanced') {
            switch_search();
        }
    }
    remove_asterisks();
    set_onclick_events();
}

function set_onclick_events() {
    // on a search page we need onclick events to trigger the searches on enter key
    // first, the simple search
    var simple_search_input = document.querySelector('#simple-search-input');
    if (simple_search_input) {
        simple_search_input.addEventListener('keypress', function(event) {
            let key = event.which;
            if (key == 13) {
                simple_search();
            }
        })
    }

    // next, the advanced search fields. This is more tricky, as there are several
    var input_fields = document.querySelectorAll('input.form-control');
    for (var i = 0; i < input_fields.length; i++) {
        if (input_fields[i].id != 'w2p_keywords' && input_fields[i].id != 'simple-search-input') {
            let input_field = input_fields[i];
            input_field.addEventListener('keypress', function(event) {
                let key = event.which;
                if (key == 13) {
                    let new_btn = input_field.parentElement.querySelector('.add-btn');
                    new_search(new_btn);
                }
            })
        }
    }
}

function get_user_type() {
    var all_columns = document.querySelectorAll('.web2py_htmltable > table col');
    for (var i = 0; i < all_columns.length; i++) {
        if (all_columns[i].id != '') {
            return all_columns[i].id.split('-')[0]
        }
    }
}

function initialise_simple_search() {
    // if the page is opened and no search is ongoing, initialise simple search
    var grid = document.querySelector('.web2py_grid');
    var advanced_search = grid.querySelector('#w2p_query_panel');
    var wconsole = grid.querySelector('.web2py_console');
    var possible_form = grid.querySelector('.web2py_console > form');
    possible_form.style.display = 'none';
    advanced_search.style.display = 'none';

    var simple_search_div = document.createElement('div');
    simple_search_div.id = 'simple-search';
    var input_field = document.createElement('input');
    input_field.classList.add('simple');
    input_field.classList.add('form-control');
    input_field.setAttribute('type', 'text');
    input_field.id = 'simple-search-input';
    var clear_btn = document.createElement('input');
    clear_btn.classList.add('btn');
    clear_btn.classList.add('btn-default');
    clear_btn.style.backgroundColor = '#393a35';
    clear_btn.setAttribute('type', 'button');
    clear_btn.id = 'simple-clear-btn';
    clear_btn.setAttribute('onclick', 'clear_simple_search()');
    clear_btn.setAttribute('value', 'Reset');

    var search_btn = document.createElement('input');
    search_btn.classList.add('btn');
    search_btn.classList.add('btn-default');
    search_btn.classList.add('add-btn');
    search_btn.id = 'simple-search-btn';
    search_btn.style.backgroundColor = '#93c54b';
    search_btn.setAttribute('type', 'button');
    search_btn.setAttribute('onclick', 'simple_search()');
    search_btn.setAttribute('value', 'SEARCH');

    simple_search_div.appendChild(input_field);
    simple_search_div.appendChild(search_btn);
    simple_search_div.appendChild(clear_btn);
    grid.insertBefore(simple_search_div, wconsole);

    var switch_search_btn = document.querySelector('#switch-search-btn');
    if (switch_search_btn == null) {
        switch_search_btn = create_switch_search_btn('advanced');
        insertAfter(switch_search_btn, wconsole);
    }
    search_bar.value = '';

    setSearchType('simple');
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
    if (modus == 'advanced') {
        switch_search_btn.setAttribute('value', 'Advanced Search');
    } else {
        switch_search_btn.setAttribute('value', 'Simple Search');
    }

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
        setSearchType('advanced');
    } else {
        setSearchType('simple');
        try {
            simple_search_div.style.display = 'flex';
            switch_search_btn.setAttribute('value', 'Advanced Search');
        } catch {
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
    setSearchType('simple');
    var search_term = document.querySelector('#simple-search-input').value;

    // create add all query (some searches have "any" field, others do not)
    if (user_types_without_any.includes(user_type)) {
        var search_statement = search_term;
    } else {
        var search_statement = 'any contains "' + search_term + '"';
    }

    // get the statement to the search field and trigger it
    var search_field = document.querySelector('#w2p_keywords');
    var search_form = document.querySelector('.web2py_console > form');
    search_form.style.display = 'none';
    search_field.value = search_statement;

    search_form.submit();
}

function ongoing_search() {
    // for an ongoing search, display the non-empty search bar
    var search_type = getSearchType().value;
    if (search_type == 'simple') {
        initialise_simple_search();
        return
    } else {
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
        and_btn.setAttribute('onclick', 'add_to_search(this)');
        // add new options to form control
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
    // finally, create new onclick events for the ADD buttons
    var input_fields = document.querySelectorAll('input.form-control');
    for (var i = 0; i < input_fields.length; i++) {
        if (input_fields[i].id != 'w2p_keywords' && input_fields[i].id != 'simple-search-input') {
            let input_field = input_fields[i];
            input_field.addEventListener('keypress', function(event) {
                let key = event.which;
                if (key == 13) {
                    let new_btn = input_field.nextSibling;
                    add_to_search(new_btn);
                }
            })
        }
    }
}

function add_to_search(input_field) {
    // first get db field
    var db_field = document.querySelector('#w2p_query_fields').value;

    // then get regulator
    var regulator_whole = input_field.parentElement.querySelector('select.form-control').value;
    var regulator = regulator_whole.split(' ')[0];

    // lastly get search term
    var search_term = get_search_term(input_field);

    // create statement
    if (regulator == 'not') {
        var statement = ' and not ';
    } else {
        var statement = ' ' + regulator + ' ';
    }
    statement += db_field;
    if (regulator == 'not') {
        statement += ' contains "';
    } else {
        statement += ' contains "';
    }
    statement += search_term + '"';

    // add statement to search bar
    var search_bar = document.querySelector('#w2p_keywords');
    search_bar.value += statement;
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

function get_search_term(input_field) {
    var search_form = input_field.parentElement;

    var search_term = search_form.querySelector('input.form-control');
    if (!search_term) {
	search_term = search_form.querySelectorAll('select.form-control')[1];
    }

    return search_term.value;
}

function new_search(input_field) {
    // make search bar visible
    var main_search_form = document.querySelector('.web2py_console > form');
    main_search_form.style.display = 'flex';

    // get regulator (contains/not contains)
    var regulator = input_field.parentElement.querySelector('select.form-control').value;
    if (regulator == 'contains' || regulator == 'and contains') {
        var not_statement = false;
    } else {
        var not_statement = true;
    }

    // get search term
    var search_term = get_search_term(input_field);

    var statement = '';
    var select_field = document.querySelector('#w2p_query_fields');
    if (not_statement) {
        statement += 'not ' + select_field.value + ' contains "' + search_term + '"';
    } else {
        statement += select_field.value + ' contains "' + search_term + '"';
    }
    var main_search_input = main_search_form.querySelector('#w2p_keywords');
    main_search_input.value = statement;
    setSearchType('advanced');
    main_search_form.submit();
}

function getCookie(cname) {
    var name = cname + "=";
    var ca = document.cookie.split(';');
    for (var i = 0; i < ca.length; i++) {
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

function setSearchType(cvalue) {
    getSearchType().value = cvalue;
}

function setCookieUT(cvalue) {
    document.cookie = 'user_type=' + cvalue + '; SameSite=None; Secure'
}

function getSearchType() {
    var search_type = document.querySelector('input[name="search_type"]');
    if (!search_type) {
        search_type = document.createElement("input");
        search_type.setAttribute("name", "search_type");
        search_type.setAttribute("type", "hidden");
        search_type.value = "simple";
        document.forms[0].appendChild(search_type);
    }
    return search_type;
}
