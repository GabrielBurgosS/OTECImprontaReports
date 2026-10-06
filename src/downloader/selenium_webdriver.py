from selenium import webdriver
from selenium.webdriver.common.by import By
from typing import Literal, List

class WebDriverInstance:
    def __init__(self, options:webdriver.ChromeOptions|None=None) -> None:
        """
        Initializes a WebDriver instance with the given options.

        Parameters:
        options (webdriver.ChromeOptions | None): The options to use when initializing the WebDriver instance.
        If None, then the default options will be used.
        """
        self.driver = webdriver.Chrome(service=webdriver.ChromeService(), options=options)

    def navigate(self, link:str) -> None:
        """
        Navigate to the given link.
        """
        self.driver.get(link)

    def get_element(self,
                      by:Literal[By.CSS_SELECTOR, By.XPATH, By.ID, By.CLASS_NAME, By.TAG_NAME, By.NAME, By.LINK_TEXT,By.PARTIAL_LINK_TEXT], value:str) -> None: # type: ignore
        """
        Returns the text from an element on the page using the given by and value.
        The by parameter should be one of the By objects from selenium.webdriver.common.by,
        and the value parameter should be the actual value to search for.
        """
        return self.driver.find_element(by, value)
    
    def get_elements_list(self,
                      by:Literal[By.CSS_SELECTOR, By.XPATH, By.ID, By.CLASS_NAME, By.TAG_NAME, By.NAME, By.LINK_TEXT,By.PARTIAL_LINK_TEXT], value:str) -> List: # type: ignore
        """
        Returns the text from an element on the page using the given by and value.
        The by parameter should be one of the By objects from selenium.webdriver.common.by,
        and the value parameter should be the actual value to search for.
        """
        return self.driver.find_elements(by, value)
    
    def click_element(self,
                      by:Literal[By.CSS_SELECTOR, By.XPATH, By.ID, By.CLASS_NAME, By.TAG_NAME, By.NAME, By.LINK_TEXT,By.PARTIAL_LINK_TEXT], value:str) -> None: # type: ignore
        """
        Clicks an element on the page using the given by and value.
        The by parameter should be one of the By objects from selenium.webdriver.common.by,
        and the value parameter should be the actual value to search for.
        """
        self.get_element(by, value).click()

    def send_text_to_element(self,
                      by:Literal[By.CSS_SELECTOR, By.XPATH, By.ID, By.CLASS_NAME, By.TAG_NAME, By.NAME, By.LINK_TEXT,By.PARTIAL_LINK_TEXT], value:str, text:str) -> None: # type: ignore
        """
        Sends a key to an element on the page using the given by and value.
        The by parameter should be one of the By objects from selenium.webdriver.common.by,
        and the value parameter should be the actual value to search for.
        The text parameter should be the string to send to the element.
        """
        self.get_element(by, value).send_keys(text)

    def close(self) -> None:
        """
        Closes the WebDriver instance, ending the browser and chromedriver processes.
        """
        self.driver.quit()

class WebDriver():
    def __init__(self, options:webdriver.ChromeOptions|None=None) -> None:
        """
        Initializes a WebDriver context manager with the given options.

        Parameters:
        options (webdriver.ChromeOptions | None): The options to use when initializing the WebDriver instance.
        If None, then the default options will be used.
        """
        self.driver = WebDriverInstance(options)

    def close(self):
        self.__exit__(None, None, None)

    def __enter__(self):
        """
        Enters the runtime context for the WebDriver.

        This method is called when entering a with statement using this context manager.
        It returns the WebDriver instance to use within the with block.

        Returns:
        WebDriverInstance: The WebDriver instance to use within the with block.
        """
        return self.driver

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Exits the runtime context for the WebDriver.

        This method is called when exiting a with statement using this context manager.
        It closes the WebDriver instance, performing any necessary cleanup.
        """
        self.driver.close()
