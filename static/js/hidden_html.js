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
    new_div.id = 'no_table_content_fake';
    //new_div.classList.add('form-control');
    //new_div.classList.add('text');
    new_div.setAttribute('contenteditable', 'true')
    //new_div.setAttribute('name', 'content')
    new_div.innerHTML = spaces;
    parent.appendChild(new_div);

    //let form_submit_btn = document.querySelector('#submit_record__row .btn');
    let edit_form = document.querySelector('.form-horizontal');
    edit_form.addEventListener('submit', function(event){
        event.preventDefault();
        let fake_field = document.querySelector('#no_table_content_fake');
        let true_field = document.querySelector('#no_table_content');
        true_field.innerHTML = fake_field.innerHTML;
        //console.log(fake_field.innerHTML);
        event.target.submit();
    })

}
