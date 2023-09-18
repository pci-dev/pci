let status_field = document.querySelector('#t_articles_status');
let status_field_value = status_field.value;

status_field.addEventListener("focus", function(event) {
    status_field_value = event.target.value;
  });
  
if (status_field) {
    status_field.addEventListener('change', function(event) {
        let confirmed = window.confirm("Are you sure you want to change the article status?");
        if (confirmed) { status_field_value = event.target.value; }
        else { event.target.value = status_field_value; }
    })
}