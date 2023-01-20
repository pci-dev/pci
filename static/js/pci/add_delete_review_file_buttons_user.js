const urlOrigin = window.location.href.split("user")[0];
const urlParams = new URLSearchParams(window.location.search)
var reviewId = urlParams.get("reviewId")

// function to create delete button if there's [file] link
function createDeleteFileButton(file_type, row_css_id) {
  const trackChangeFileLink = document.querySelector(
    row_css_id + " a"
  );

  if (trackChangeFileLink && reviewId) {
    const trackChangeFileSpan = document.querySelector(
        row_css_id + " > div > div > span"
    );

    if (trackChangeFileSpan) {
      deleteUrl =
        urlOrigin +
        "user_actions/delete_review_file?reviewId=" +
        reviewId +
        "&fileType=" +
        file_type;

      var link = document.createElement("a");
      link.href = deleteUrl;
      link.innerHTML =
        '<i class="glyphicon glyphicon-trash"></i><span> delete file</span>';
      link.style.color = "#d9534f";
      link.style.marginLeft = "15px";

      trackChangeFileSpan.appendChild(link);
    }
  }
}


createDeleteFileButton("review_pdf", "#t_reviews_review_pdf__row");
