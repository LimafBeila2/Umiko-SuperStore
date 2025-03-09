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
import pickle

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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

# Папка для хранения профиля в контейнере Railway
# Папка для хранения профиля в контейнере Railway
CHROME_PROFILE_PATH = "/app/tmp/chrome_profile"
COOKIES_PATH = "/app/tmp/cookies/cookies.pkl"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def check_and_create_directory(path):
    """Проверяем, существует ли директория, и если нет - создаем её."""
    if not os.path.exists(path):
        os.makedirs(path)
        logging.info(f"Директория {path} была создана.")
    else:
        logging.info(f"Директория {path} существует.")

def check_directory_access(path):
    """Проверяем доступность директории для записи."""
    if os.access(path, os.W_OK):
        logging.info(f"Доступ к директории {path} для записи разрешен.")
    else:
        logging.warning(f"Нет доступа к директории {path} для записи.")

def load_cookies(driver, file_path=COOKIES_PATH):
    """Загружаем cookies из файла."""
    try:
        if os.path.exists(file_path):
            cookies = pickle.load(open(file_path, "rb"))
            for cookie in cookies:
                driver.add_cookie(cookie)
            logging.info("Cookies успешно загружены.")
        else:
            logging.warning(f"Файл cookies не найден: {file_path}")
    except Exception as e:
        logging.warning(f"Ошибка при загрузке cookies: {e}")

def save_cookies(driver, file_path=COOKIES_PATH):
    """Сохраняем cookies в файл."""
    try:
        cookies = driver.get_cookies()
        with open(file_path, "wb") as file:
            pickle.dump(cookies, file)
        logging.info("Cookies успешно сохранены.")
    except Exception as e:
        logging.warning(f"Ошибка при сохранении cookies: {e}")

def create_driver():
    logging.info("Создаем новый WebDriver...")


    # Автоматическая установка правильной версии ChromeDriver
    chromedriver_autoinstaller.install()
    logging.info("ChromeDriver успешно установлен.")
    # Проверяем и создаем директории, если необходимо
    check_and_create_directory(os.path.dirname(COOKIES_PATH))
    check_and_create_directory(CHROME_PROFILE_PATH)

    # Проверяем права доступа к директориям
    check_directory_access(CHROME_PROFILE_PATH)
    check_directory_access(os.path.dirname(COOKIES_PATH))

    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--headless")  # Для серверной среды
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920x1080")
    options.add_argument(f"--user-data-dir={CHROME_PROFILE_PATH}")  # Путь к профилю

    # Устанавливаем переменные окружения для Chromium и ChromeDriver
    chrome_bin = os.environ.get("CHROME_BIN", "/usr/bin/chromium")
    chromedriver_path = os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")

    options.binary_location = chrome_bin
    driver = webdriver.Chrome(executable_path=chromedriver_path, options=options)
    logging.info("WebDriver создан.")

    return driver  # Возвращаем драйвер с профилем и заголовками


def login_to_umico(driver):
    logging.info("Загружаем переменные окружения для авторизации...")
    load_dotenv()  # Загружаем переменные окружения из файла .env
    username = os.getenv("UMICO_USERNAME")
    password = os.getenv("UMICO_PASSWORD")

    if not username or not password:
        logging.error("Ошибка: логин или пароль не найдены в .env")
        raise ValueError("Ошибка: логин или пароль не найдены в .env")

    logging.info("Открываем страницу авторизации Umico...")

    # Проверяем, если есть cookies
    if os.path.exists("cookies.pkl"):
        logging.info("Загружаем cookies...")
        load_cookies(driver)
        driver.get("https://business.umico.az/account/orders")
        sleep(3)
        
        try:
            # Проверяем, если мы успешно вошли
            WebDriverWait(driver, 30).until(EC.url_contains("/account/orders"))
            logging.info("Успешный вход с помощью cookies!")
            return
        except Exception as e:
            logging.warning(f"Ошибка входа с cookies: {e}")
            logging.info("Cookies не работают, повторный вход...")
    
    # Если cookies не подходят или не существуют, проходим вход с логином и паролем
    driver.get("https://business.umico.az/sign-in")
    
    # Ожидаем, пока появится поле для ввода логина
    login_input = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, "//input[@placeholder='İstifadəçi adı daxil edin']"))
    )
    login_input.send_keys(username)  # Вводим логин
    logging.info(f"Логин '{username}' введен.")

    # Находим поле для ввода пароля и отправляем его
    password_input = driver.find_element(By.XPATH, "//input[@placeholder='Şifrəni daxil edin']")
    password_input.send_keys(password)  # Вводим пароль
    password_input.send_keys(Keys.RETURN)  # Нажимаем Enter
    logging.info("Пароль введен и форма отправлена.")

    try:
        # Ожидаем загрузки страницы заказов, чтобы убедиться, что вход был успешным
        WebDriverWait(driver, 30).until(EC.url_contains("/account/orders"))
        sleep(3)  # Пауза для полной загрузки страницы
        logging.info("Успешный вход в Umico Business!")
        
        # Сохраняем cookies для дальнейших сессий
        save_cookies(driver)
    except:
        logging.error("Ошибка входа!")
        driver.quit()  # Закрываем драйвер
        raise ValueError("Ошибка входа! Проверь логин и пароль.")

def close_ad(driver):
    try:
        # Здесь добавляется возможность выбора города "Баку"
        logging.info("Ожидаем выбора города...")
        baku_option = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Баку' or text()='Bakı']"))
        )
        baku_option.click()
        logging.info("Город Баку выбран.")
    except:
        logging.info("Окно выбора города не появилось.")

def process_product(product, driver):
    try:
        logging.info(f"Начинаем обработку товара: {product['product_url']}")
        sleep(10)
        product_url, edit_url = product["product_url"], product["edit_url"]
        logging.info(f"Открываем страницу товара: {product_url}")
        driver.get(product_url)
        sleep(2)
        close_ad(driver)
        
        try:
            logging.info("Ищем кнопку для просмотра цен всех продавцов...")
            button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//a[contains(text(), 'Посмотреть цены всех продавцов') or contains(text(), 'Bütün satıcıların qiymətlərinə baxmaq')]"
                ))
            )
            button.click()
            logging.info("Кнопка для просмотра цен всех продавцов была нажата.")
        except Exception as e:
            logging.warning(f"Не удалось найти кнопку для просмотра цен: {e}")
            return
        
        logging.info("Ожидаем загрузки предложений по товару...")
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
        
        logging.info(f"Обрабатываем {len(product_offers)} предложений для этого товара.")
        for offer in product_offers:
            try:
                merchant = offer.find_element(By.CLASS_NAME, "NameMerchant").text.strip()
                logging.info(f"Предложение от продавца: {merchant}")
                
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
                logging.info(f"Найдена цена: {price}₼")
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

        logging.info(f"Процесс обработки товара завершён.")

    except Exception as e:
        logging.exception(f"Ошибка при обработке товара: {e}")
