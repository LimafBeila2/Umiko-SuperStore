import json
import os
import asyncio
import aiohttp
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
from time import sleep
from bs4 import BeautifulSoup

# Логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Настройки Chrome
def create_driver():
    options = Options()
    options.binary_location = "/usr/bin/chromium"
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920x1080")
    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=options)

# Функция загрузки JSON
def load_json(filename):
    with open(filename, "r", encoding="utf-8") as file:
        return json.load(file)

# Функция сохранения ссылок в JSON
def save_links_to_json(filename, links):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(links, file, ensure_ascii=False, indent=4)

# Функция входа в Umico Business
def login_to_umico(driver):
    load_dotenv()
    username = os.getenv("UMICO_USERNAME")
    password = os.getenv("UMICO_PASSWORD")

    if not username or not password:
        raise ValueError("Ошибка: логин или пароль не найдены в .env")

    driver.get("https://business.umico.az/sign-in")
    login_input = WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.XPATH, "//input[@placeholder='İstifadəçi adı daxil edin']"))
    )
    login_input.send_keys(username)

    password_input = driver.find_element(By.XPATH, "//input[@placeholder='Şifrəni daxil edin']")
    password_input.send_keys(password)
    password_input.send_keys(Keys.RETURN)

    try:
        WebDriverWait(driver, 60).until(EC.url_contains("/account/orders"))
        sleep(3)
        logging.info("Успешный вход в Umico Business!")
    except:
        logging.error("Ошибка входа!")
        driver.quit()
        raise ValueError("Ошибка входа! Проверь логин и пароль.")

# Функция закрытия рекламы
def close_ad(driver):
    try:
        baku_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Баку' or text()='Bakı']"))
        )
        baku_option.click()
        logging.info("Город Баку выбран.")
    except:
        logging.info("Окно выбора города не появилось.")

# Асинхронная функция для получения цен с товаров
async def get_product_price(session, url):
    try:
        # Отправка GET-запроса
        async with session.get(url) as response:
            html = await response.text()
            
            # Парсим HTML с помощью BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')

            # Извлечение новой цены
            new_price_element = soup.find('span', {'data-info': 'item-desc-price-new'})
            if new_price_element:
                new_price = float(new_price_element.text.strip().replace(' ₼', '').replace(',', '.'))
            else:
                new_price = None

            # Извлечение старой цены
            old_price_element = soup.find('span', {'data-info': 'item-desc-price-old'})
            if old_price_element:
                old_price = float(old_price_element.text.strip().replace(' ₼', '').replace(',', '.'))
            else:
                old_price = None

            # Возвращаем обе цены
            return new_price, old_price

    except Exception as e:
        logging.warning(f"Ошибка при получении цены с {url}: {e}")
        return None, None

# Функция для обработки товаров
def process_products(products, links):
    driver = create_driver()
    try:
        login_to_umico(driver)

        for product in products:
            product_url = product["product_url"]

            # Проверка, если ссылка уже сохранена, пропускаем
            if product_url in links:
                logging.info(f"Ссылка {product_url} уже добавлена, пропускаем...")
                continue

            # Добавляем ссылку в список
            links.append(product_url)
            save_links_to_json("links.json", links)

            logging.info(f"Обрабатываем товар: {product_url}")
            driver.get(product_url)
            sleep(2)
            close_ad(driver)

            product_offers = driver.find_elements(By.CLASS_NAME, "MPProductOffer")
            if not product_offers:
                logging.warning("Нет предложений по этому товару.")
                continue

            lowest_price = float('inf')
            lowest_price_merchant = ""
            super_store_price = None

            # Асинхронно собираем цены с предложений
            async def get_prices_from_offers():
                async with aiohttp.ClientSession() as session:
                    prices = await asyncio.gather(
                        *[get_product_price(session, offer.get_attribute("href")) for offer in product_offers]
                    )
                return prices

            prices = asyncio.run(get_prices_from_offers())

            for offer, price_tuple in zip(product_offers, prices):
                new_price, old_price = price_tuple
                if new_price is None:
                    continue

                merchant = offer.find_element(By.CLASS_NAME, "NameMerchant").text.strip()

                # Если магазин "Super Store", запоминаем цену
                if merchant == "Super Store":
                    super_store_price = new_price

                # Проверка на самую низкую цену
                if new_price < lowest_price:
                    lowest_price = new_price
                    lowest_price_merchant = merchant

            logging.info(f"Самая низкая цена: {lowest_price} от {lowest_price_merchant}")
            if super_store_price is not None:
                logging.info(f"Цена от Super Store: {super_store_price}")

            if super_store_price is not None and lowest_price < super_store_price:
                logging.info("Меняем цену...")

                edit_url = product["edit_url"]
                driver.get(edit_url)
                sleep(5)

                try:
                    discount_checkbox = WebDriverWait(driver, 100).until(
                        EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Скидка') or contains(text(), 'Endirim')]//preceding-sibling::div[contains(@class, 'tw-border-')]"))
                    )

                    if 'tw-border-umico-brand-main-brand' not in discount_checkbox.get_attribute('class'):
                        discount_checkbox.click()
                        logging.info("Галочка на скидку поставлена.")

                    discount_input = WebDriverWait(driver, 100).until(
                        EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Скидочная цена' or @placeholder='Endirimli qiymət']"))
                    )

                    discount_input.clear()
                    discount_input.send_keys(str(round(lowest_price - 0.01, 2)))
                    logging.info(f"Установлена скидочная цена: {round(lowest_price - 0.01, 2)} ₼")

                    save_button = WebDriverWait(driver, 100).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[span[text()='Готово'] or span[text()='Hazır']]"))
                    )
                    sleep(2)
                    save_button.click()
                    logging.info("Цена обновлена!")
                    sleep(10)
                except Exception as e:
                    logging.error(f"Ошибка при установке скидочной цены: {e}")

    except Exception as e:
        logging.exception(f"Ошибка при обработке товаров: {e}")
    finally:
        driver.quit()

# Основная функция работы с JSON
def process_products_from_json(json_file):
    products = load_json(json_file)
    links = []  # Список для хранения ссылок

    # Загружаем уже сохраненные ссылки, если файл существует
    if os.path.exists("links.json"):
        links = load_json("links.json")

    process_products(products, links)

    logging.info("Работа завершена!")

if __name__ == "__main__":
    process_products_from_json("product.json")
