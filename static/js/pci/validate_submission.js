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

  createLinkFromText();
});


function createLinkFromText() {
  var plagiarism_label = document.querySelector('[for=no_plagiarism] h5');
  if (!plagiarism_label) return

  var a = document.createElement('a');
  var link = document.createTextNode('(ithenticate)');
  a.appendChild(link);
  a.title = 'ithenticate';
  a.href = 'https://crosscheck.ithenticate.com/en_us/folder';
  a.target = '_blank';
  plagiarism_label.append(a)
  plagiarism_label.append(' - plagiarism check is not needed for bioRxiv and medRxiv preprints')
}
