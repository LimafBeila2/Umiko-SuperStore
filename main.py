from dotenv import load_dotenv
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from time import sleep
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import asyncio
from database.models import async_session, Product
from sqlalchemy.future import select
import logging
from selenium.common.exceptions import TimeoutException


# Настройки Chrome
options = Options()
options.add_argument("--disable-blink-features=AutomationControlled")  # Отключение признаков автоматизации
options.add_argument("--headless")  # Для работы без графического интерфейса
options.add_argument("--no-sandbox")  # Важно для серверов, таких как Railway
options.add_argument("--disable-dev-shm-usage")  # Решает некоторые проблемы с памятью

# Автоустановка ChromeDriver
service = Service(ChromeDriverManager().install())

# Создание экземпляра драйвера с установленными опциями
driver = webdriver.Chrome(service=service, options=options)

#Функция для входа в аккаунт Umico Business с использованием данных из .env
def login_to_umico(driver):
    load_dotenv()

    username = os.getenv("UMICO_USERNAME")
    password = os.getenv("UMICO_PASSWORD")

    if not username or not password:
        raise ValueError("Ошибка: логин или пароль не найдены в .env")

    driver.get("https://business.umico.az/sign-in")

    # Ввод логина и пароля
    login_input = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, "//input[@placeholder='İstifadəçi adı daxil edin']"))
    )
    login_input.send_keys(username)

    password_input = driver.find_element(By.XPATH, "//input[@placeholder='Şifrəni daxil edin']")
    password_input.send_keys(password)
    password_input.send_keys(Keys.RETURN)

    try:
        WebDriverWait(driver, 30).until(EC.url_contains("/account/orders"))
        print("Успешный вход в Umico Business! Вы находитесь на странице заказов.")
    except Exception as e:
        print(f"Ошибка входа: {e}")
        driver.quit()
        raise ValueError("Ошибка входа! Проверь логин и пароль.")

# Основная функция для посещения товаров
async def visit_products(driver):
    products = await get_product_urls()  # Получаем все товары из базы данных

    for product in products:
        await process_product(driver, product)

if __name__ == "__main__":
    try:
        # Входим в Umico Business
        login_to_umico(driver)

        # Создаём и запускаем цикл событий
        loop = asyncio.get_event_loop()
        loop.run_until_complete(visit_products(driver))

    except Exception as e:
        print(f"Ошибка в основном потоке: {e}")

    finally:
        driver.quit()
        print("Ты красавчик")
