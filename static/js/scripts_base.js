var scroll_lock = false;
function lock_body() {
    /* this function locks page scrolling while navigation bar is open; */
    /* secondly, we adapt navbar visibility on tablet in order to have 
        a different behaviour than bootstrap intends; */
    /* last, we also change the burger icon from active/inactive */
    var body = document.querySelector('body');
    var mynavbar = document.querySelector('#myNavbar');
    var burger = document.querySelector('#pci-burger');
    if (scroll_lock == false) {
        body.style.overflow = 'hidden';
        scroll_lock = true;
        if (window.innerWidth > 767) {
            mynavbar.style.display = 'block';
        }
        burger.src = '/pci/static/images/pci-burger-active-03.svg';
    }
    else {
        body.style.overflow = 'scroll';
        scroll_lock = false;
        if (window.innerWidth > 767) {
            mynavbar.style.display = 'none';
        }
        burger.src = '/pci/static/images/pci-burger-default.svg';
    }


}

