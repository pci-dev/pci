jQuery(document).ready(function() {
  if (
    jQuery("#no_conflict_of_interest").prop("checked") &
    jQuery("#due_time").prop("checked")
  ) {
    jQuery(":submit").prop("disabled", false);
  } else {
    jQuery(":submit").prop("disabled", true);
  }

  jQuery("#no_conflict_of_interest").change(function() {
    if (
      jQuery("#no_conflict_of_interest").prop("checked") &
      jQuery("#due_time").prop("checked")
    ) {
      jQuery(":submit").prop("disabled", false);
    } else {
      jQuery(":submit").prop("disabled", true);
    }
  });

  jQuery("#due_time").change(function() {
    if (
      jQuery("#no_conflict_of_interest").prop("checked") &
      jQuery("#due_time").prop("checked")
    ) {
      jQuery(":submit").prop("disabled", false);
    } else {
      jQuery(":submit").prop("disabled", true);
    }
  });
});
