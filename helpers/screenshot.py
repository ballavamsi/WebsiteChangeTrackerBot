from selenium import webdriver
from selenium.webdriver.firefox.options import Options
import os
import asyncio


class Screenshot:
    driver = None
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    """
    Initialize the webdriver
    """
    def __init__(self, admin_user):
        self.browser = os.environ.get("DEFAULT_BROWSER", "chrome")

        if self.driver is None:
            # current folder
            self.admin_user = admin_user
            driver_path = os.path.join(self.app_dir, 'driver')

            if self.browser == "firefox":
                driver_name = "geckodriver.exe"
                options = Options()
                if os.environ.get("IS_HEADLESS", "") == "True":
                    options.add_argument("--headless")
                self.driver = webdriver.Firefox(
                                executable_path=os.path.join(driver_path,
                                                             driver_name),
                                options=options)
            elif self.browser == "chrome":
                driver_name = "chromedriver.exe"
                options = webdriver.ChromeOptions()
                if os.environ.get("IS_HEADLESS", "") == "True":
                    options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument('--disable-infobars')
                options.add_argument("--disable-dev-shm-usage")
                self.driver = webdriver.Chrome(
                                executable_path=os.path.join(driver_path,
                                                             driver_name),
                                chrome_options=options)
            elif self.browser == "brave":
                driver_name = "chromedriver.exe"
                options = webdriver.ChromeOptions()
                if os.environ.get("IS_HEADLESS", "") == "True":
                    options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument('--disable-infobars')
                options.add_argument("--disable-dev-shm-usage")

                if os.environ.get("BRAVE_BROWSER_PATH", "") != "":
                    options.binary_location = \
                        os.environ.get("BRAVE_BROWSER_PATH", "")
                self.driver = webdriver.Chrome(
                                executable_path=os.path.join(driver_path,
                                                             driver_name),
                                chrome_options=options)
            elif self.browser == "remotechrome":

                options = webdriver.ChromeOptions()
                options.add_argument('--ignore-ssl-errors=yes')

                options.add_extension(os.path.join(driver_path,
                                                   'adblocker.crx'))
                options.add_argument('--ignore-certificate-errors')
                options.add_argument('--window-size=1920,1080')

                self.driver = webdriver.Remote(
                               command_executor=os.environ.get("SELENIUM_URL"),
                               options=options)

        if self.browser != "remotechrome":
            self.driver.set_window_position(-10000, 0)
            self.driver.set_window_size(1920, 1080)
        else:
            self.driver.maximize_window()

    """
    Capture screenshot of a given url
    """
    async def capture(self, url, task_id, delay=30):

        self.driver.get(url)
        # unique filename
        filename = os.path.join(os.getenv("FILESYSTEM_PATH"),
                                f"screenshot_{task_id}_temp.png")
        await asyncio.sleep(int(os.getenv("SCREENSHOT_DELAY", 30)))
        self.driver.save_screenshot(filename)

        if self.browser == 'remotechrome':
            self.driver.stop_client()
        self.driver.close()
        self.driver.quit()
        return filename
