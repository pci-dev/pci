var oldUrl = $(".btn-info").attr("href");
var queryString = window.location.search;
var articleId = new URLSearchParams(queryString).get('articleId');
var editArticle = localStorage.getItem(`editArticle__${articleId}`)
if (!editArticle) {
    $(".btn-info").removeAttr("href");
    $(".btn-info").attr("disabled", true);
}
