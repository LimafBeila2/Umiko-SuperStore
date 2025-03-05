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
from sqlalchemy.exc import OperationalError
import time


# Настройки Chrome
options = Options()
options.binary_location = "/usr/bin/chromium"
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920x1080")

# Используем системный chromedriver
service = Service("/usr/bin/chromedriver")

# Создаем веб-драйвер
driver = webdriver.Chrome(service=service, options=options)

# Функция для входа в аккаунт Umico Business с использованием данных из .env
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


# Функция для получения ссылок на товары из базы данных
async def get_product_urls():
    async with async_session() as session:
        async with session.begin():
            # Выполняем запрос для получения всех продуктов
            result = await session.execute(select(Product.id, Product.product_url, Product.edit_url))
            products = result.fetchall()  # Получаем все строки
            return products  # Возвращаем список кортежей с данными (id, product_url, edit_url)


# Функция для закрытия рекламы на странице
async def close_ad(driver):
    try:
        baku_option = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Баку' or text()='Bakı']"))
        )
        baku_option.click()
        print("Город Баку выбран.")
    except Exception:
        print("Окно выбора города не появилось, продолжаем выполнение кода.")


def click_element_by_text(text1, text2):
    # Используем XPath с условием "или" для поиска обоих текстов
    element = driver.find_element(By.XPATH, f"//a[contains(text(), '{text1}') or contains(text(), '{text2}')]")
    actions = ActionChains(driver)
    actions.move_to_element(element).perform()
    element.click()


# Функция для проверки существования таблицы в базе данных
async def wait_for_table_creation():
    max_retries = 10
    retries = 0
    while retries < max_retries:
        try:
            async with async_session() as session:
                async with session.begin():
                    # Проверяем наличие таблицы, выполняя запрос
                    result = await session.execute(select(Product.id).limit(1))  # Просто пробуем запросить данные
                    result.fetchall()  # Проверка, есть ли записи
                    print("Таблица существует!")
                    return True
        except OperationalError:
            # Если таблица не существует, ждем некоторое время и пробуем снова
            print("Таблица не существует, ждем...")
            retries += 1
            await asyncio.sleep(3)  # Используем асинхронный sleep
    print("Не удалось найти таблицу после нескольких попыток.")
    return False


# Функция для обновления цены товара в базе данных
async def update_product_price_in_db(product_to_update, new_price):
    async with async_session() as session:
        async with session.begin():
            product_to_update.current_price = new_price
            await session.commit()
            print(f"Цена товара обновлена в базе на {new_price} ₼")


# Основная функция для обработки каждого товара
async def process_product(driver, product):
    try:
        # Извлекаем данные из product (кортеж, а не объект Product)
        product_url = product[1]  # Позиция 1 — это product_url
        print(f"Обрабатываем товар: {product_url}")

        driver.get(product_url)
        await asyncio.sleep(2)  # Ждем загрузки страницы

        # Закрытие рекламы
        await close_ad(driver)

        # Кликаем по ссылке "Посмотреть цены всех продавцов" на разных языках
        click_element_by_text("Bütün satıcıların qiymətlərinə baxmaq", "Посмотреть цены всех продавцов")

        # Ожидаем загрузки блока с товарами
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "MPProductOffer")))

        # Находим все блоки товаров
        product_offers = driver.find_elements(By.CLASS_NAME, "MPProductOffer")

        # Переменные для отслеживания самой низкой цены и магазина
        lowest_price = float('inf')
        lowest_price_merchant = ""
        super_store_price = None

        # Парсим данные по каждому товару
        for product_offer in product_offers:
            try:
                merchant = product_offer.find_element(By.CLASS_NAME, "NameMerchant").text.strip()
                price_text = None
                price_element = None

                try:
                    price_element = product_offer.find_element(By.XPATH, ".//span[@data-info='item-desc-price-new']")
                except:
                    try:
                        price_element = product_offer.find_element(By.XPATH, ".//span[@data-info='item-desc-price-old']")
                    except:
                        continue

                if price_element:
                    price_text = price_element.text.strip().replace("₼", "").strip()

                if price_text:
                    price = float(price_text)

                    if merchant == "Super Store":
                        super_store_price = price

                    if price < lowest_price:
                        lowest_price = price
                        lowest_price_merchant = merchant

            except Exception as e:
                print(f"Ошибка при обработке товара: {e}")
                continue

        # Выводим результаты
        print(f"Самая низкая цена: {lowest_price} от магазина {lowest_price_merchant}")
        if super_store_price is not None:
            print(f"Цена от Super Store: {super_store_price}")

        # Обновление базы данных и изменение цены, если нужно
        async with async_session() as session:
            async with session.begin():
                result = await session.execute(select(Product).filter(Product.product_url == product_url))
                product_to_update = result.scalars().first()

                if product_to_update:
                    product_to_update.last_checked_price = lowest_price  # Обновляем самую низкую цену конкурента

                    # Сравниваем с ценой Super Store и обновляем, если нужно
                    if lowest_price < super_store_price:
                        print("Цена конкурента ниже, открываем ссылку для изменения цены.")
                        driver.get(product_to_update.edit_url)  # Открываем ссылку для изменения
                        await asyncio.sleep(5)

                        # Обновляем цену
                        new_price = round(lowest_price - 0.01, 2)
                        discount_price_input = WebDriverWait(driver, 20).until(
                            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Скидочная цена']"))
                        )
                        discount_price_input.clear()
                        discount_price_input.send_keys(str(new_price))
                        print(f"Новая цена товара: {new_price} ₼")

                        # Сохраняем изменения
                        save_button = WebDriverWait(driver, 30).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[span[text()='Готово']]"))
                        )
                        save_button.click()
                        print("Цена успешно обновлена на сайте.")

                        # Обновляем цену в базе данных
                        await update_product_price_in_db(product_to_update, new_price)

    except Exception as e:
        logging.error(f"Ошибка при обработке товара: {product[1]}: {e}")


# Основная функция для посещения товаров
async def visit_products(driver):
    if await wait_for_table_creation():  # Проверяем, существует ли таблица
        products = await get_product_urls()  # Получаем все товары из базы данных

        for product in products:
            await process_product(driver, product)
    else:
        print("Ошибка: таблица не существует. Завершаем работу.")


if __name__ == "__main__":
    try:
        # Входим в Umico Business
        login_to_umico(driver)
        # Запускаем процесс проверки и обновления цен
        asyncio.run(visit_products(driver))

    finally:
        # Закрываем драйвер после завершения всех операций
        driver.quit()