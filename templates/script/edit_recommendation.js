jQuery(document).ready(function() {
  jQuery("#t_recommendations_no_conflict_of_interest").click(function() {
    jQuery(":submit[name=terminate]").prop(
      "disabled",
      !(
        jQuery("#t_recommendations_no_conflict_of_interest").prop("checked") &
        ($("#opinion_recommend").prop("checked") |
          $("#opinion_revise").prop("checked") |
          $("#opinion_reject").prop("checked"))
      )
    );
  });
  jQuery("input[type=radio][name=recommender_opinion]").change(function() {
    jQuery(":submit[name=terminate]").prop(
      "disabled",
      !(
        jQuery("#t_recommendations_no_conflict_of_interest").prop("checked") &
        ($("#opinion_recommend").prop("checked") |
          $("#opinion_revise").prop("checked") |
          $("#opinion_reject").prop("checked"))
      )
    );
  });
  jQuery(":submit[name=terminate]").prop(
    "disabled",
    !(
      jQuery("#t_recommendations_no_conflict_of_interest").prop("checked") &
      ($("#opinion_recommend").prop("checked") |
        $("#opinion_revise").prop("checked") |
        $("#opinion_reject").prop("checked"))
    )
  );
});
