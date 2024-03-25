function checkPanel(panelId, iconId) {
  const panel = document.querySelector(panelId);
  const arrowIcon = document.querySelector(iconId);

  if (panel?.classList.contains("pci2-panel-closed")) {
    iconTranslations = document.getElementById("icon-translations");
    icons = iconTranslations?.querySelectorAll(".glyphicon");

    iconTranslations
      ?.querySelectorAll(".glyphicon-rotate-reversed")
      ?.forEach((icon) => {
        icon.classList.remove("glyphicon-rotate-reversed");
        icon.classList.remove("pci2-hover-main-color");
        icon.classList.add("glyphicon-rotate");
        if (icons.length > 1) {
          icon.parentElement.classList.add("pci2-hover-main-color");
          arrowIcon.parentElement.classList.add("pci2-main-color-selected");
        }
      });

    menuTranslations = document.getElementById("menu-translations");
    menuTranslations
      ?.querySelectorAll(".pci2-abstract-div")
      ?.forEach((menu) => {
        menu.classList.add("pci2-panel-closed");
      });

    panel.classList.remove("pci2-panel-closed");
    arrowIcon.classList.remove("glyphicon-rotate");
    arrowIcon.classList.add("glyphicon-rotate-reversed");
    if (icons.length > 1) {
      arrowIcon.parentElement.classList.remove("pci2-hover-main-color");
      arrowIcon.parentElement.classList.add("pci2-main-color-selected");
    }
  } else {
    panel.classList.add("pci2-panel-closed");
    arrowIcon.classList.remove("glyphicon-rotate-reversed");
    arrowIcon.classList.add("glyphicon-rotate");
    if (icons.length > 1) {
      arrowIcon.parentElement.classList.add("pci2-hover-main-color");
      arrowIcon.parentElement.classList.remove("pci2-main-color-selected");
    }
  }
}
