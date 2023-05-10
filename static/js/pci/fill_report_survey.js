// select input with details box
toggleElementDetailsOnChange(
  "#t_report_survey_q11_details__row",
  "#t_report_survey_q11",
  [2]
);
toggleElementDetailsOnChange(
  "#t_report_survey_q12_details__row",
  "#t_report_survey_q12",
  [2]
);

toggleElementDetailsOnChange(
  "#t_report_survey_q24_1_details__row",
  "#t_report_survey_q24_1",
  [2]
);

// radio button with details box
toggleRadioElementDetailsOnChange(
  "#t_report_survey_q13_details__row",
  "q13",
  [2, 3]
);
toggleRadioElementDetailsOnChange(
  "#t_report_survey_q26_details__row",
  "q26",
  [2, 3]
);
toggleRadioElementDetailsOnChange(
  "#t_report_survey_q27_details__row",
  "q27",
  [2, 3]
);
toggleRadioElementDetailsOnChange(
  "#t_report_survey_q28_details__row",
  "q28",
  [2, 3]
);

function toggleElementDetailsOnChange(
  details_div_id,
  select_input_id,
  indexes
) {
  let details_div = document.querySelector(details_div_id);
  let select_input = document.querySelector(select_input_id);

  if (select_input && indexes.includes(select_input.selectedIndex)) {
    if (details_div) {
      details_div.style.display = "flex";
    }
  } else {
    if (details_div) {
      details_div.style.display = "none";
    }
  }

  if (select_input) {
    select_input.addEventListener("change", (event) => {
      details_div = document.querySelector(details_div_id);
      if (indexes.includes(event.target.selectedIndex)) {
        if (details_div) {
          details_div.style.display = "flex";
        }
      } else {
        if (details_div) {
          details_div.style.display = "none";
        }
      }
    });
  }
}

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

function disableQuestionOnChange(question_id, answer_id, awaited_answer) {
  let toggledInputDiv = document.querySelector(question_id + "__row");
  let toggledInput = document.querySelector(question_id + "__row input");
  let answerSelect = document.querySelector(answer_id);

  if (!toggledInput) {
    toggledInput = document.querySelector(question_id + "__row select");
  }
  // text value for recommender (view mode =/= edit mode)
  let answerValueTextMode = document.querySelector(
    answer_id + "__row > .col-sm-9"
  );

  if (
    (answerSelect && answerSelect.selectedIndex == 2) ||
    (answerValueTextMode && answerValueTextMode.innerText == awaited_answer)
  ) {
    if (toggledInputDiv) {
      toggledInputDiv.style.opacity = 1;
      toggledInput.disabled = false;
    }
  } else {
    if (toggledInputDiv) {
      toggledInputDiv.style.opacity = 0.5;
      toggledInput.disabled = true;
    }
  }

  if (answerSelect) {
    answerSelect.addEventListener("change", (event) => {
      toggledInputDiv = document.querySelector(question_id + "__row");
      if (event.target.selectedIndex == 2) {
        if (toggledInputDiv) {
          toggledInputDiv.style.opacity = 1;
          toggledInput.disabled = false;
        }
      } else {
        if (toggledInputDiv) {
          toggledInputDiv.style.opacity = 0.5;
          toggledInput.disabled = true;
        }
      }
    });
  }
}
// don't install on-change handler for q10 if force disabled
if (! document.getElementById("t_report_survey_q10").disabled)
disableQuestionOnChange(
  "#t_report_survey_q10",
  "#t_report_survey_q1",
  "RR SNAPSHOT FOR SCHEDULED REVIEW"
);
disableQuestionOnChange(
  "#t_report_survey_q1_1",
  "#t_report_survey_q1",
  "RR SNAPSHOT FOR SCHEDULED REVIEW"
);
disableQuestionOnChange(
  "#t_report_survey_q1_2",
  "#t_report_survey_q1",
  "RR SNAPSHOT FOR SCHEDULED REVIEW"
);

// Set title for all options
optionsItems = document.querySelectorAll("form select option");
if (optionsItems) {
  optionsItems.forEach(function (item) {
    item.title = item.innerText;
  });
}

// Message alert if level 0 submission
let levelRadioItems = document.querySelectorAll('input[name="q7"]');
var isAlertMessageShown = false;
if (levelRadioItems) {
  let messagediv = document.querySelector(
    "#t_report_survey_q7__row .help-block"
  );

  levelRadioItems.forEach((item) => {
    item.onchange = function () {
      messagediv.innerText = "";
    };
  });

  let level0item = levelRadioItems[levelRadioItems.length - 2];
  if (level0item) {
    level0item.onchange = function () {
      messagediv.innerText =
        "Level 0 reports are not eligible for submission to PCI RR because there is no a priori bias control";
      messagediv.classList.add("message-level-0");
    };
  }
}

// un-disable selected inputs before submitting, so we don't loose data
document.querySelector("input[type=submit]").onclick = function() {
	document.querySelectorAll(":disabled")
	.forEach(function (it) {
		if (it.value) it.disabled = false;
	})
	this.form.submit();
}

function checkEmbargo(){
  if (jQuery("#t_report_survey_q16").val() === "MAKE PUBLIC IMMEDIATELY") {
    jQuery("#t_report_survey_q17").prop("disabled", true);
    jQuery("#t_report_survey_q17").val("");
  } else {
    jQuery("#t_report_survey_q17").prop("disabled", false);
  }
}

jQuery(document).ready(function() {
  checkEmbargo()
  jQuery("#t_report_survey_q16").change(function() {
    checkEmbargo()
  })
});
