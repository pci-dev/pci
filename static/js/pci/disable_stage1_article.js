    document.querySelector("#t_articles_art_stage_1_id").disabled = true;

    var parent = document.querySelector("#t_articles_art_stage_1_id__row > div");
    var text = document.createTextNode("This article already has some related stage 2.");
    var child = document.createElement("span");

    child.style.color = "#fcc24d"
    child.style.fontWeight = "bold"
    child.style.fontStyle = "italic"

    child.appendChild(text);
    parent.appendChild(child);
