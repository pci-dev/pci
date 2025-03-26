document
  .getElementById("cancel-submission-button")
  ?.addEventListener("click", confirmationDialogFunction);

function confirmationDialogFunction(e) {
  e.preventDefault();

  const link = e.currentTarget.getElementsByTagName("a")?.[0];
  if (link != null) {
    $("#confirmation-modal")
      .modal("show")
      .on("click", "#confirm-dialog", function () {
        location.href = link.getAttribute('href');
      });

    $("#cancel-dialog").on("click", function () {
      return;
    });
  }
}
