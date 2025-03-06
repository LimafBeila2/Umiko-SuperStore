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

# Функция обработки товаров с повторными попытками
def process_product(queue, links):
    retry_attempts = 3  # Количество попыток при ошибках

    while not queue.empty():
        product = queue.get()  # Берем задачу из очереди
        product_url = product["product_url"]
        
        # Проверка, если ссылка уже сохранена, пропустить
        if product_url in links:
            logging.info(f"Ссылка {product_url} уже добавлена, пропускаем...")
            queue.task_done()
            return
        
        # Добавляем ссылку в список
        links.append(product_url)
        save_links_to_json("links.json", links)
        
        driver = create_driver()
        attempt = 0
        success = False

        while attempt < retry_attempts and not success:
            try:
                login_to_umico(driver)
                edit_url = product["edit_url"]
                logging.info(f"Обрабатываем товар: {product_url}")
                driver.get(product_url)
                sleep(2)
                close_ad(driver)

                # Проверка цен
                button = WebDriverWait(driver, 100).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Посмотреть цены всех продавцов') or contains(text(), 'Bütün satıcıların qiymətlərinə baxmaq')]"))
                )
                button.click()

                WebDriverWait(driver, 100).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "MPProductOffer"))
                )
                
                product_offers = driver.find_elements(By.CLASS_NAME, "MPProductOffer")
                if not product_offers:
                    logging.warning("Нет предложений по этому товару.")
                    return

                lowest_price = float('inf')
                lowest_price_merchant = ""
                super_store_price = None

                for offer in product_offers:
                    try:
                        merchant = offer.find_element(By.CLASS_NAME, "NameMerchant").text.strip()
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

                if super_store_price is not None and lowest_price < super_store_price:
                    logging.info("Меняем цену...")
                    driver.get(edit_url)
                    sleep(5)

                    try:
                        # Находим элемент с чекбоксом "Скидка" или "Endirim" (для двух языков)
                        discount_checkbox = WebDriverWait(driver, 100).until(
                            EC.presence_of_element_located((
                                By.XPATH, 
                                "//div[contains(text(), 'Скидка') or contains(text(), 'Endirim')]//preceding-sibling::div[contains(@class, 'tw-border-')]"
                            ))
                        )

                        # Если галочка не установлена, ставим её
                        if 'tw-border-umico-brand-main-brand' not in discount_checkbox.get_attribute('class'):
                            discount_checkbox.click()
                            logging.info("Галочка на скидку поставлена.")

                        # Ждем появления поля для ввода скидочной цены (на двух языках)
                        discount_input = WebDriverWait(driver, 100).until(
                            EC.presence_of_element_located((
                                By.XPATH, 
                                "//input[@placeholder='Скидочная цена' or @placeholder='Endirimli qiymət']"
                            ))
                        )

                        # Устанавливаем новую цену
                        discount_input.clear()
                        discount_input.send_keys(str(round(lowest_price - 0.01, 2)))
                        logging.info(f"Установлена скидочная цена: {round(lowest_price - 0.01, 2)} ₼")

                        # Нажимаем на кнопку "Готово" или "Hazır"
                        save_button = WebDriverWait(driver, 100).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[span[text()='Готово'] or span[text()='Hazır']]"))
                        )
                        sleep(2)
                        save_button.click()
                        logging.info("Цена обновлена!")
                        sleep(10)
                        success = True
                    except Exception as e:
                        logging.error(f"Ошибка при установке скидочной цены: {e}")

                else:
                    logging.info("Не требуется изменение цены.")

            except Exception as e:
                logging.exception(f"Ошибка при обработке товара {product['product_url']}: {e}")
                attempt += 1
                if attempt < retry_attempts:
                    logging.info(f"Попытка {attempt} не удалась, повторяем через 5 секунд...")
                    sleep(5)
                else:
                    logging.error("Все попытки завершились неудачей.")
            finally:
                driver.quit()
                if not success:
                    queue.put(product)  # Возвращаем товар в очередь для повторной попытки
                queue.task_done()  # Завершаем обработку задачи

# Основная функция работы с JSON
def process_products_from_json(json_file):
    products = load_json(json_file)
    queue = Queue()
    links = []  # Список для хранения ссылок
    
    # Загружаем уже сохраненные ссылки, если файл существует
    if os.path.exists("links.json"):
        links = load_json("links.json")
    
    # Добавляем все товары в очередь
    for product in products:
        queue.put(product)

    # Создаем потоки, каждый из которых будет обрабатывать задачи
    num_threads = 5  # Количество потоков, вы можете менять это значение
    threads = []
    for _ in range(num_threads):
        thread = threading.Thread(target=process_product, args=(queue, links))
        thread.start()
        threads.append(thread)

    # Ожидаем завершения всех задач
    for thread in threads:
        thread.join()

    logging.info("Работа завершена!")

if __name__ == "__main__":
    process_products_from_json("product.json")
