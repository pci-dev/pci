var scroll_lock = false;
function lock_body() {
    /* this function locks page scrolling while navigation bar is open */
    var body = document.querySelector('body');
    if (scroll_lock == false) {
        body.style.overflow = 'hidden';
        scroll_lock = true;
    }
    else {
        body.style.overflow = 'scroll';
        scroll_lock = false;
    }
}