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
from selenium.webdriver.common.action_chains import ActionChains


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Заголовки запроса
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
}

# Папка для хранения профиля в контейнере Railway
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
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument",{
        'source':'''delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_JSON;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Object;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Proxy;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Window;
                    '''
    })
    logging.info("✅ WebDriver создан.")
    driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {"headers": headers})
    # Открываем страницу логина


    # Загружаем куки перед тем, как страница потребует авторизацию

    return driver
    # # Применяем stealth, чтобы скрыть использование Selenium
    # stealth(driver,
    #     user_agent=headers["User-Agent"],
    #     languages=["az", "ru"],
    #     timezone_id="Asia/Baku",
    #     platform="Win32"

    # Добавляем заголовки через CDP

def login_to_umico(driver):
    logging.info("Загружаем переменные окружения для авторизации...")
    load_dotenv()  # Загружаем переменные окружения из файла .env

    username = os.getenv("UMICO_USERNAME")
    password = os.getenv("UMICO_PASSWORD")

    if not username or not password:
        logging.error("Ошибка: логин или пароль не найдены в .env")
        raise ValueError("Ошибка: логин или пароль не найдены в .env")

    # Если куки есть, загружаем их

    # Переходим на страницу, чтобы проверить сессию
    driver.get("https://business.umico.az/sign-in")
    sleep(2)

    # Если мы не на странице входа, значит, мы уже авторизованы
    if check_if_logged_in(driver):
        logging.info("Мы уже авторизованы.")
        return

    logging.info("Открываем страницу авторизации Umico...")
    driver.get("https://business.umico.az/sign-in")
    sleep(1)
    # Ожидаем, пока появится поле для ввода логина
    login_input = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, "//input[@placeholder='İstifadəçi adı daxil edin']"))
    )
    login_input.send_keys(username)  # Вводим логин
    logging.info(f"Логин '{username}' введен.")
    sleep(1)
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
    except Exception as e:
        logging.error("Ошибка входа!")
        logging.exception(e)
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
    except Exception as e:
        logging.info("Окно выбора города не появилось.")
        logging.exception(e)

def check_if_logged_in(driver):
    current_url = driver.current_url
    if "sign-in" in current_url:
        logging.error(f"Не на правильной странице. Текущий URL: {current_url}")
        return False
    return True


def check_javascript_loaded(driver):
    try:
    def process_product(product, driver):
    try:
        logging.info(f"Начинаем обработку товара: {product['product_url']}")
        sleep(10)

        product_url, edit_url = product["product_url"], product["edit_url"]
        logging.info(f"Открываем страницу товара: {product_url}")
        driver.get(product_url)
        sleep(2)
        close_ad(driver)

        # Оставляем прежнюю часть без изменений (поиск минимальной цены и т.д.)...
        # ...

        # Переходим на страницу редактирования товара
        logging.info("Открываем страницу изменения цены...")
        login_to_umico(driver)
        sleep(5)
        driver.get(edit_url)
        logging.info(f"Открыта страница изменения цены: {edit_url}")

        # Проверяем, что страница полностью загружена
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        logging.info("Страница полностью загружена (document.readyState = 'complete').")

        # Дебаг - сохраняем всю страницу в файл
        page_source = driver.page_source
        with open("debug_edit_page.html", "w", encoding="utf-8") as f:
            f.write(page_source)
        logging.info("Сохранил HTML страницы в debug_edit_page.html")

        # Логируем количество input полей
        try:
            inputs = driver.find_elements(By.XPATH, "//input")
            logging.info(f"Найдено {len(inputs)} input полей.")
        except Exception as e:
            logging.error(f"Ошибка при поиске input полей: {e}")

        # Логируем все кнопки на странице
        all_buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in all_buttons:
            btn_text = btn.text or "Текста нет"
            btn_html = btn.get_attribute("outerHTML")
            logging.info(f"Найденная кнопка: Текст='{btn_text}' | HTML={btn_html}")

        # Проверка наличия изображения (если нужно)
        try:
            image_element = driver.find_element(By.XPATH, "//img[@src='https://strgimgr.umico.az/sized/1680/339754-1e8e2aff1a4ae183fc4080047729fab8.jpg']")
            if image_element.is_displayed():
                logging.info(f"Изображение найдено и отображается.")
            else:
                logging.info(f"Изображение найдено, но не отображается.")
        except Exception:
            logging.info(f"Изображение не найдено.")

        # Пробуем найти кнопку "Готово" (Hazır)
        try:
            save_button = WebDriverWait(driver, 60).until(
                EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(), 'Hazır')]]"))
            )
            save_button.click()
            logging.info("Кнопка 'Готово' была нажата.")
            sleep(10)
        except Exception as e:
            logging.error(f"Ошибка при нажатии кнопки 'Готово': {e}")
            current_url = driver.current_url
            logging.error(f"Текущий URL: {current_url}")

    except Exception as e:
        logging.exception(f"Ошибка при обработке товара: {e}")    # Ждем, пока не исчезнут индикаторы загрузки, если они есть
        WebDriverWait(driver, 30).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "loading-indicator"))  # Поменяйте на свой индикатор
        )
        logging.info("JavaScript загрузка завершена.")
    except Exception as e:
        logging.error(f"Ошибка при ожидании загрузки JavaScript: {e}")

def load_json(json_file):
    logging.info(f"Загружаем товары из файла {json_file}...")
    with open(json_file, "r", encoding="utf-8") as f:
        return json.load(f)

def process_products_from_json(json_file):
    logging.info("Создаем драйвер для обработки товаров...")
    driver = create_driver()  # Создаем драйвер один раз перед обработкой всех товаров
    try:
        products = load_json(json_file)
        for product in products:
            logging.info(f"Обрабатываем товар {product['product_url']}")
            process_product(product, driver)
    finally:
        driver.quit()  # Закрываем драйвер после обработки всех товаров

if __name__ == "__main__":
    while True:
        logging.info("Запускаем процесс обработки товаров...")
        process_products_from_json("product.json")
        logging.info("Работа завершена, повторная обработка через 60 секунд...")
        sleep(60)  # Пауза перед повторным запуском
