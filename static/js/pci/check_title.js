function checkTitle(){
    if(jQuery("#no_table_report_stage").val() === "STAGE 1"){
        jQuery("#no_table_title__row").show();
        jQuery("#submit_record__row .btn-primary").prop("disabled", false);
    }
    else if (jQuery("#no_table_report_stage").val() === "STAGE 2") {
        jQuery("#no_table_title__row").hide();
        jQuery("#submit_record__row .btn-primary").prop("disabled", false);
    } else {
      jQuery("#no_table_title__row").hide();
      jQuery("#submit_record__row .btn-primary").prop("disabled", true);
    }
};

jQuery(document).ready(function() {
    checkTitle()
    jQuery("#no_table_report_stage").change(function() {
      checkTitle()
    })
});




