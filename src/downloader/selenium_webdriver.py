from selenium import webdriver
from selenium.webdriver.common.by import By


class WebDriverInstance:
    def __init__(self, options: webdriver.ChromeOptions | None = None) -> None:
        """
        Initializes a Chrome WebDriver with the given options.
        Selenium Manager downloads a matching ChromeDriver when needed.
        """
        self.driver = webdriver.Chrome(service=webdriver.ChromeService(), options=options)

    def navigate(self, link: str) -> None:
        """Navigate to the given link."""
        self.driver.get(link)

    def get_element(self, by: By, value: str):
        """Return the first element matching *by* / *value*."""
        return self.driver.find_element(by, value)

    def get_elements_list(self, by: By, value: str) -> list:
        """Return all the elements matching *by* / *value*."""
        return self.driver.find_elements(by, value)

    def click_element(self, by: By, value: str) -> None:
        """Click the first element matching *by* / *value*."""
        self.get_element(by, value).click()

    def send_text_to_element(self, by: By, value: str, text: str) -> None:
        """Type *text* into the first element matching *by* / *value*."""
        self.get_element(by, value).send_keys(text)

    def close(self) -> None:
        """Close the browser and end the chromedriver process."""
        self.driver.quit()
