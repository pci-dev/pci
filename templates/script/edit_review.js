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

