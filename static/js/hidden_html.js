let hidden_html = document.querySelector('#hidden-html');
if (hidden_html) {
    // fix HTML string
    let lower = hidden_html.innerHTML.replace(/&lt;/g, '<');
    let greater = lower.replace(/&gt;/g, '>');
    let spaces = greater.replace(/&nbsp;/g, '');

    // hide text area form field
    let form_field = document.querySelector('#no_table_content');
    form_field.style.display = 'none';

    // replace with editable div that includes rendered HTML
    let parent = document.querySelector('#no_table_content__row .col-sm-9');
    let new_div = document.createElement('div');
    new_div.id = 'rendered-html';
    new_div.setAttribute('contenteditable', 'true')
    new_div.innerHTML = spaces;
    parent.appendChild(new_div);
}