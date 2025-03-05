import asyncio
import os
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv  # Для загрузки переменных из .env файла

# Загружаем переменные окружения из .env файл
load_dotenv()

# Установите переменные окружения
PGHOST = os.getenv('PGHOST', 'crossover.proxy.rlwy.net')  # Новый хост
PGPORT = os.getenv('PGPORT', '25898')  # Новый порт
PGUSER = os.getenv('PGUSER', 'postgres')
PGPASSWORD = os.getenv('PGPASSWORD', 'xRaUWyniDrKbOcbJGTFLcgiZTYEDfAck')
PGDATABASE = os.getenv('PGDATABASE', 'railway')

# Формирование строки подключения
DATABASE_URL = f"postgresql+asyncpg://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}"

# Выводим переменные для проверки
print("PGHOST:", PGHOST)
print("PGUSER:", PGUSER)
print("PGPASSWORD:", PGPASSWORD)
print("PGDATABASE:", PGDATABASE)
print("DATABASE_URL:", DATABASE_URL)

# Создание асинхронного движка и сессии
engine = create_async_engine(DATABASE_URL, echo=True)

# Сессия для работы с базой данных
async_session = async_sessionmaker(engine, expire_on_commit=False)

# Базовый класс для моделей
class Base(AsyncAttrs, DeclarativeBase):
    pass

# Определяем модель таблицы для товаров
class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_url = Column(String, nullable=False)
    edit_url = Column(String, nullable=False)
    current_price = Column(Float, nullable=False)
    last_checked_price = Column(Float)
    last_checked = Column(DateTime, default=datetime.utcnow)

# Функция для создания таблицы с обработкой ошибок
async def create_table():
    try:
        # Проверяем соединение с базой данных и создаем таблицу
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Таблица успешно создана!")

        # Вставляем данные в таблицу
        async with async_session() as session:
            # Создание объекта товара с данными
            product = Product(
                id=339754,
                product_url="https://umico.az/product/339754-qadinlar-uchun-tualet-suyu-bvlgari-omnia-coral-65-ml",
                edit_url="https://business.umico.az/account/products/my/2576516",
                current_price=1.0,
                last_checked_price=1.0,
                last_checked=datetime(2025, 3, 5, 19, 39, 14)
            )
            session.add(product)  # Добавляем объект в сессию
            await session.commit()  # Сохраняем в базу данных
        print("Данные успешно добавлены в таблицу!")
    except Exception as e:
        print(f"Ошибка при создании таблицы или вставке данных: {e}")
        # Дополнительная диагностика:
        print("Проверьте, существует ли база данных и корректны ли права доступа.")

# Асинхронный запуск
async def main():
    await create_table()

if __name__ == "__main__":
    try:
        asyncio.run(main())  # Запуск основного процесса
    except Exception as e:
        print(f"Ошибка при запуске асинхронного процесса: {e}")
