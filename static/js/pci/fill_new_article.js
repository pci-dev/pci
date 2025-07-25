jQuery(document).ready(function() {

  // checkboxes required for submission
  var prerequisites = [
    't_articles_guide_read',
    't_articles_approvals_obtained',
    't_articles_human_subject_consent_obtained',
    't_articles_lines_numbered',
    't_articles_conflicts_of_interest_indicated',
    't_articles_no_financial_conflict_of_interest',
    't_articles_sample_size'
  ]

  var pciRRactivated = document.querySelector("#t_articles_report_stage__label")
  if (pciRRactivated) {
      prerequisites = [
        't_articles_i_am_an_author',
        't_articles_is_not_reviewed_elsewhere'
      ]
  }
  if (pciRRactivated) {
    if (jQuery("#t_articles_picture_rights_ok").prop("checked")) {
      jQuery("#t_articles_uploaded_picture").prop("disabled", false);
    } else {
      jQuery("#t_articles_uploaded_picture").prop("disabled", true);
    }
}

  if (jQuery("#t_articles_already_published").prop("checked")) {
    jQuery("#t_articles_article_source__row").show();
  } else {
    jQuery("#t_articles_article_source__row").hide();
    jQuery("input[type=submit]").prop("disabled", true);
  }

  if (jQuery("#t_articles_already_published").length)
    if (all_prerequisites()) {
      jQuery("input[type=submit]").prop("disabled", false);
    }

  if (jQuery("#t_articles_is_not_reviewed_elsewhere").prop("checked")) {
    jQuery("#t_articles_parallel_submission").prop("disabled", true);
  }

  if (
    (jQuery("#t_articles_is_not_reviewed_elsewhere").prop("checked") |
      jQuery("#t_articles_parallel_submission").prop("checked")) &
    jQuery("#t_articles_i_am_an_author").prop("checked")
  ) {
    if (all_prerequisites()) {
      jQuery("input[type=submit]").prop("disabled", false);
    }
  } else {
    jQuery("input[type=submit]").prop("disabled", true);
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
      if (all_prerequisites()) {
        jQuery("input[type=submit]").prop("disabled", false);
      }
    } else {
      jQuery("input[type=submit]").prop("disabled", true);
    }
  });
  jQuery("#t_articles_i_am_an_author").change(function() {
    if (
      (jQuery("#t_articles_is_not_reviewed_elsewhere").prop("checked") |
        jQuery("#t_articles_parallel_submission").prop("checked")) &
      jQuery("#t_articles_i_am_an_author").prop("checked")
    ) {
      if (all_prerequisites()) {
        jQuery("input[type=submit]").prop("disabled", false);
      }
    } else {
      jQuery("input[type=submit]").prop("disabled", true);
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
      if (all_prerequisites()) {
        jQuery("input[type=submit]").prop("disabled", false);
      }
    } else {
      jQuery("input[type=submit]").prop("disabled", true);
    }
  });


  // function checks all prerequisite checkbox status
  function all_prerequisites() {
    for (var i = 0; i < prerequisites.length; i++) {
      var checkbox = document.querySelector('#' + prerequisites[i]);
      if (checkbox.checked == false) { return false }
    }
    return true
  }

  // prerequisite checkbox onchange events
  for (var i = 0; i < prerequisites.length; i++) {
    var checkbox = document.querySelector('#' + prerequisites[i]);
    checkbox.onchange = function() {
      var not_reviewed_elsewhere = document.querySelector("#t_articles_is_not_reviewed_elsewhere");
      var parallel_submission = document.querySelector("#t_articles_parallel_submission");
      var i_am_author = document.querySelector("#t_articles_i_am_an_author");
      if (parallel_submission != null) {
        if ((not_reviewed_elsewhere.checked == true | parallel_submission.checked == true) &
            i_am_author.checked == true & all_prerequisites()) {
            document.querySelector("#submit_record__row input[type=submit]").disabled = false; }
        else {
          document.querySelector("#submit_record__row input[type=submit]").disabled = true;
        }
      }
      else {
        if (not_reviewed_elsewhere.checked == true & i_am_author.checked == true & all_prerequisites()) {
              document.querySelector("#submit_record__row input[type=submit]").disabled = false; }
        else {
              document.querySelector("#submit_record__row input[type=submit]").disabled = true;
        }
      }
    }
  };




})

