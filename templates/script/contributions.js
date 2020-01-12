$(function() {
  $("span")
    .filter(function(i) {
      return $(this).attr("title")
        ? $(this)
            .attr("title")
            .indexOf('"""+T("Add record to database")+"""') != -1
        : false;
    })
    .each(function(i) {
      $(this)
        .text('"""+T("Add a contributor")+"""')
        .attr(
          "title",
          '"""+T("Add a new contributor to this recommendation")+"""'
        );
    });
});
