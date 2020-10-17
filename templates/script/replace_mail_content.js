element = document.querySelector("#mail_queue_mail_content");
if (element) {
  content_textarea = element.value;

  if (content_textarea.lastIndexOf("<!-- CONTENT START -->") != -1) {
    content_textarea = content_textarea.substring(
      content_textarea.lastIndexOf("<!-- CONTENT START -->") + 22,
      content_textarea.lastIndexOf("<!-- CONTENT END -->")
    );

    content_textarea = rtrim(content_textarea);
    content_textarea = ltrim(content_textarea);

    document.querySelector("#mail_queue_mail_content").value = content_textarea;
  }

  function rtrim(str) {
    if (!str) return str;
    return str.replace(/\s+$/g, "");
  }

  function ltrim(str) {
    if (!str) return str;
    return str.replace(/^\s+/g, "");
  }
}
