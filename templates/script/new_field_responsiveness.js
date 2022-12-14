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


class FormValidator {
  constructor(form, fields) {
    this.form = form
    this.fields = fields
  }

  initialize() {
    this.validateOnEntry()
  }

  validateOnEntry() {
    let self = this
    this.fields.forEach(field => {
      const input = document.querySelector(`#${field}`)

      input.addEventListener('input', () => {
        self.validateFields(input)
      })
    })
  }

  validateFields(field) {

    // Check presence of values
    if (field.value.trim().length === 0) {
      this.setStatus(field, "Manuscript version cannot be blank", "error");
    } else {
      this.setStatus(field, null, "success")
    }

    if (field.id === "t_articles_ms_version") {
      if (isNaN(field.value)){
        this.setStatus(field, "Enter an integer between 1 and 100", "error")
      } else if (prevVersion > parseInt(field.value)){
	if (window.location.pathname.match("/user/"))
        this.setStatus(field, "New version number must be greater than or same as previous version number", "error")
      } else if (prevVersion === parseFloat(field.value)) {
        this.setStatus(field, "This version number is the same as the version number of the preprint of the previous round of evaluation", "static")
      } else{
        this.setStatus(field, null, "success")
      }
    }
  }

  setStatus(field, message, status) {
    const errorMessage = document.getElementById("t_articles_ms_version__row").getElementsByClassName("help-block")[0];
    const serverMessage = document.getElementById("ms_version__error");

    if (serverMessage) { 
      serverMessage.remove()
    }

    if (status === "success") {
      if (errorMessage) { 
        errorMessage.innerText = "" 
      }
    }

    if (status === "error") {
      errorMessage.innerText = message
      errorMessage.style.color = "red"
    }

    if (status === "static") {
      errorMessage.innerText = message
      errorMessage.style.color = "#7f8177"
    }
  }
}

const form = document.querySelector('.form-horizontal');
const fields = ["t_articles_ms_version"];
var queryString = window.location.search;
var urlParams = new URLSearchParams(queryString);
var articleId = urlParams.get('articleId')

var prevVersion;
var presentVersion = parseInt(document.getElementById('t_articles_ms_version').value);
if (isNaN(presentVersion)){
  presentVersion = ""
}
if (localStorage.getItem(`ms_version__${articleId}`) === null){
  localStorage.setItem(`ms_version__${articleId}`, presentVersion)
  prevVersion = parseInt(localStorage.getItem(`ms_version__${articleId}`))
}
else {
  if(presentVersion >= localStorage.getItem(`ms_version__${articleId}`)){
    localStorage.setItem(`ms_version__${articleId}`, presentVersion)
    prevVersion = parseInt(localStorage.getItem(`ms_version__${articleId}`, presentVersion))
    
  }else{
    prevVersion = parseInt(localStorage.getItem(`ms_version__${articleId}`))
  }
}

const validator = new FormValidator(form, fields);
validator.initialize();

$(".btn-success").on("click", function() {
  if (prevVersion === parseFloat($("#t_articles_ms_version").val())){
    $(".btn-success").attr("data-toggle", "modal");
    $(".btn-success").attr("data-target", "#myModal"); 
    $('.form-horizontal').submit(function (evt) {
      evt.preventDefault();
    });
  } else {
    $(".btn-success").attr("data-toggle", "");
    $(".btn-success").attr("data-target", ""); 
    $('.form-horizontal').submit(function (evt) {
      $(this).unbind('submit').submit();
    });
  }
});


$(".btn-primary").on("click", function() {
  $('.form-horizontal').submit(function (evt) {
    $(this).unbind('submit').submit();
  });
  $('.form-horizontal').submit();
});
