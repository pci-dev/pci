jQuery("#t_articles_picture_rights_ok").change(function() {
    if (jQuery("#t_articles_picture_rights_ok").prop("checked")) {
        jQuery("#t_articles_uploaded_picture").prop("disabled", false);
    } else {
        jQuery("#t_articles_uploaded_picture").prop("disabled", true);
        jQuery("#t_articles_uploaded_picture").val("");
    }
});
