import json
from dotenv import load_dotenv
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from queue import Queue
from threading import Thread, Lock
import time
import logging
from time import sleep

# Логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Количество потоков (можно увеличить)
NUM_DRIVERS = 5


def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-software-rasterizer")  # Добавление
    return webdriver.Chrome(options=options)

# Функция загрузки JSON
def load_json(filename):
    with open(filename, "r", encoding="utf-8") as file:
        return json.load(file)

# Функция входа в Umico Business
def login_to_umico(driver):
    load_dotenv()
    username = os.getenv("UMICO_USERNAME")
    password = os.getenv("UMICO_PASSWORD")

    if not username or not password:
        raise ValueError("Ошибка: логин или пароль не найдены в .env")

    driver.get("https://business.umico.az/sign-in")
    
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='İstifadəçi adı daxil edin']"))).send_keys(username)
    password_input = driver.find_element(By.XPATH, "//input[@placeholder='Şifrəni daxil edin']")
    password_input.send_keys(password)
    password_input.send_keys(Keys.RETURN)
    
    try:
        WebDriverWait(driver, 10).until(EC.url_contains("/account/orders"))
        logging.info("Успешный вход в Umico Business!")
    except:
        logging.error("Ошибка входа!")
        driver.quit()
        raise ValueError("Ошибка входа! Проверь логин и пароль.")

# Функция для закрытия рекламы
def close_ad(driver):
    try:
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Баку' or text()='Bakı']"))
        ).click()
        logging.info("Город Баку выбран.")
    except:
        pass

# Функция обработки товаров
def process_product(driver, product):
    product_url, edit_url = product["product_url"], product["edit_url"]
    logging.info(f"Обрабатываем товар: {product_url}")
    driver.get(product_url)
    
    time.sleep(1)  # Минимальная задержка
    close_ad(driver)

    try:
        button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Посмотреть цены всех продавцов') or contains(text(), 'Bütün satıcıların qiymətlərinə baxmaq')]"))
        )
        button.click()
    except:
        logging.warning("Не удалось найти кнопку просмотра цен.")
        return

    try:
        product_offers = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "MPProductOffer"))
        )
    except:
        logging.warning("Нет предложений по этому товару.")
        return

    lowest_price = float('inf')
    lowest_price_merchant = ""
    super_store_price = None

    for offer in product_offers:
        try:
            merchant = offer.find_element(By.CLASS_NAME, "NameMerchant").text.strip()
            price_text = offer.find_element(By.XPATH, ".//span[@data-info='item-desc-price-old']").text.strip()
            price = float(price_text.replace("₼", "").strip())

            if merchant == "Super Store":
                super_store_price = price
            if price < lowest_price:
                lowest_price = price
                lowest_price_merchant = merchant
        except:
            continue

    logging.info(f"Самая низкая цена: {lowest_price} от {lowest_price_merchant}")
    if super_store_price is not None:
        logging.info(f"Цена от Super Store: {super_store_price}")

    if super_store_price is not None and lowest_price < super_store_price:
        logging.info("Меняем цену...")
        driver.get(edit_url)
        time.sleep(1)

        try:
            discount_checkbox = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Скидка') or contains(text(), 'Endirim')]//preceding-sibling::div[contains(@class, 'tw-border-')]"))
            )

            if 'tw-border-umico-brand-main-brand' not in discount_checkbox.get_attribute('class'):
                discount_checkbox.click()
            sleep(3)
            discount_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Скидочная цена' or @placeholder='Endirimli qiymət']"))
            )

            discount_input.clear()
            discount_input.send_keys(str(round(lowest_price - 0.01, 2)))
            time.sleep(2)

            save_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[span[text()='Готово'] or span[text()='Hazır']]"))
            )
            save_button.click()
            logging.info("Цена обновлена!")
        except:
            logging.error("Ошибка при изменении цены")

# Функция обработки товаров в многопотоке
def worker(driver, queue, lock):
    while not queue.empty():
        with lock:
            product = queue.get()
        if product:
            process_product(driver, product)

# Основная функция
def process_products_from_json(json_file):
    products = load_json(json_file)
    queue = Queue()
    lock = Lock()

    for product in products:
        queue.put(product)

    drivers = [create_driver() for _ in range(NUM_DRIVERS)]

    threads = [Thread(target=worker, args=(drivers[i], queue, lock)) for i in range(NUM_DRIVERS)]
    
    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    for driver in drivers:
        driver.quit()

if __name__ == "__main__":
    process_products_from_json("product.json")
    logging.info("Работа завершена!")
