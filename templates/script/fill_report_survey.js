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

// Q10 showing depends on Q1 answer (hidden by default)
function toggleQ10onChange() {
  let Q10_div = document.querySelector("#t_report_survey_q10__row");
  let Q10_input = document.querySelector("#t_report_survey_q10__row input");
  let Q1_select = document.querySelector("#t_report_survey_q1");

  // text value for recommender
  let Q1_value_for_recomm = document.querySelector(
    "#t_report_survey_q1__row > .col-sm-9"
  );

  if (
    (Q1_select && Q1_select.selectedIndex == 2) ||
    (Q1_value_for_recomm &&
      Q1_value_for_recomm.innerText == "RR SNAPSHOT FOR SCHEDULED REVIEW")
  ) {
    if (Q10_div) {
      Q10_div.style.opacity = 1;
      Q10_input.disabled = false;
    }
  } else {
    if (Q10_div) {
      Q10_div.style.opacity = 0.5;
      Q10_input.disabled = true;
    }
  }

  if (Q1_select) {
    Q1_select.addEventListener("change", (event) => {
      Q10_div = document.querySelector("#t_report_survey_q10__row");
      if (event.target.selectedIndex == 2) {
        if (Q10_div) {
          Q10_div.style.opacity = 1;
          Q10_input.disabled = false;
        }
      } else {
        if (Q10_div) {
          Q10_div.style.opacity = 0.5;
          Q10_input.disabled = true;
        }
      }
    });
  }
}
toggleQ10onChange();

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
