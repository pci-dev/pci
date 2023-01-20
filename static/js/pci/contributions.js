$(function() {
  $("span")
    .filter(function(i) {
      return $(this).attr("title")
        ? $(this)
            .attr("title")
            .indexOf("Add record to database") != -1
        : false;
    })
    .each(function(i) {
      $(this)
        .text("Add a contributor")
        .attr(
          "title",
          "Add a new contributor to this recommendation"
        );
    });
});

// add icon for delete checkbox
document.getElementById('delete_record').insertAdjacentHTML('afterend','<i class="glyphicon glyphicon-trash">')
