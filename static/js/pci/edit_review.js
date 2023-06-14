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
  activate_conditions_for_submission();
});


function deactivate_submit_btn() {
  // deactivate submit button on page load
  let submit_btn = document.querySelector('#submit-btn');
  submit_btn.setAttribute('disabled', '');

  // check if a review already exists as a saved version
  setTimeout( function() { 
    activate_submit_btn(); 
  }, 1000);
};


function activate_conditions_for_submission() {
  // set event listeners to monitor if review was provided by user
  setTimeout( function() {
    // event of review provision in text field
    let text_frame = document.querySelector('#t_reviews_review_ifr');
    let iframe_doc = text_frame.contentDocument || text_frame.contentWindow.document;
    let ee = iframe_doc.querySelector('body');
    ee.addEventListener('input', activate_submit_btn);

    // event of review file upload
    let upload_file = document.querySelector('#t_reviews_review_pdf');
    upload_file.addEventListener('change', activate_submit_btn);
  }, 1000);

};


function activate_submit_btn() {
  // activate submit button if review is provided as either text or file
  let tiny_mce = tinymce.get('t_reviews_review');
  let upload_file = document.querySelector('#t_reviews_review_pdf');

  let submit_btn = document.querySelector('#submit-btn');
  if (upload_file.value != '' || tiny_mce.getContent() != '') {
    submit_btn.removeAttribute('disabled');
  }
  else {
    submit_btn.setAttribute('disabled', '');
  }
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
