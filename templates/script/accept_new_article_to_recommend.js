jQuery(document).ready(function() {
  if (
    jQuery("#no_conflict_of_interest").prop("checked") &
    jQuery("#interesting").prop("checked") &
    jQuery("#invitations").prop("checked") &
    jQuery("#ten_days").prop("checked") &
    jQuery("#recomm_text").prop("checked") &
    jQuery("#commitments").prop("checked")
  ) {
    jQuery(":submit").prop("disabled", false);
  } else {
    jQuery(":submit").prop("disabled", true);
  }
  jQuery("#no_conflict_of_interest").change(function() {
    if (
      jQuery("#no_conflict_of_interest").prop("checked") &
      jQuery("#interesting").prop("checked") &
      jQuery("#invitations").prop("checked") &
      jQuery("#ten_days").prop("checked") &
      jQuery("#recomm_text").prop("checked") &
      jQuery("#commitments").prop("checked")
    ) {
      jQuery(":submit").prop("disabled", false);
    } else {
      jQuery(":submit").prop("disabled", true);
    }
  });
  jQuery("#interesting").change(function() {
    if (
      jQuery("#no_conflict_of_interest").prop("checked") &
      jQuery("#interesting").prop("checked") &
      jQuery("#invitations").prop("checked") &
      jQuery("#ten_days").prop("checked") &
      jQuery("#recomm_text").prop("checked") &
      jQuery("#commitments").prop("checked")
    ) {
      jQuery(":submit").prop("disabled", false);
    } else {
      jQuery(":submit").prop("disabled", true);
    }
  });
  jQuery("#invitations").change(function() {
    if (
      jQuery("#no_conflict_of_interest").prop("checked") &
      jQuery("#interesting").prop("checked") &
      jQuery("#invitations").prop("checked") &
      jQuery("#ten_days").prop("checked") &
      jQuery("#recomm_text").prop("checked") &
      jQuery("#commitments").prop("checked")
    ) {
      jQuery(":submit").prop("disabled", false);
    } else {
      jQuery(":submit").prop("disabled", true);
    }
  });
  jQuery("#ten_days").change(function() {
    if (
      jQuery("#no_conflict_of_interest").prop("checked") &
      jQuery("#interesting").prop("checked") &
      jQuery("#invitations").prop("checked") &
      jQuery("#ten_days").prop("checked") &
      jQuery("#recomm_text").prop("checked") &
      jQuery("#commitments").prop("checked")
    ) {
      jQuery(":submit").prop("disabled", false);
    } else {
      jQuery(":submit").prop("disabled", true);
    }
  });
  jQuery("#recomm_text").change(function() {
    if (
      jQuery("#no_conflict_of_interest").prop("checked") &
      jQuery("#interesting").prop("checked") &
      jQuery("#invitations").prop("checked") &
      jQuery("#ten_days").prop("checked") &
      jQuery("#recomm_text").prop("checked") &
      jQuery("#commitments").prop("checked")
    ) {
      jQuery(":submit").prop("disabled", false);
    } else {
      jQuery(":submit").prop("disabled", true);
    }
  });
  jQuery("#commitments").change(function() {
    if (
      jQuery("#no_conflict_of_interest").prop("checked") &
      jQuery("#interesting").prop("checked") &
      jQuery("#invitations").prop("checked") &
      jQuery("#ten_days").prop("checked") &
      jQuery("#recomm_text").prop("checked") &
      jQuery("#commitments").prop("checked")
    ) {
      jQuery(":submit").prop("disabled", false);
    } else {
      jQuery(":submit").prop("disabled", true);
    }
  });
});
