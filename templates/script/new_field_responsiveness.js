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
