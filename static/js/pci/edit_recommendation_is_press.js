jQuery(document).ready(function() {
  jQuery(":submit[name=terminate]").prop(
    "disabled",
    !jQuery("#t_recommendations_no_conflict_of_interest").prop("checked")
  );
});
