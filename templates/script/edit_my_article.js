jQuery(document).ready(function () {
  if (jQuery("#t_articles_is_not_reviewed_elsewhere").prop("checked")) {
    jQuery("#t_articles_parallel_submission").prop("disabled", true);
  }

  if (
    jQuery("#t_articles_is_not_reviewed_elsewhere").prop("checked") |
    jQuery("#t_articles_parallel_submission").prop("checked")
  ) {
    jQuery(":submit").prop("disabled", false);
  } else {
    jQuery(":submit").prop("disabled", true);
  }

  jQuery("#t_articles_picture_rights_ok").change(function () {
    if (jQuery("#t_articles_picture_rights_ok").prop("checked")) {
      jQuery("#t_articles_uploaded_picture").prop("disabled", false);
    } else {
      jQuery("#t_articles_uploaded_picture").prop("disabled", true);
      jQuery("#t_articles_uploaded_picture").val("");
    }
  });

  jQuery("#t_articles_already_published").change(function () {
    if (jQuery("#t_articles_already_published").prop("checked")) {
      jQuery("#t_articles_article_source__row").show();
    } else {
      jQuery("#t_articles_article_source__row").hide();
    }
  });

  jQuery("#t_articles_is_not_reviewed_elsewhere").change(function () {
    if (jQuery("#t_articles_is_not_reviewed_elsewhere").prop("checked")) {
      jQuery("#t_articles_parallel_submission").prop("checked", false);
      jQuery("#t_articles_parallel_submission").prop("disabled", true);
    } else {
      jQuery("#t_articles_parallel_submission").prop("disabled", false);
    }
    if (
      jQuery("#t_articles_is_not_reviewed_elsewhere").prop("checked") |
      jQuery("#t_articles_parallel_submission").prop("checked")
    ) {
      jQuery(":submit").prop("disabled", false);
    } else {
      jQuery(":submit").prop("disabled", true);
    }
  });
  jQuery("#t_articles_i_am_an_author").change(function () {
    if (
      jQuery("#t_articles_is_not_reviewed_elsewhere").prop("checked") |
      jQuery("#t_articles_parallel_submission").prop("checked")
    ) {
      jQuery(":submit").prop("disabled", false);
    } else {
      jQuery(":submit").prop("disabled", true);
    }
  });
  jQuery("#t_articles_parallel_submission").change(function () {
    if (jQuery("#t_articles_parallel_submission").prop("checked")) {
      jQuery("#t_articles_is_not_reviewed_elsewhere").prop("checked", false);
      jQuery("#t_articles_is_not_reviewed_elsewhere").prop("disabled", true);
    } else {
      jQuery("#t_articles_is_not_reviewed_elsewhere").prop("disabled", false);
    }
    if (
      jQuery("#t_articles_is_not_reviewed_elsewhere").prop("checked") |
      jQuery("#t_articles_parallel_submission").prop("checked")
    ) {
      jQuery(":submit").prop("disabled", false);
    } else {
      jQuery(":submit").prop("disabled", true);
    }
  });
});



toggleRadioElementDetailsOnChange(
  "#t_articles_data_doi__row",
  "results_based_on_data",
  [2]
);

toggleRadioElementDetailsOnChange(
  "#t_articles_scripts_doi__row",
  "scripts_used_for_result",
  [2]
);

toggleRadioElementDetailsOnChange(
  "#t_articles_codes_doi__row",
  "codes_used_in_study",
  [2]
);

function toggleRadioElementDetailsOnChange(
  details_div_id,
  question_number,
  indexes
) {
  let levelRadioItems = document.querySelectorAll(
    `input[name="${question_number}"]`
  );
  let details_div = document.querySelector(details_div_id);

  if (levelRadioItems) {
    levelRadioItems.forEach((item) => {
      if (item) {
        if (details_div) {
          details_div.style.display = "none";
        }

        item.onchange = function () {
          if (details_div) {
            details_div.style.display = "none";
          }
        };
      }
    });

    indexes.forEach((item) => {
      if (levelRadioItems[item - 1]) {
        if (levelRadioItems[item - 1].checked) {
          if (details_div) {
            details_div.style.display = "flex";
          }
        }

        levelRadioItems[item - 1].onchange = function () {
          if (details_div) {
            details_div.style.display = "flex";
          }
        };
      }
    });
  }
}



// // PCI RR
// let elemPciRR = document.querySelector(
//   "#t_articles_art_stage_1_id option[value='']"
// );
// if (elemPciRR) {
//   document.querySelector(
//     "#t_articles_art_stage_1_id option[value='']"
//   ).innerHTML = "This is a stage 1 submission";
// }



// // Scheduled submission
// let elemScheduledSubmission = document.querySelector(
//   "#t_articles_scheduled_submission_date__row"
// );
// let scheduledSubmissionInput = document.querySelector(
//   "#t_articles_scheduled_submission_date"
// );

// if (elemScheduledSubmission) {
//   elemScheduledSubmission.style.display = "none";

//   let checkboxFormGroup = document.createElement("div");
//   checkboxFormGroup.classList = "form-group";
//   elemScheduledSubmission.before(checkboxFormGroup);

//   let checkboxContainer = document.createElement("div");
//   checkboxContainer.classList = "col-sm-3";
//   checkboxFormGroup.appendChild(checkboxContainer);

//   let checkboxContainer2 = document.createElement("div");
//   checkboxContainer2.classList = "checkbox";
//   checkboxContainer.appendChild(checkboxContainer2);

//   let checkboxLabel = document.createElement("label");
//   checkboxContainer2.appendChild(checkboxLabel);

//   let checkboxInput = document.createElement("input");
//   checkboxInput.setAttribute("type", "checkbox");
//   checkboxInput.id = "checkbox-scheduled-submission";
//   checkboxInput.onchange = toggleScheduledSubmission;
//   checkboxLabel.appendChild(checkboxInput);

//   checkboxText = document.createTextNode(
//     "This is a scheduled submission (no doi yet)"
//   );
//   checkboxLabel.appendChild(checkboxText);

//   if (scheduledSubmissionInput && scheduledSubmissionInput.value != ""){
//     let elem = document.querySelector("#checkbox-scheduled-submission");
//     elem.checked = true
//     toggleScheduledSubmission()
//   }
// }

// function toggleScheduledSubmission() {
//   let scheduledSubmissionRow = document.querySelector(
//     "#t_articles_scheduled_submission_date__row"
//   );
//   let scheduledSubmissionInput = document.querySelector(
//     "#t_articles_scheduled_submission_date"
//   );

//   let doiRow = document.querySelector("#t_articles_doi__row");
//   let doiInput = document.querySelector("#t_articles_doi");

//   let msVersionRow = document.querySelector("#t_articles_ms_version__row");
//   let msVersionInput = document.querySelector("#t_articles_ms_version");

//   let elem = document.querySelector("#checkbox-scheduled-submission");

//   // if scheduled subbmission is checked
//   if (elem.checked) {
//     doiRow.style.display = "none";
//     msVersionRow.style.display = "none";
//     msVersionInput.value = "";
//     doiInput.value = "";
//     scheduledSubmissionRow.style.display = "flex";
//   } else {
//     scheduledSubmissionRow.style.display = "none";
//     scheduledSubmissionInput.value = "";
//     doiRow.style.display = "flex";
//     msVersionRow.style.display = "flex";
//   }
// }
