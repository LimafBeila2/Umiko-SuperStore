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
from selenium_stealth import stealth

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Заголовки запроса
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
}

# Папка для хранения профиля в контейнере Railway
CHROME_PROFILE_PATH = "/tmp/chrome_profile"
COOKIES_PATH = "/tmp/cookies.json"  # Путь для хранения куки

def create_driver():
    logging.info("🚀 Создаем новый WebDriver...")

    # Автоматическая установка ChromeDriver
    chromedriver_autoinstaller.install()
    logging.info("✅ ChromeDriver успешно установлен.")

    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920x1080")
    options.add_argument(f"--user-data-dir={CHROME_PROFILE_PATH}")  # Путь к профилю
    options.add_argument("--headless")  # Без интерфейса (если нужно)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument('--disable-service-worker')
    options.add_argument('--disable-application-cache')
    options.add_argument('--disk-cache-size=1')

    driver = webdriver.Chrome(options=options)
    logging.info("✅ WebDriver создан.")
    driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {"headers": headers})

    # Загружаем куки перед тем, как страница потребует авторизацию
    load_cookies(driver)

    sleep(3)  # Добавляем паузу, чтобы страницы успели прогрузиться

    return driver

def save_cookies(driver):
    """Сохранение куков в файл"""
    os.makedirs(os.path.dirname(COOKIES_PATH), exist_ok=True)
    cookies = driver.get_cookies()
    with open(COOKIES_PATH, "w", encoding="utf-8") as f:
        json.dump(cookies, f, indent=4)
    logging.info(f"✅ Куки сохранены: {len(cookies)} шт.")

def load_cookies(driver):
    """Загрузка куков из файла"""
    if os.path.exists(COOKIES_PATH):
        with open(COOKIES_PATH, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        for cookie in cookies:
            driver.add_cookie(cookie)
        logging.info("✅ Куки загружены, обновляем страницу...")
        driver.refresh()
    else:
        logging.warning("❌ Файл с куками не найден, потребуется вход.")
        login_to_umico(driver)

def check_session(driver):
    try:
        # Проверяем, что мы не на странице входа, а на странице с заказами
        WebDriverWait(driver, 10).until(EC.url_contains("/account/orders"))
        logging.info("Сессия активна.")
    except Exception as e:
        logging.warning("Сессия не активна, требуется повторный вход.")
        logging.exception(e)
        login_to_umico(driver)  # Повторная авторизация

def refresh_cookies(driver):
    """Перезагружает куки перед выполнением операций"""
    driver.delete_all_cookies()
    
    if os.path.exists(COOKIES_PATH):
        with open(COOKIES_PATH, "r", encoding="utf-8") as f:
            cookies = json.load(f)

        for cookie in cookies:
            driver.add_cookie(cookie)

        logging.info("✅ Куки обновлены, пробуем снова...")
        driver.refresh()

def login_to_umico(driver):
    logging.info("Загружаем переменные окружения для авторизации...")
    load_dotenv()  # Загружаем переменные окружения из файла .env

    username = os.getenv("UMICO_USERNAME")
    password = os.getenv("UMICO_PASSWORD")

    if not username or not password:
        logging.error("Ошибка: логин или пароль не найдены в .env")
        raise ValueError("Ошибка: логин или пароль не найдены в .env")

    logging.info("Открываем страницу авторизации Umico...")
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

        # Сохраняем куки после успешного входа
        save_cookies(driver)
    except Exception as e:
        logging.error("Ошибка входа!")
        logging.exception(e)
        driver.quit()  # Закрываем драйвер
        raise ValueError("Ошибка входа! Проверь логин и пароль.")

# Дополнительные функции остаются без изменений

if __name__ == "__main__":
    while True:
        logging.info("Запускаем процесс обработки товаров...")
        process_products_from_json("product.json")
        logging.info("Работа завершена, повторная обработка через 60 секунд...")
        sleep(60)  # Пауза перед повторным запуском
