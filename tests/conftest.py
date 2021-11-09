from selenium.webdriver.common.by import By
from selenium import webdriver
from argparse import Namespace

def get_driver():
    options = webdriver.chrome.options.Options()
    options.headless = True
    return webdriver.Chrome(options=options)

def get_config():
    base_url = "http://localhost:8000/pci"
    users = [ "user", "reviewer", "recommender", "manager", "admin", "test" ]
    return Namespace(
            base_url = base_url,
            users = users_dict(users),
    )

def users_dict(users):
    return Namespace(**{
        user: Namespace(
                name=user,
                email=user+"@pci.org",
                password="pci")
        for user in users
    })


driver = get_driver()
config = get_config()


# HELPERS

def visit(url):
    return driver.get(url)

def select(css, text=""):
    if text: return lookup(css, text)
    return driver.find_element(By.CSS_SELECTOR, css)

def lookup(css, text):
    for e in driver.find_elements(By.CSS_SELECTOR, css):
        if text in e.text: return e
    raise KeyError("no such element: " + text)

def login(user):
    visit(config.base_url)
    select(".btn", "LOG IN").click()
    select("#auth_user_email").send_keys(user.email)
    select("#auth_user_password").send_keys(user.password)
    select("input.btn").click()
    select(".w2p_flash.alert", "Logged in")

def logout(user):
    select(".dropdown-toggle", user.name).click()
    select(".dropdown-menu li", "Log out").click()
    select(".w2p_flash.alert", "Logged out")
