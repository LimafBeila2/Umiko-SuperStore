import os
import logging
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

# Настроим логирование
logging.basicConfig(level=logging.INFO)

# Функция для создания драйвера
def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Запуск в фоновом режиме (без открытия окна)
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)
    return driver

# Функция закрытия рекламы
def close_ad(driver):
    try:
        ad_close_button = driver.find_element(By.XPATH, "//button[@class='close']")
        ad_close_button.click()
        logging.info("Реклама закрыта.")
    except Exception as e:
        logging.warning(f"Ошибка при закрытии рекламы: {e}")

# Функция авторизации на Umico
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
    return driver.current_url == "https://business.umico.az/sign-in"

# Функция обработки товаров
def process_product(product):
    driver = create_driver()
    try:
        product_url, edit_url = product["product_url"], product["edit_url"]
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
            return

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

            # Пытаемся перейти на страницу редактирования
            driver.get(edit_url)
            sleep(5)

            # Проверяем, если текущий URL - это страница входа, выполняем логин
            current_url = driver.current_url
            if "sign-in" in current_url:
                logging.info("Необходима авторизация для изменения цены.")
                driver = login_to_umico(driver)  # Входим в систему, если это страница входа
            elif "edit" in current_url or "product" in current_url:
                logging.info("Страница редактирования товара. Продолжаем изменение цены.")

            try:
                # Находим элемент с чекбоксом "Скидка" или "Endirim" (для двух языков)
                discount_checkbox = WebDriverWait(driver, 100).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Скидка') or contains(text(), 'Endirim')]//preceding-sibling::div[contains(@class, 'tw-border-')]"))
                )

                # Если галочка не установлена, ставим её
                if 'tw-border-umico-brand-main-brand' not in discount_checkbox.get_attribute('class'):
                    discount_checkbox.click()
                    logging.info("Галочка на скидку поставлена.")

                # Ждем появления поля для ввода скидочной цены (на двух языках)
                discount_input = WebDriverWait(driver, 100).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Скидочная цена' or @placeholder='Endirimli qiymət']"))
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
            except Exception as e:
                logging.error(f"Ошибка при установке скидочной цены: {e}")

    except Exception as e:
        logging.exception(f"Ошибка при обработке товара {product_url}: {e}")
    finally:
        driver.quit()
