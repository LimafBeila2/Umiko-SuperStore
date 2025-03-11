import os
import json
import asyncio
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from time import sleep
# Настройки для Chrome


options = Options()
options.binary_location = "/usr/bin/chromium"  # Путь к бинарному файлу Chromium
options.add_argument("--headless")  # Без интерфейса
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920x1080")

# Используем системный chromedriver
service = Service("/usr/bin/chromedriver")  # Путь к chromedriver

# Создаем веб-драйвер
driver = webdriver.Chrome(service=service, options=options)

# Функция для загрузки товаров из JSON
def load_products():
    with open("product.json", "r", encoding="utf-8") as file:
        return json.load(file)

# Функция входа в Umico Business


# Функция входа в Umico Business
def login_to_umico(driver):
    login_to_umico(driver)  # Передаем драйвер в функцию
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
    return driver.current_url == "https://business.umico.az/sign-in"

# Функция обработки товара
async def process_product(driver, product):
    try:
        name = product["name"]
        check_url = product["check_url"]
        change_url = product["change_url"]
        print(f"Обрабатываем: {name}")

        driver.get(check_url)
        await asyncio.sleep(5)

        # Парсим цену конкурентов с текущей страницы
        lowest_price = 500  # Заглушка для самой низкой цены
        super_store_price = 600  # Заглушка для цены от Super Store

        # Получаем данные о ценах (например, по xpath или другому методу)
        try:
            # Пример для парсинга цены на странице конкурента (поменяйте на реальный XPath)
            lowest_price = float(driver.find_element(By.XPATH, "xpath_цены_конкурента").text.replace('₼', '').strip())
        except Exception as e:
            print(f"Ошибка при получении цены конкурента: {e}")
        
        print(f"Самая низкая цена: {lowest_price}")
        print(f"Цена от Super Store: {super_store_price}")

        # Сравнение цен
        if lowest_price < super_store_price:
            print("Цена конкурента ниже, обновляем цену.")
            driver.get(change_url)
            await asyncio.sleep(5)

            # Ожидание чекбокса "Скидка"
            endirim_checkbox = WebDriverWait(driver, 40).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Скидка') or contains(text(), 'Endirim')]//preceding-sibling::div"))
            )

            try:
                checkmark = endirim_checkbox.find_element(By.XPATH, ".//img[@src='/checkMark.svg?url']")
                is_checked = checkmark.is_displayed()
            except:
                is_checked = False

            if not is_checked:
                print("Активируем галочку 'Скидка'.")
                endirim_checkbox.click()

            # Ожидание поля ввода скидочной цены
            discount_price_input = WebDriverWait(driver, 40).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Скидочная цена' or @placeholder='Endirimli qiymət']"))
            )

            new_price = round(lowest_price - 0.01, 2)
            discount_price_input.clear()
            discount_price_input.send_keys(str(new_price))

            print(f"Цена товара обновлена на {new_price} ₼")
            await asyncio.sleep(3)

            # Нажатие кнопки "Готово"
            save_button = WebDriverWait(driver, 40).until(
                EC.element_to_be_clickable((By.XPATH, "//button[span[text()='Готово'] or span[text()='Hazır']]"))
            )
            await asyncio.sleep(2)
            save_button.click()

            print("Цена успешно обновлена и сохранена.")
            await asyncio.sleep(10)

    except Exception as e:
        logging.error(f"Ошибка при обработке товара {name}: {e}")

# Основная функция обработки товаров
async def visit_products(driver):
    products = load_products()  # Загружаем товары из JSON
    for product in products:
        await process_product(driver, product)

if __name__ == "__main__":
    try:
        # Входим в Umico Business
        login_to_umico(driver)

        # Запускаем обработку товаров
        asyncio.run(visit_products(driver))

    except Exception as e:
        print(f"Ошибка в основном потоке: {e}")
        logging.error(f"Ошибка в основном потоке: {e}")

    finally:
        driver.quit()
        print("Ты красавчик")
