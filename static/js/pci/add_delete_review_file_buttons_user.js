const MANAGER_PAGE_PATH = 'recommender/reviews/edit/t_reviews/';
const isManagerPage = window.location.pathname.includes(MANAGER_PAGE_PATH);

function getReviewId() {
  const urlParams = new URLSearchParams(window.location.search);
  let reviewId = urlParams.get("reviewId");
  if (reviewId != null) {
    return reviewId;
  }

  if (isManagerPage) {
    reviewId = window.location.pathname.substring(window.location.pathname.lastIndexOf('/') + 1);
  }
  
  return reviewId;
}


function getUrlOrigin() {
  if (isManagerPage) {
    return window.location.href.split(MANAGER_PAGE_PATH)[0];
  } else {
    return window.location.href.split('user')[0];
  }
}

// function to create delete button if there's [file] link
function createDeleteFileButton(file_type, row_css_id) {
  const trackChangeFileLink = document.querySelector(
    row_css_id + " a"
  );
  const reviewId = getReviewId();

  if (trackChangeFileLink && reviewId) {
    const trackChangeFileSpan = document.querySelector(
        row_css_id + " > div > div > span"
    );

    if (trackChangeFileSpan) {
      deleteUrl =
        getUrlOrigin() +
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
