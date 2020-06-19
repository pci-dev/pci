let action_buttons = document.querySelectorAll(".action-button-absolute .web2py_htmltable>table>tbody>tr>td:last-child>div")
for(let i=0; i < action_buttons.length; i++) { 
    let itemHeight = document.querySelectorAll(".action-button-absolute .web2py_htmltable>table>tbody>tr>td:first-child")[i].offsetHeight ;
    action_buttons[i].style.height = itemHeight + 'px' 
}

window.addEventListener("resize", () => {
    let action_buttons = document.querySelectorAll(".action-button-absolute .web2py_htmltable>table>tbody>tr>td:last-child>div")
    for(let i=0; i < action_buttons.length; i++) { 
        let itemHeight = document.querySelectorAll(".action-button-absolute .web2py_htmltable>table>tbody>tr>td:first-child")[i].offsetHeight ;
        action_buttons[i].style.height = itemHeight + 'px' 
    }
});
