import json
from dotenv import load_dotenv
import os
import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
import logging
from queue import Queue

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

# Функция для закрытия рекламы
def close_ad(driver):
    try:
        baku_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Баку' or text()='Bakı']"))
        )
        baku_option.click()
        logging.info("Город Баку выбран.")
    except:
        logging.info("Окно выбора города не появилось.")

# Функция для изменения цены на товар
def change_price(driver, edit_url, new_price):
    driver.get(edit_url)
    try:
        # Ждем загрузки поля для изменения цены
        price_input = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Qiymət']"))
        )
        # Очищаем текущее поле цены
        price_input.clear()
        # Вводим новую цену
        price_input.send_keys(str(new_price))
        
        # Найдем кнопку для сохранения
        save_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Yadda saxla')]")
        save_button.click()
        
        # Ждем подтверждения изменений
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Dəyişikliklər yadda saxlanılıb')]"))
        )
        logging.info(f"Цена успешно обновлена на {new_price}!")
    except Exception as e:
        logging.error(f"Ошибка при изменении цены: {e}")
        driver.quit()

# Функция обработки товаров
def process_product(queue, links):
    while not queue.empty():
        product = queue.get()
        product_url = product["product_url"]
        
        if product_url in links:
            logging.info(f"Ссылка {product_url} уже добавлена, пропускаем...")
            queue.task_done()
            continue
        
        links.append(product_url)
        save_links_to_json("links.json", links)
        
        driver = create_driver()
        try:
            login_to_umico(driver)
            edit_url = product["edit_url"]
            logging.info(f"Обрабатываем товар: {product_url}")
            driver.get(product_url)
            sleep(2)
            close_ad(driver)
            
            try:
                button = WebDriverWait(driver, 100).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Посмотреть цены всех продавцов') or contains(text(), 'Bütün satıcıların qiymətlərinə baxmaq')]"))
                )
                button.click()
            except:
                logging.warning("Не удалось найти кнопку просмотра цен.")
                continue
            
            WebDriverWait(driver, 100).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "MPProductOffer"))
            )
            
            product_offers = driver.find_elements(By.CLASS_NAME, "MPProductOffer")
            if not product_offers:
                logging.warning("Нет предложений по этому товару.")
                continue
            
            lowest_price = float('inf')
            lowest_price_merchant = ""
            super_store_price = None
            
            for offer in product_offers:
                try:
                    merchant = offer.find_element(By.CLASS_NAME, "NameMerchant").text.strip()
                    
                    price_text = ""
                    try:
                        price_text = offer.find_element(By.XPATH, ".//span[@data-info='item-desc-price-new']").text.strip()
                    except:
                        pass
                    
                    if not price_text:
                        price_text = offer.find_element(By.XPATH, ".//span[@data-info='item-desc-price-old']").text.strip()
                    
                    price_text_cleaned = price_text.replace("₼", "").strip()
                    if not price_text_cleaned:
                        continue
                    
                    price = float(price_text_cleaned)
                    
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
            
            # Если цена не наша, меняем её
            if lowest_price_merchant != "Super Store" and super_store_price is not None and super_store_price != lowest_price:
                logging.info(f"Цена не наша, меняем на {super_store_price}")
                change_price(driver, edit_url, super_store_price)
            
        finally:
            driver.quit()
            queue.task_done()

# Основная функция работы с JSON
def process_products_from_json(json_file):
    products = load_json(json_file)
    queue = Queue()
    links = []
    
    if os.path.exists("links.json"):
        links = load_json("links.json")
    
    for product in products:
        queue.put(product)
    
    num_threads = 1
    threads = []
    for _ in range(num_threads):
        thread = threading.Thread(target=process_product, args=(queue, links))
        thread.start()
        threads.append(thread)
    
    for thread in threads:
        thread.join()
    
    logging.info("Работа завершена!")

if __name__ == "__main__":
    process_products_from_json("product.json")
