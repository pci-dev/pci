$(function() {
    $('span')
    .filter(function(i) {
        return (
	    $(this).attr("title") | ""
        )
        .indexOf("Add record to database") != -1
    })
    .each(function(i) {
	$(this)
	.text("Add a review")
	.attr("title", "Add a new review from scratch");
    });
})
