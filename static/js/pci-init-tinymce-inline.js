function init_article_title_tinymce_editor() {

const ids_array_inline = ["#t_articles_title"];

for (const id_textarea of ids_array_inline) {
  let elem = document.querySelector(id_textarea);
  if (elem) {
    // let newNode = document.createElement("h4")
    // newNode.id = elem.id + "_inline"
    // newNode.className = "test-toto"
    // newNode.innerText = ""
    // newNode.style.margin = "0"

    // get value
    // newNode.innerHTML = elem.value

    // elem.style.display = "none"

    // let parentNode = elem.parentNode
    // parentNode.insertBefore(newNode, elem)
    // let editor_elem = `<div id="${id_textarea + '_editor'}"></div>`

    let tinymce_options = {
      external_plugins: { mathjax: "../tinymce-mathjax/plugin.min.js" },
      invalid_styles:
        "font-size font-family background background-color font-color",
      selector: id_textarea,
      // Remove auto conversion to relative url
      branding: false,
      menubar: false,
      // inline: true,
      plugins: "paste",
      paste_as_text: true,
      statusbar: false,
      toolbar_sticky: true,
      toolbar: [
        {
          name: "history",
          items: ["undo", "redo"],
        },
        {
          name: "formatting",
          items: ["italic", "underline"],
        },
        {
          name: "mediatype",
          items: ["mathjax"],
        },
      ],
      mathjax: {
        lib: "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js", //required path to mathjax
        //symbols: {start: '\\(', end: '\\)'}, //optional: mathjax symbols
        //className: "math-tex", //optional: mathjax element class
        //configUrl: '/your-path-to-plugin/@dimakorotkov/tinymce-mathjax/config.js' //optional: mathjax config js
      },
    };
    if (id_textarea == "#t_articles_title") {
      (tinymce_options.content_css = false),
        (tinymce_options.content_style = `
				  body p {
              font-weight: bold;
				  }

          body p em {
            font-weight: normal;
          }
        `);
    }

    tinymce.init(tinymce_options);
  }
}

}
