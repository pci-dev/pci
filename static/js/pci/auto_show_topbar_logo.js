(function () {
let navbar = document.querySelector(".navbar")
let logo = document.querySelector(".web2py-menu-first")

function onscroll() {
    let scrollPosition = window.pageYOffset;

    if (scrollPosition <= 150) {
        logo.style.display = "none"
        navbar.style.backgroundColor = "transparent"
    } else {
        logo.style.display = ""
        navbar.style.backgroundColor = ""
    }
}

onscroll()
document.addEventListener('scroll', onscroll)
})()
