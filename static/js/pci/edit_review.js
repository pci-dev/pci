jQuery(document).ready(function() {
  let checkboxConflictInterest = document.getElementById("t_reviews_no_conflict_of_interest")
  if (checkboxConflictInterest.value == "on") {
    checkboxConflictInterest.checked = true
  }

  if (jQuery("#t_reviews_no_conflict_of_interest").prop("checked")) {
    jQuery(":submit").prop("disabled", false);
  } else {
    jQuery(":submit").prop("disabled", true);
  }
  jQuery("#t_reviews_no_conflict_of_interest").change(function() {
    if (jQuery("#t_reviews_no_conflict_of_interest").prop("checked")) {
      jQuery(":submit").prop("disabled", false);
    } else {
      jQuery(":submit").prop("disabled", true);
    }
  });

  // control enabling of submit button
  deactivate_submit_btn();
  setInterval(activate_submit_btn, 500);
});


function deactivate_submit_btn() {
  // deactivate submit button on page load
  let submit_btn = document.querySelector('#submit-btn');
  let save_btn = document.querySelector('#save-btn');
  submit_btn.setAttribute('disabled', '');
  save_btn.setAttribute('disabled', '');
};


function activate_submit_btn() {
  // activate submit button if review is provided as either text or file
  try {
    let tiny_mce = tinymce.get('t_reviews_review');
    let upload_file = document.querySelector('#t_reviews_review_pdf');
    let file_list = document.querySelector('#t_reviews_review_pdf__row .col-sm-9 > div > span > a');

    let submit_btn = document.querySelector('#submit-btn');
    let save_btn = document.querySelector('#save-btn');
    if (upload_file.value != '' || tiny_mce.getContent().length >= 8 || file_list) {
      submit_btn.removeAttribute('disabled');
      save_btn.removeAttribute('disabled');
    }
    else {
      submit_btn.setAttribute('disabled', '');
      save_btn.setAttribute('disabled', '');
    }
  }
  catch { }
};


$('input[name="save"],input[name="terminate"]').on('click', anonymousReviewerFunction);

function anonymousReviewerFunction(e) {
  const buttonName = e.target.name;

  if (document.getElementById('t_reviews_anonymously')?.checked) {
    return;
  }

  e.preventDefault();

  $('#anonymous-reviewer-confirm').modal('show')
  .on('click', '#confirm-dialog', function(){ 
    const anonymousDialogInput = document.getElementById('anonymous-dialog-input');
    anonymousDialogInput.value = buttonName;

    const form = document.getElementsByClassName('form-horizontal')[0];
    form.submit();
  });
  
  $('#cancel-dialog')
  .on('click',function(){ return; });
}
