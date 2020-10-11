jQuery(document).ready(function () {
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
      (jQuery("#t_articles_is_not_reviewed_elsewhere").prop("checked") |
        jQuery("#t_articles_parallel_submission").prop("checked")) &
      jQuery("#t_articles_i_am_an_author").prop("checked")
    ) {
      jQuery(":submit").prop("disabled", false);
    } else {
      jQuery(":submit").prop("disabled", true);
    }
  });
  jQuery("#t_articles_i_am_an_author").change(function () {
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
  jQuery("#t_articles_parallel_submission").change(function () {
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

// Crossref API
function insertAfter(referenceNode, newNode) {
  referenceNode.parentNode.insertBefore(newNode, referenceNode.nextSibling);
}

var doi_button_container = document.createElement("div");
doi_button_container.classList = "pci2-flex-row pci2-align-items-center";
doi_button_container.style = "margin: 5px 0 0";

var button = document.createElement("a");
button.innerHTML = "Auto-fill form with Crossref API";
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

    console.log("toto");
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
      error_message.innerText = "Some field has been auto-filled";
      error_message.classList = "success-text";
    } else {
      error_message.innerText = "Error : doi not found";
      error_message.classList = "danger-text";
    }
  }
}

function fillFormFields(data) {
  data_json = JSON.parse(data);
  console.log(data_json);

  // title
  document.getElementById("t_articles_title").value =
    data_json.message.title[0];

  // authors
  var authors = "";
  var i = 0;
  data_json.message.author.forEach((author_data) => {
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
}
