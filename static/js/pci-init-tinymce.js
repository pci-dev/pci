const ids_array = [
  "#help_texts_contents",
  "#t_articles_abstract",
  "#t_articles_cover_letter",
  "#t_recommendations_recommendation_comments",
  "#t_reviews_review",
  "#t_recommendations_reply",
  "#mail_templates_contents"
];

for (const id_textarea of ids_array) {
  let elem = document.querySelector(id_textarea);
  if (elem) {
    // let editor_elem = `<div id="${id_textarea + '_editor'}"></div>`

    let tinymce_options = {
      external_plugins: { mathjax: "../tinymce-mathjax/plugin.min.js" },
      invalid_styles: "font-size background background-color",

      selector: id_textarea,
      branding: false,
      menubar: false,
      statusbar: false,
      plugins: "lists link autoresize media",
      toolbar_sticky: true,
      autoresize_bottom_margin: 15,
      toolbar: [
        {
          name: "history",
          items: ["undo", "redo"],
        },
        {
          name: "styles",
          items: ["styleselect"],
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
          items: ["numlist", "bullist", "blockquote", "media", "mathjax"],
        },
      ],
      style_formats: [
        { title: "Heading 1", format: "h2" },
        { title: "Heading 2", format: "h3" },
        { title: "Heading 3", format: "h4" },
        { title: "Normal", block: "div" },
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
			  		font-family: unset;
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
			`);
    } else {
      (tinymce_options.content_css = false),
        (tinymce_options.content_style = `
				body{
			  		font-family: unset;
				}
            
				blockquote {
					padding: 10px 20px;
					margin: 0 0 20px;
					border-left: 5px solid #dfd7ca;
				}					
			`);
    }

    tinymce.init(tinymce_options);
  }
}
