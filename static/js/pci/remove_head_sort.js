// This piece of code removes faulty sorting behaviour in table headers,
// which is caused by our usage of the .represent function while creating
// the table contents.
let web2py_table = document.querySelector('.web2py_htmltable');
let label_to_wrong_field = {'Recommenders': 't_articles.title', 'Name': 'auth_user.id'};
let wrong_field_2_right_field = {'auth_user.id': 'auth_user.last_name'};
if (web2py_table) {
    let header_links = web2py_table.querySelectorAll('th > a');
    for (let i = 0; i < header_links.length; i++) {
        let label = header_links[i].innerHTML;
        let href = header_links[i].getAttribute('href');
        if (label in label_to_wrong_field) {
            let wrong_field = label_to_wrong_field[label];
            // replace sort functions
            if (wrong_field in wrong_field_2_right_field) {
                try {
                    let new_href = href.replace(wrong_field, wrong_field_2_right_field[wrong_field]);
                    header_links[i].setAttribute('href', new_href);
                } catch { }
            } 
            // remove sort functions
            else if (href.includes(wrong_field)) {
                header_links[i].removeAttribute('href');
                header_links[i].style.color = '#598398';
                header_links[i].style.textDecoration = 'none';
            }
    
        }

        
    }
}