import json
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
from webdriver_manager.chrome import ChromeDriverManager
import random
import chromedriver_autoinstaller


# Список прокси
proxies_list = [
    "103.119.111.1:8080",
    "103.119.111.2:8080",
    "103.119.111.3:8080",
]



# Заголовки запроса
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
}


def create_driver():
    # Автоматическая установка правильной версии ChromeDriver
    chromedriver_autoinstaller.install()

    options = Options()
    # options.add_argument("--headless")  # Без графического интерфейса
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920x1080")

    # Выбираем случайный прокси
    proxy = random.choice(proxies_list)
    # options.add_argument(f"--proxy-server={proxy}")

    # Создаем драйвер
    driver = webdriver.Chrome(options=options)

    # Добавляем заголовки через CDP
    driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {"headers": headers})

    return driver  # Возвращаем драйвер с прокси и заголовками



# Функция для авторизации
# Функция для авторизации в Umico
def login_to_umico(driver):
    load_dotenv()  # Загружаем переменные окружения из файла .env
    username = os.getenv("UMICO_USERNAME")
    password = os.getenv("UMICO_PASSWORD")

    if not username or not password:
        raise ValueError("Ошибка: логин или пароль не найдены в .env")

    # Открываем страницу авторизации
    driver.get("https://business.umico.az/sign-in")
    
    # Ожидаем, пока появится поле для ввода логина
    login_input = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, "//input[@placeholder='İstifadəçi adı daxil edin']"))
    )
    login_input.send_keys(username)  # Вводим логин
    
    # Находим поле для ввода пароля и отправляем его
    password_input = driver.find_element(By.XPATH, "//input[@placeholder='Şifrəni daxil edin']")
    password_input.send_keys(password)  # Вводим пароль
    password_input.send_keys(Keys.RETURN)  # Нажимаем Enter

    try:
        # Ожидаем загрузки страницы заказов, чтобы убедиться, что вход был успешным
        WebDriverWait(driver, 30).until(EC.url_contains("/account/orders"))
        sleep(3)  # Пауза для полной загрузки страницы
        logging.info("Успешный вход в Umico Business!")
    except:
        logging.error("Ошибка входа!")
        driver.quit()  # Закрываем драйвер
        raise ValueError("Ошибка входа! Проверь логин и пароль.")
# Функция закрытия рекламы / выбора города
def close_ad(driver):
    try:
        # Здесь добавляется возможность выбора города "Баку"
        baku_option = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Баку' or text()='Bakı']"))
        )
        baku_option.click()
        logging.info("Город Баку выбран.")
    except:
        logging.info("Окно выбора города не появилось.")

# Функция обработки одного товара
def process_product(product, driver):
    try:
        sleep(10)
        product_url, edit_url = product["product_url"], product["edit_url"]
        logging.info(f"Обрабатываем товар: {product_url}")
        driver.get(product_url)
        sleep(2)
        close_ad(driver)
        
        try:
            button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//a[contains(text(), 'Посмотреть цены всех продавцов') or contains(text(), 'Bütün satıcıların qiymətlərinə baxmaq')]"
                ))
            )
            button.click()
        except:
            logging.warning("Не удалось найти кнопку просмотра цен.")
            return
        
        WebDriverWait(driver, 30).until(
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
                
                price_text_old = offer.find_element(By.XPATH, ".//span[@data-info='item-desc-price-old']").text.strip() if offer.find_elements(By.XPATH, ".//span[@data-info='item-desc-price-old']") else None
                price_text_new = offer.find_element(By.XPATH, ".//span[@data-info='item-desc-price-new']").text.strip() if offer.find_elements(By.XPATH, ".//span[@data-info='item-desc-price-new']") else None
                
                # Выбираем минимальную цену, если оба атрибута найдены
                price_text = None
                if price_text_old and price_text_new:
                    price_text = min(price_text_old, price_text_new, key=lambda x: float(x.replace("₼", "").replace(" ", "").strip()))  # Убираем пробелы

                elif price_text_old:
                    price_text = price_text_old
                elif price_text_new:
                    price_text = price_text_new
                # Если цена найдена, очищаем и конвертируем её в число
                if price_text:
                    price_text_cleaned = price_text.replace("₼", "").replace(" ", "").strip()
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

        # Проверяем, если цена товара меньше или равна 80.1, то пропускаем
        if lowest_price <= 80.1:
            logging.info(f"Самая низкая цена ({lowest_price}₼) равна или меньше 80.1, пропускаем товар.")
            return
        
        if super_store_price is not None and lowest_price < super_store_price:
            logging.info("Меняем цену...")

            # Авторизация перед переходом на страницу редактирования
            login_to_umico(driver)

            driver.get(edit_url)
            logging.info(f"Открыта страница изменения цены: {edit_url}")
 
            # Логируем текущий URL после загрузки страницы
            logging.info(f"Текущий URL: {driver.current_url}")
            
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
                sleep(1)
                save_button.click()
                logging.info("Цена обновлена!")
                sleep(1)
                # После изменения цены пересоздаем драйвер
                driver.quit()
                driver = create_driver()
                logging.info("Пересоздан новый драйвер.")

            except Exception as e:
                logging.error(f"Ошибка при установке скидочной цены: {e}")
   
    except Exception as e:
        logging.exception(f"Ошибка при обработке товара: {e}")

# Функция для загрузки товаров из JSON
def load_json(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        return json.load(f)

# Функция для обработки товаров из JSON
def process_products_from_json(json_file):
    driver = create_driver()  # Создаем драйвер один раз перед обработкой всех товаров
    try:
        products = load_json(json_file)
        for product in products:
            process_product(product, driver)
    finally:
        driver.quit()  # Закрываем драйвер после обработки всех товаров

# Бесконечный цикл
if __name__ == "__main__":
    while True:
        process_products_from_json("product.json")
        logging.info("Работа завершена, повторная обработка через 60 секунд...")
        sleep(60)  # Пауза перед повторным запуском
