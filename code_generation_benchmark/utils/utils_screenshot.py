from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image
import time


options = Options()
options.add_argument('--headless')
options.add_argument("--window-size=1920,1080")
_driver = webdriver.Chrome(options=options)

def get_driver():
    return _driver

def take_screenshot(driver: webdriver.Chrome, html_path: str):

    driver.get(f'file://{html_path}')
    time.sleep(0.2)

    svg = driver.find_element("css selector", "svg")

    svg_width = driver.execute_script("return arguments[0].getBoundingClientRect().width;", svg)
    svg_height = driver.execute_script("return arguments[0].getBoundingClientRect().height;", svg)
    required_width = int(svg_width + 500)
    required_height = int(svg_height + 500)

    if required_width > 1920 or required_height > 1080:
        driver.set_window_size(required_width, required_height)
        time.sleep(0.3)

    location = svg.location
    size = svg.size

    x = location['x']
    y = location['y']
    width = size['width']
    height = size['height']

    driver.save_screenshot(html_path.replace('.html', '_full.png'))

    image = Image.open(html_path.replace('.html', '_full.png'))
    left = round(x)
    top = round(y)
    right = round(x + width)
    bottom = round(y + height)
    cropped_image = image.crop((left, top, right, bottom))
    cropped_image.save(html_path.replace('.html', '.png'))

def crop_icon(full_img_path: str, norm_bbox: list):
    image = Image.open(full_img_path)
    w, h = image.size
    
    left = int(norm_bbox[0] * w)
    top = int(norm_bbox[1] * h)
    right = int(norm_bbox[2] * w)
    bottom = int(norm_bbox[3] * h)

    cropped_image = image.crop((left, top, right, bottom))

    return cropped_image

