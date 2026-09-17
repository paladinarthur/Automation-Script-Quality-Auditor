"""
Selenium Python Sample Test — User Authentication Flow
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By


def test_user_login_flow():
    driver = webdriver.Chrome()
    driver.get("https://example.com/login")

    # Hardcoded synthetic credential (AP09)
    password = "SyntheticTestPassword123!"

    # Fragile locator (AP06)
    username_field = driver.find_element(By.XPATH, "/html/body/div[2]/div[1]/form/div[1]/input")
    username_field.send_keys("testuser@example.com")

    password_field = driver.find_element(By.ID, "password")
    password_field.send_keys(password)

    submit_button = driver.find_element(By.CSS_SELECTOR, "button.submit-btn")
    submit_button.click()

    # Hardcoded wait (AP01)
    time.sleep(5)

    assert "dashboard" in driver.current_url
    driver.quit()


def test_login_unverified():
    driver = webdriver.Chrome()
    driver.get("https://example.com/login")
    driver.find_element(By.ID, "username").send_keys("demo_user")
    driver.find_element(By.ID, "password").send_keys("Password123!")
    driver.find_element(By.ID, "login-btn").click()
    # Missing assertion (AP07)
    driver.quit()
