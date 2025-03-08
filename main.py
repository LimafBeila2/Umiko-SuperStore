import json
import logging
from time import sleep
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from subprocess import Popen

# Логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def create_driver():
    logging.info("Создаем драйвер Chrome...")
    options = Options()
    options.binary_location = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920x1080")
    service = Service(ChromeDriverManager().install())
    logging.info("Драйвер Chrome успешно создан.")
    return webdriver.Chrome(service=service, options=options)

def load_json(filename):
    logging.info(f"Загружаем данные из файла: {filename}")
    with open(filename, "r", encoding="utf-8") as file:
        data = json.load(file)
    logging.info(f"Данные из файла {filename} успешно загружены.")
    return data

def close_ad(driver):
    try:
        logging.info("Пытаемся закрыть рекламу...")
        baku_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Баку' or text()='Bakı']"))
        )
        baku_option.click()
        logging.info("Город Баку выбран.")
    except:
        logging.info("Окно выбора города не появилось.")

def process_product(product):
    logging.info(f"Обрабатываем товар: {product['product_url']}")
    driver = create_driver()
    try:
        product_url = product["product_url"]
        driver.get(product_url)
        sleep(2)
        
        if "404" in driver.title:
            logging.warning(f"Страница 404 для товара {product_url}. Пропускаем товар.")
            return None, None, None
        
        close_ad(driver)
        
        try:
            button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Посмотреть цены всех продавцов') or contains(text(), 'Bütün satıcıların qiymətlərinə baxmaq')]"))
            )
            button.click()
            logging.info("Нажата кнопка 'Посмотреть цены всех продавцов'.")
        except:
            logging.warning(f"Не удалось найти кнопку для просмотра цен для товара {product_url}.")
            return None, None, None
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "MPProductOffer"))
        )
        
        product_offers = driver.find_elements(By.CLASS_NAME, "MPProductOffer")
        if not product_offers:
            logging.warning(f"Нет предложений по товару {product_url}.")
            return None, None, None
        
        lowest_price = float('inf')
        lowest_price_merchant = ""
        
        for offer in product_offers:
            try:
                merchant = offer.find_element(By.CLASS_NAME, "NameMerchant").text.strip()
                
                try:
                    price_text = offer.find_element(By.XPATH, ".//span[@data-info='item-desc-price-new']").text.strip()
                except:
                    price_text = offer.find_element(By.XPATH, ".//span[@data-info='item-desc-price-old']").text.strip()

                price = float(price_text.replace("₼", "").strip())

                if price < lowest_price:
                    lowest_price = price
                    lowest_price_merchant = merchant
            
            except Exception as e:
                logging.warning(f"Ошибка при обработке предложения для товара {product_url}: {e}")
                continue
        
        logging.info(f"Самая низкая цена для товара {product_url}: {lowest_price} от {lowest_price_merchant}")
        return lowest_price, product.get("competitor_url"), product.get("edit_url")
        
    except Exception as e:
        logging.exception(f"Ошибка при обработке товара {product['product_url']}: {e}")
    finally:
        driver.quit()
    return None, None, None

def get_competitor_price(competitor_url):
    logging.info(f"Получаем цену у конкурента: {competitor_url}")
    driver = create_driver()
    try:
        driver.get(competitor_url)
        sleep(2)
        
        if "404" in driver.title:
            logging.warning(f"Страница 404 у конкурента {competitor_url}. Пропускаем.")
            return None
        
        competitor_price_text = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "product-price"))
        ).text.strip()
        competitor_price = float(competitor_price_text.replace("₼", "").strip())
        logging.info(f"Цена у конкурента {competitor_url}: {competitor_price}")
        return competitor_price
    except Exception as e:
        logging.error(f"Ошибка при получении цены с сайта конкурента {competitor_url}: {e}")
        return None
    finally:
        driver.quit()

def process_price_update(lowest_price, competitor_price, edit_url):
    if lowest_price < competitor_price:
        logging.info(f"Цена товара ниже, чем у конкурента. Запускаем процесс изменения цены.")
        
        with open("edit_url.txt", "w", encoding="utf-8") as file:
            file.write(edit_url)
        logging.info(f"Записан URL для изменения цены: {edit_url}")
        
        process = Popen(["python", "main2.py"])
        process.communicate()
        logging.info("Процесс изменения цены успешно запущен.")
    else:
        logging.info("Самая низкая цена у Super Store. Пропускаем.")

def process_products_from_json(json_file):
    logging.info(f"Обрабатываем продукты из файла {json_file}.")
    products = load_json(json_file)
    for product in products:
        lowest_price, competitor_url, edit_url = process_product(product)
        
        if lowest_price and competitor_url and edit_url:
            competitor_price = get_competitor_price(competitor_url)
            
            if competitor_price:
                process_price_update(lowest_price, competitor_price, edit_url)
            else:
                logging.warning(f"Не удалось получить цену конкурента для товара {product['product_url']}")
    logging.info("Обработка всех товаров завершена.")

if __name__ == "__main__":
    process_products_from_json("product.json")
    logging.info("Работа завершена!")
