import json
import threading
import queue
import os
import logging
from time import sleep
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Настройки логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Функция загрузки JSON
def load_json(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        return json.load(f)

# Функция для создания драйвера
def create_driver():
    options = Options()
    options.binary_location = "/usr/bin/chromium"
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920x1080")
    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=options)

# Функция входа в Umico Business
def login_to_umico(driver):
    load_dotenv()
    username = os.getenv("UMICO_USERNAME")
    password = os.getenv("UMICO_PASSWORD")

    if not username or not password:
        raise ValueError("Ошибка: логин или пароль не найдены в .env")

    driver.get("https://business.umico.az/sign-in")
    login_input = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, "//input[@placeholder='İstifadəçi adı daxil edin']"))
    )
    login_input.send_keys(username)
    
    password_input = driver.find_element(By.XPATH, "//input[@placeholder='Şifrəni daxil edin']")
    password_input.send_keys(password)
    password_input.send_keys(Keys.RETURN)
    
    try:
        WebDriverWait(driver, 30).until(EC.url_contains("/account/orders"))
        sleep(3)
        logging.info("Успешный вход в Umico Business!")
    except:
        logging.error("Ошибка входа!")
        driver.quit()
        raise ValueError("Ошибка входа! Проверь логин и пароль.")

# Функция закрытия рекламы / выбора города
def close_ad(driver):
    try:
        baku_option = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Баку' or text()='Bakı']"))
        )
        baku_option.click()
        logging.info("Город Баку выбран.")
    except:
        logging.info("Окно выбора города не появилось.")

# Функция для проверки самой низкой цены и изменения цены, если нужно
def check_and_update_price(driver, product_url, edit_url, login_needed=False):
    if login_needed:
        login_to_umico(driver)  # Авторизация, если требуется

    driver.get(product_url)
    sleep(2)
    close_ad(driver)

    try:
        # Обновленный XPath для кнопки "Bütün satıcıların qiymətlərinə baxmaq"
        button = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//div[@class='Other-Sellers']/a[contains(text(), 'Bütün satıcıların qiymətlərinə baxmaq')]"))
        )
        button.click()
    except:
        logging.warning("Не удалось найти кнопку просмотра цен.")
        return

    WebDriverWait(driver, 30).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, "MPProductPricesOtherSellers"))
    )

    # Извлекаем все предложения от других продавцов
    product_offers = driver.find_elements(By.CLASS_NAME, "MPProductPricesOtherSellers-List")
    if not product_offers:
        logging.warning("Нет предложений по этому товару.")
        return
    
    lowest_price = float('inf')
    lowest_price_merchant = ""
    super_store_price = None

    for offer in product_offers:
        try:
            # Извлекаем цену и продавца
            price_text = offer.find_element(By.XPATH, ".//span[@data-info='item-desc-price-old']").text.strip()
            price_text_cleaned = price_text.replace("₼", "").strip()
            if not price_text_cleaned:
                continue
            price = float(price_text_cleaned)

            merchant = offer.find_element(By.XPATH, ".//span[@class='text-[11px] !text-[#50557a] !font-bold']").text.strip()

            if merchant == "Super Store":
                super_store_price = price
            if price < lowest_price:
                lowest_price = price
                lowest_price_merchant = merchant
        except Exception as e:
            logging.warning(f"Ошибка при обработке предложения: {e}")
            continue

    logging.info(f"Самая низкая цена: {lowest_price} от {lowest_price_merchant}")
    if super_store_price is not None:
        logging.info(f"Цена от Super Store: {super_store_price}")

    if super_store_price is not None and lowest_price < super_store_price:
        logging.info("Меняем цену...")
        driver.get(edit_url)
        sleep(5)

        try:
            discount_checkbox = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Скидка') or contains(text(), 'Endirim')]//preceding-sibling::div[contains(@class, 'tw-border-')]"))
            )

            if 'tw-border-umico-brand-main-brand' not in discount_checkbox.get_attribute('class'):
                discount_checkbox.click()
                logging.info("Галочка на скидку поставлена.")

            discount_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Скидочная цена' or @placeholder='Endirimli qiymət']"))
            )

            discount_input.clear()
            discount_input.send_keys(str(round(lowest_price - 0.01, 2)))
            logging.info(f"Установлена скидочная цена: {round(lowest_price - 0.01, 2)} ₼")

            save_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, "//button[span[text()='Готово'] or span[text()='Hazır']]"))
            )
            sleep(2)
            save_button.click()
            logging.info("Цена обновлена!")
            sleep(10)
        except Exception as e:
            logging.error(f"Ошибка при установке скидочной цены: {e}")

# Функция обработки одного товара
def process_product(q):
    driver = create_driver()
    try:
        while not q.empty():
            product = q.get()
            product_url, edit_url, login_needed = product["product_url"], product["edit_url"], product.get("login_needed", False)
            logging.info(f"Обрабатываем товар: {product_url}")
            check_and_update_price(driver, product_url, edit_url, login_needed)

            while True:
                logging.info(f"Проверяем цену товара {product_url} каждую минуту...")
                check_and_update_price(driver, product_url, edit_url, login_needed)
                sleep(60)
            q.task_done()
    except Exception as e:
        logging.exception(f"Ошибка при обработке товара: {e}")
    finally:
        driver.quit()

# Функция для запуска потоков
def process_products_from_json(json_file):
    products = load_json(json_file)
    q = queue.Queue()

    for product in products:
        q.put(product)

    threads = []
    num_threads = 2  # Запускаем 2 потока

    for _ in range(num_threads):
        thread = threading.Thread(target=process_product, args=(q,))
        threads.append(thread)
        thread.start()

    q.join()

    for thread in threads:
        thread.join()

if __name__ == "__main__":
    process_products_from_json("product.json")
    logging.info("Работа завершена!")
