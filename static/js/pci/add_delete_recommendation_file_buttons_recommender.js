const urlOrigin = window.location.href.split("recommender")[0];
const urlParams = new URLSearchParams(window.location.search)
var recommId = urlParams.get("recommId")

// function to create delete button if there's [file] link
function createDeleteFileButton(file_type, row_css_id) {
  const trackChangeFileLink = document.querySelector(
    row_css_id + " a"
  );

  if (trackChangeFileLink && recommId) {
    const trackChangeFileSpan = document.querySelector(
        row_css_id + " > div > div > span"
    );

    if (trackChangeFileSpan) {
      deleteUrl =
        urlOrigin +
        "recommender_actions/delete_recommendation_file?recommId=" +
        recommId +
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


createDeleteFileButton("recommender_file", "#t_recommendations_recommender_file__row");
