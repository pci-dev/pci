
var form = document.querySelector('form');
var years_field;
if (form) {
    years_field = form.querySelector('#t_articles_article_year__row');
}
if (years_field) {
    shove_manager_fields(form, years_field);
}

function shove_manager_fields(form, years_field) {
  // shove extra fields to the correct position
  let manager_label = form.querySelector('#t_articles_manager_label__row');
  form.insertBefore(manager_label, years_field);

  let manager_checks = form.querySelectorAll('.manager_checks');
  for (let i = 0; i < manager_checks.length; i++) {
    let manager_row = manager_checks[i].parentNode.parentNode.parentNode.parentNode;
    form.insertBefore(manager_row, years_field);
  }
}
function check_checkboxes() {
  // check if all checkboxes are checked, and if they are, prompt user
  let checkboxes = document.querySelectorAll('.manager_checks');
  for (let i = 0; i < checkboxes.length; i++) {
    if (checkboxes[i].checked == false) { return }
  }
  let alert = window.alert('Submission impossible because all managers are also co-authors. Please contact the managing board at contact@xxx.peercommunityin.org')
  for (let i = 0; i < checkboxes.length; i++) {
    checkboxes[i].checked = false;
  }
}