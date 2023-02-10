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

function non_transparent_burger_menu() {
    document.querySelector(".navbar-collapse")
    .style.backgroundColor = window.
        getComputedStyle(document.body).backgroundColor;
}

non_transparent_burger_menu()

onscroll()

document.addEventListener('scroll', onscroll)
})()
