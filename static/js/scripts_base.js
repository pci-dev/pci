// remove all empty containers, as they litter the layout
var all_ps = document.querySelectorAll('p');
for (var i = 0; i<all_ps.length; i++) {
    if (all_ps[i].innerHTML == '' || all_ps[i].innerHTML == '&nbsp;' || all_ps[i].innerHTML == '&nbsp;&nbsp;') {
        all_ps[i].style.display = 'none';
    }
}


var scroll_lock = false;
function lock_body() {
    /* this function locks page scrolling while navigation bar is open; */
    /* secondly, we adapt navbar visibility on tablet in order to have 
        a different behaviour than bootstrap intends; */
    /* last, we also change the burger icon from active/inactive */
    var mynavbar = document.querySelector('#myNavbar');
    var burger = document.querySelector('#pci-burger');
    if (scroll_lock == false) {
        scroll_lock = true;
        if (window.innerWidth > 767) {
            mynavbar.style.display = 'block';
        }
        burger.classList.add('burger-active');
    }
    else {
        scroll_lock = false;
        if (window.innerWidth > 767) {
            mynavbar.style.display = 'none';
        }
        burger.classList.remove('burger-active');
    }
}


function subnavs(subnav_li) {
    // only one of the sub navigations must be open at one time
    // so that they do not overlap;
    // this function closes all sub navigations except for the one clicked
    var subnav = subnav_li.querySelector('.subnav');
    var sub_navs = document.querySelectorAll('.subnav');
    for (var i = 0; i<sub_navs.length; i++) {
        if (sub_navs[i] != subnav) {
            sub_navs[i].classList.remove('in');
        }
    }
}


// observe the height of the dynamic navbar to also allow the content to shift down
var nav_height = document.querySelector('nav').offsetHeight;
var main_content = document.querySelector('#main-content');
var header = null;
if (document.querySelector('#pci-home-header-large')) {
    header = document.querySelector('#pci-home-header-large');
}
if (document.querySelector('#pci-small-header')) {
    header = document.querySelector('#pci-small-header');
}
if (document.querySelector('#pci-home-header')) {
    header = document.querySelector('#pci-home-header');
}
if (header != null) {
    header.style.paddingTop = parseInt(nav_height) + 10 + 'px';
}
else {
    main_content.style.paddingTop = parseInt(nav_height) + 10 + 'px';
}
