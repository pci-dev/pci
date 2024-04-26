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

    initIframe(panel);

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

function initIframe(iframe) {
  const doc = iframe.contentDocument || iframe.contentWindow.document;
  
  const linkOpenSans = doc.createElement('link');
  linkOpenSans.rel = 'stylesheet'
  linkOpenSans.href = 'https://fonts.googleapis.com/css?family=Open+Sans:400,400i,700'
  doc.head.appendChild(linkOpenSans);

  const style = document.createElement('style');
  style.textContent = `
    * {
      font-family: "Open Sans", sans-serif;
      color: rgb(136, 136, 136);
      font-size: 14px;
      margin: 0px;
      line-height: 20px
    }

    i {
      font-size: 14px;
    }

    h3 {
      font-weight: bold;
      font-size: 17px;
      margin-bottom: 5px;
      margin-top: 3px;
    }
  `
  doc.head.append(style);

  const contentHeight = iframe.contentWindow.document.body.scrollHeight
  iframe.style.height = contentHeight + 7 + 'px';
}