// Crossref API
function insertAfter(referenceNode, newNode) {
  referenceNode.parentNode.insertBefore(newNode, referenceNode.nextSibling);
}

var doi_button_container = document.createElement("div");
doi_button_container.classList = "pci2-flex-row pci2-align-items-center";
doi_button_container.style = "margin: 5px 0 0";

var button = document.createElement("a");
button.innerHTML = "Complete form automatically";
button.classList = "btn btn-default";
button.style = "margin: 0";
button.onclick = getCrossrefDatas;

var error_message = document.createElement("span");
error_message.style = "margin-left: 10px; font-weight: bold";

doi_button_container.appendChild(button);
doi_button_container.appendChild(error_message);

var div = document.getElementById("t_articles_doi");
insertAfter(div, doi_button_container);

var prevent_double_submit = false;

function getCrossrefDatas() {
  if (!prevent_double_submit) {
    prevent_double_submit = true;
    button.classList = "btn btn-default disabled";

    error_message.innerHTML =
      '<div class="pci2-flex-row pci2-align-items-center"><i class="glyphicon glyphicon-refresh icon-rotating" style="color: #ffbf00; font-size: 20px; margin-right:5px"></i> <span>Waiting for Crossref API...</span></div>';

    var doi = document.getElementById("t_articles_doi").value;
    httpRequest = new XMLHttpRequest();

    httpRequest.onreadystatechange = alertContents;
    httpRequest.open("GET", "https://api.crossref.org/works/" + doi, true);
    httpRequest.send();
  }
}

function alertContents() {
  if (httpRequest.readyState === XMLHttpRequest.DONE) {
    prevent_double_submit = false;
    button.classList = "btn btn-default";

    if (httpRequest.status === 200) {
      fillFormFields(httpRequest.responseText);
      error_message.innerText = "Some fields have been auto-filled";
      error_message.classList = "success-text";
    } else {
      error_message.innerText = "Sorry: although the DOI or URL of your preprint is probably correct, it cannot be used to auto-fill the submission form. Please, fill the form below manually. Thanks!";
      error_message.classList = "success-text";
    }
  }
}

function fillFormFields(data) {
  data_json = JSON.parse(data);

  // title
  document.getElementById("t_articles_title").value =
    data_json.message.title[0];

  // authors
  var authors = "";
  var i = 0;
  data_json.message.author.forEach(author_data => {
    authors += author_data.given + " " + author_data.family;

    i++;
    if (data_json.message.author[i]) {
      authors += ", ";
    }
  });
  document.getElementById("t_articles_authors").value = authors;

  // abstract
  if (data_json.message.abstract) {
    document.getElementById(
      "t_articles_abstract_ifr"
    ).contentDocument.body.innerHTML = data_json.message.abstract;
  } else {
    document.getElementById(
      "t_articles_abstract_ifr"
    ).contentDocument.body.innerHTML = "";
  }

  const preprintServerField = document.getElementById('t_articles_preprint_server');
  if (preprintServerField != null) {
    preprintServerField.value = getPrepintServer(data_json);
  }

  const yearField = document.getElementById('t_articles_article_year');
  if (yearField != null) {
    yearField.value = getDate(data_json);
  }
}

function getPrepintServer(data_json) {
  let server = data_json.message.institution?.[0]?.name;
  if (server != null) {
    return server;
  }

  server = data_json.message['group-title'];
  if (server != null) {
    return server;
  }
}

