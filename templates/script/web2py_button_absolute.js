let action_buttons = document.querySelectorAll(
  ".action-button-absolute .web2py_htmltable>table>tbody>tr>td:last-child"
);

for (let i = 0; i < action_buttons.length; i++) {
  let itemHeight = document.querySelectorAll(
    ".action-button-absolute .web2py_htmltable>table>tbody>tr>td:first-child"
  )[i].offsetHeight;

  container = document.createElement("div");
  var cln = action_buttons[i].innerHTML;

  container.innerHTML = cln;
  action_buttons[i].innerHTML = "";
  action_buttons[i].appendChild(container);

  if (container.childNodes.length > 2 && itemHeight < 120) {
    itemHeight = 120;
  }

  //container.style.height = itemHeight + "px";
  //action_buttons[i].style.height = itemHeight + "px";
}

window.addEventListener("resize", () => {
  let action_buttons = document.querySelectorAll(
    ".action-button-absolute .web2py_htmltable>table>tbody>tr>td:last-child>div"
  );
  for (let i = 0; i < action_buttons.length; i++) {
    let itemHeight = document.querySelectorAll(
      ".action-button-absolute .web2py_htmltable>table>tbody>tr>td:first-child"
    )[i].offsetHeight;
    action_buttons[i].style.height = itemHeight + "px";
  }
});
