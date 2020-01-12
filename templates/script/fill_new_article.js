jQuery(document).ready(function() {
  if (jQuery("#t_articles_picture_rights_ok").prop("checked")) {
    jQuery("#t_articles_uploaded_picture").prop("disabled", false);
  } else {
    jQuery("#t_articles_uploaded_picture").prop("disabled", true);
  }

  if (jQuery("#t_articles_already_published").prop("checked")) {
    jQuery("#t_articles_article_source__row").show();
  } else {
    jQuery("#t_articles_article_source__row").hide();
    jQuery(":submit").prop("disabled", true);
  }

  if (jQuery("#t_articles_already_published").length)
    jQuery(":submit").prop("disabled", false);

  if (jQuery("#t_articles_is_not_reviewed_elsewhere").prop("checked")) {
    jQuery("#t_articles_parallel_submission").prop("disabled", true);
  }

  if (
    (jQuery("#t_articles_is_not_reviewed_elsewhere").prop("checked") |
      jQuery("#t_articles_parallel_submission").prop("checked")) &
    jQuery("#t_articles_i_am_an_author").prop("checked")
  ) {
    jQuery(":submit").prop("disabled", false);
  } else {
    jQuery(":submit").prop("disabled", true);
  }

  jQuery("#t_articles_picture_rights_ok").change(function() {
    if (jQuery("#t_articles_picture_rights_ok").prop("checked")) {
      jQuery("#t_articles_uploaded_picture").prop("disabled", false);
    } else {
      jQuery("#t_articles_uploaded_picture").prop("disabled", true);
      jQuery("#t_articles_uploaded_picture").val("");
    }
  });

  jQuery("#t_articles_already_published").change(function() {
    if (jQuery("#t_articles_already_published").prop("checked")) {
      jQuery("#t_articles_article_source__row").show();
    } else {
      jQuery("#t_articles_article_source__row").hide();
    }
  });

  jQuery("#t_articles_is_not_reviewed_elsewhere").change(function() {
    if (jQuery("#t_articles_is_not_reviewed_elsewhere").prop("checked")) {
      jQuery("#t_articles_parallel_submission").prop("checked", false);
      jQuery("#t_articles_parallel_submission").prop("disabled", true);
    } else {
      jQuery("#t_articles_parallel_submission").prop("disabled", false);
    }
    if (
      (jQuery("#t_articles_is_not_reviewed_elsewhere").prop("checked") |
        jQuery("#t_articles_parallel_submission").prop("checked")) &
      jQuery("#t_articles_i_am_an_author").prop("checked")
    ) {
      jQuery(":submit").prop("disabled", false);
    } else {
      jQuery(":submit").prop("disabled", true);
    }
  });
  jQuery("#t_articles_i_am_an_author").change(function() {
    if (
      (jQuery("#t_articles_is_not_reviewed_elsewhere").prop("checked") |
        jQuery("#t_articles_parallel_submission").prop("checked")) &
      jQuery("#t_articles_i_am_an_author").prop("checked")
    ) {
      jQuery(":submit").prop("disabled", false);
    } else {
      jQuery(":submit").prop("disabled", true);
    }
  });
  jQuery("#t_articles_parallel_submission").change(function() {
    if (jQuery("#t_articles_parallel_submission").prop("checked")) {
      jQuery("#t_articles_is_not_reviewed_elsewhere").prop("checked", false);
      jQuery("#t_articles_is_not_reviewed_elsewhere").prop("disabled", true);
    } else {
      jQuery("#t_articles_is_not_reviewed_elsewhere").prop("disabled", false);
    }
    if (
      (jQuery("#t_articles_is_not_reviewed_elsewhere").prop("checked") |
        jQuery("#t_articles_parallel_submission").prop("checked")) &
      jQuery("#t_articles_i_am_an_author").prop("checked")
    ) {
      jQuery(":submit").prop("disabled", false);
    } else {
      jQuery(":submit").prop("disabled", true);
    }
  });
});
