var button, list;

function checkAllTrue(){
  if (jQuery(list).find("input").toArray().some(x => ! x.checked)) {
    button.setAttribute("disabled", "1")
    button.parentNode.onclick = function() { return false }
  } else {
    button.removeAttribute("disabled")
    button.parentNode.onclick = ""
  }
}

jQuery(document).ready(function() {
  list = document.getElementById("validation_checklist")
  if (!list) return

  button = list.nextSibling.querySelector("span")
  checkAllTrue()
  jQuery(list).find("input").change(function() {
    checkAllTrue()
  });
});
