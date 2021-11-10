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


# Selenium extensions

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from time import sleep

def wait_clickable(self):
    WebDriverWait(driver, timeout=5).until(EC.element_to_be_clickable(self))
    sleep(.1)
    return self

def element_contains(self, text):
    assert(text in self.text)

from contextlib import contextmanager

@contextmanager
def element_frame(self):
    driver.switch_to.frame(self)
    yield self
    driver.switch_to.default_content()


WebElement.wait_clickable = wait_clickable
WebElement.contains = element_contains
WebElement.frame = element_frame


# HELPERS

def visit(url):
    return driver.get(url)

def select(css, text="", contains=""):
    if text or contains:
        return lookup(css, text, contains)
    sel = driver.find_elements(By.CSS_SELECTOR, css)
    return sel if len(sel) > 1 else sel[0]

def lookup(css, text="", contains=""):
    for e in driver.find_elements(By.CSS_SELECTOR, css):
        print(f"e.text='{e.text}'")
        if text and (text == e.text):
            print(f"text={text}")
            return e
        if contains and (contains in e.text):
            print(f"contains={contains}")
            return e
    raise KeyError("no such element: " + text)

def login(user):
    visit(config.base_url)
    select(".btn", "LOG IN").click()
    select("#auth_user_email").send_keys(user.email)
    select("#auth_user_password").send_keys(user.password)
    select("input.btn").click()
    select(".w2p_flash.alert", "Logged in").wait_clickable().click()

def logout(user):
    select(".dropdown-toggle", user.name).click()
    select(".dropdown-menu li", "Log out").click()
    select(".w2p_flash.alert", "Logged out").wait_clickable().click()
