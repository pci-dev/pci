jQuery(document).ready(function() {
  let checkboxConflictInterest = document.getElementById("t_reviews_no_conflict_of_interest")
  console.log(checkboxConflictInterest)
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
});

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