function getDate(data_json) {
  const indexedDate = data_json.message.indexed?.['date-parts']?.[0]?.[0] ?? 0;
  const postedDate = data_json.message.posted?.['date-parts']?.[0]?.[0] ?? 0;
  const acceptedDate = data_json.message.accepted?.['date-parts']?.[0]?.[0] ?? 0;
  const createdDate = data_json.message.created?.['date-parts']?.[0]?.[0] ?? 0;
  const depositedDate = data_json.message.deposited?.['date-parts']?.[0]?.[0] ?? 0;
  const issuedDate = data_json.message.issued?.['date-parts']?.[0]?.[0] ?? 0;
  const publishedDate = data_json.message.published?.['date-parts']?.[0]?.[0] ?? 0;

  const lastDate = Math.max(
    indexedDate,
    postedDate,
    acceptedDate,
    createdDate,
    depositedDate,
    issuedDate,
    publishedDate);

    return lastDate;
}

// radio button with details box
toggleRadioElementDetailsOnChange(
  "#t_articles_data_doi__row",
  "results_based_on_data",
  "#t_articles_data_doi",
  [2]
);

toggleRadioElementDetailsOnChange(
  "#t_articles_scripts_doi__row",
  "scripts_used_for_result",
  "#t_articles_scripts_doi",
  [2]
);

toggleRadioElementDetailsOnChange(
  "#t_articles_codes_doi__row",
  "codes_used_in_study",
  "#t_articles_codes_doi",
  [2]
);

function toggleRadioElementDetailsOnChange(
  details_div_id,
  question_number,
  input_id,
  indexes
) {
  let levelRadioItems = document.querySelectorAll(
    `input[name="${question_number}"]`
  );
  let details_div = document.querySelector(details_div_id);
  let inputItems = document.querySelectorAll(input_id);

  if (levelRadioItems) {
    levelRadioItems.forEach((item) => {
      if (item) {
        if (details_div) {
          details_div.style.display = "none";
        }

        item.onchange = function () {
          if (details_div) {
            if (inputItems){
              inputItems.forEach((inputItem) => {
                if (inputItem) {
                  inputItem.value = "";
                }
              });
            }
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

var form = document.querySelector('form');
var years_field;
if (form) {
    years_field = form.querySelector('#t_articles_article_year__row');
}
if (years_field) {
    shove_manager_fields(form, years_field);
}


function shove_manager_fields(form, years_field) {
  // shove extra fields to the correct position
  let manager_label = form.querySelector('#t_articles_manager_label__row');
  form.insertBefore(manager_label, years_field);

  let manager_checks = form.querySelectorAll('.manager_checks');
  for (let i = 0; i < manager_checks.length; i++) {
    let manager_row = manager_checks[i].parentNode.parentNode.parentNode.parentNode;
    form.insertBefore(manager_row, years_field);
  }
}


function check_checkboxes() {
  // check if all checkboxes are checked, and if they are, prompt user
  let checkboxes = document.querySelectorAll('.manager_checks');
  for (let i = 0; i < checkboxes.length; i++) {
    if (checkboxes[i].checked == false) { return }
  }
  let alert = window.alert('Submission impossible because all managers are also co-authors. Please contact the managing board at contact@xxx.peercommunityin.org')
  for (let i = 0; i < checkboxes.length; i++) {
    checkboxes[i].checked = false;
  }
}


function initUrlListStringField() {
  document.querySelectorAll('input[name="data_doi"],input[name="scripts_doi"],input[name="codes_doi"]').forEach((input) => {

    document.querySelectorAll('.input-group-addon').forEach((button) => {
      button.addEventListener('click', initUrlListStringField)
    });

    if (input.value != null && input.value.length > 0) {
      return;
    }

    input.value = 'https://'
  })
}

document.querySelectorAll('input[type="radio"]').forEach((radioInput) => {
  radioInput.addEventListener('change', initUrlListStringField);
});

initUrlListStringField();

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
