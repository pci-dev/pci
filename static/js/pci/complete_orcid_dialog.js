const orcidRadio = document.getElementsByName("orcid_radio");
const authUserOrcid = document.getElementById("auth_user_orcid");
const submitButton = document.getElementById("complete-orcid-dialog-confirm");

const yesOrcidRadio = document.getElementById("yes-orcid");
const noOrcidRadio = document.getElementById("no-orcid");
const laterOrcidRadio = document.getElementById("later-orcid");

for (radio of orcidRadio) {
  radio.addEventListener("change", function () {
    if (this.id == "yes-orcid") {
      authUserOrcid.disabled = false;
      checkOrcidNumber();
    } else {
      authUserOrcid.disabled = true;
      submitButton.disabled = false;
    }
  });
}

authUserOrcid.addEventListener("input", checkOrcidNumber);

checkOrcidNumber();
function checkOrcidNumber() {
  if (yesOrcidRadio.disable) {
    return;
  }

  orcid_regex = /^\d{4}-\d{4}-\d{4}-\d{3}(\d|X)$/;
  if (orcid_regex.test(authUserOrcid.value)) {
    submitButton.disabled = false;
  } else {
    submitButton.disabled = true;
  }
}

function submitForm(url) {
  payload = {};
  if (yesOrcidRadio.checked) {
    payload = {
      orcid: authUserOrcid.value,
      value: "yes",
    };
  }

  if (noOrcidRadio.checked) {
    payload = {
      orcid: null,
      value: "no",
    };
  }

  if (laterOrcidRadio.checked) {
    payload = {
      orcid: null,
      value: "later",
    };
  }

  $.ajax({
    type: "POST",
    url: url,
    data: payload
  });

  $('#complete-profile-modal').modal('hide')
}
