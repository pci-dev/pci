initTinyMCE();

function initTinyMCE(elementSelector, idTextarea) {

  const ids_array = [
    "#help_texts_contents",
    "#t_articles_abstract",
    "#t_articles_cover_letter",
    "#t_recommendations_recommendation_comments",
    "#t_reviews_review",
    "#t_recommendations_reply",
    "#mail_templates_contents",
    "#no_table_message",
    "#mail_queue_mail_content",
  ];

  for (const id_textarea of ids_array) {
    let elem;
    if (elementSelector && idTextarea && id_textarea == idTextarea) {
      elem = document.querySelector(elementSelector);
    } else {
      elem = document.querySelector(id_textarea);
    }
   
    if (elem) {
      // let editor_elem = `<div id="${id_textarea + '_editor'}"></div>`
      let invalid_styles;
      if (
        id_textarea == "#help_texts_contents" ||
        id_textarea == "#mail_templates_contents"
      ) {
        invalid_styles = "";
      } else if (id_textarea == "#mail_queue_mail_content") {
        invalid_styles = "font-size font-family";
      } else {
        invalid_styles = "font-size font-family background background-color";
      }

      let safePasteActivated;
      let style_tools;
      if (
        id_textarea == "#help_texts_contents" ||
        id_textarea == "#mail_templates_contents"
      ) {
        style_tools = ["styleselect", "forecolor", "removeformat"];
        safePasteActivated = false;
      } else {
        style_tools = ["styleselect"];
        safePasteActivated = true;
        invalid_styles += "font-color";
      }

      let tinymce_options = {
        external_plugins: { mathjax: "../tinymce-mathjax/plugin.min.js" },
        invalid_styles: invalid_styles,
        selector: elementSelector ? elementSelector : id_textarea,
        // Remove auto conversion to relative url
        convert_urls: false,
        branding: false,
        menubar: false,
        statusbar: false,
        plugins: "table paste lists link autoresize media image hr",
        paste_as_text: safePasteActivated,
        toolbar_sticky: true,
        autoresize_bottom_margin: 15,
        toolbar: [
          {
            name: "history",
            items: ["undo", "redo"],
          },
          {
            name: "styles",
            items: style_tools,
          },
          {
            name: "alignment",
            items: ["alignleft", "aligncenter", "alignright", "alignjustify"],
          },
          {
            name: "formatting",
            items: ["bold", "italic", "underline", "link"],
          },
          // forecolor (font-color)
          // {
          //   name: 'indentation', items: [ 'outdent', 'indent' ]
          // },
          {
            name: "blockformats",
            items: ["numlist", "bullist", "blockquote", "hr"],
          },
          {
            name: "mediatype",
            items: ["table", "image", "media", "mathjax"],
          },
        ],
        style_formats: [
          { title: "Heading 1", format: "h2" },
          { title: "Heading 2", format: "h3" },
          { title: "Heading 3", format: "h4" },
          { title: "Normal", block: "div" },
          { title: "Sub text", inline: "span", classes: "sub-text" },
        ],
        mathjax: {
          lib: "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js", //required path to mathjax
          //symbols: {start: '\\(', end: '\\)'}, //optional: mathjax symbols
          //className: "math-tex", //optional: mathjax element class
          //configUrl: '/your-path-to-plugin/@dimakorotkov/tinymce-mathjax/config.js' //optional: mathjax config js
        },
      };

      if (id_textarea == "#help_texts_contents") {
        (tinymce_options.content_css = false),
          (tinymce_options.content_style = `
				body{
            font-family: "Open Sans", sans-serif;
				}
            
				blockquote {
				    border-radius: 5px; 
					  margin: 0 0 20px;
				    border: 2px solid #cc0e0e; 
				    padding: 10px; 
				    font-weight: bold;
				}
            
				blockquote ul {
				    margin: 0;	
        }
        
        hr {
          box-sizing: content-box;
          height: 0px;
          margin-top: 20px;
          margin-bottom: 20px;
          border-right-width: 0px;
          border-bottom-width: 0px;
          border-left-width: 0px;
          border-top-style: solid;
          border-top-color: #f8f5f0;
        }

        .sub-text {
          font-size: 12px !important;
        }
			`);
      } else {
        (tinymce_options.content_css = false),
          (tinymce_options.content_style = `
				body{
            font-family: "Open Sans", sans-serif;
				}
            
				blockquote {
					padding: 10px 20px;
					margin: 0 0 20px;
					border-left: 5px solid #dfd7ca;
        }	
        
        hr {
          box-sizing: content-box;
          height: 0px;
          margin-top: 20px;
          margin-bottom: 20px;
          border-right-width: 0px;
          border-bottom-width: 0px;
          border-left-width: 0px;
          border-top-style: solid;
          border-top-color: #f8f5f0;
        }

        .sub-text {
          font-size: 12px !important;
        }
			`);
      }

      tinymce.init(tinymce_options).then((el) => {
        const editor = el[0]
        const observer = new MutationObserver((changes) => {
          changes[0].target.style.overflowY = 'scroll';
        });
        
        editor.contentDocument.body.style.overflowY = 'scroll';
        observer.observe(editor.contentDocument.body, { attributeFilter: ['style'] });
      });
    }
  }
}
