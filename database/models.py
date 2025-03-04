import asyncio
import os
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv  # Для загрузки переменных из .env файла

# Загружаем переменные окружения из .env файла
load_dotenv()

# Переменные окружения для подключения к PostgreSQL
PGHOST = os.getenv('PGHOST', 'postgres.railway.internal')
PGPORT = os.getenv('PGPORT', '5432')
PGUSER = os.getenv('PGUSER', 'postgres')
PGPASSWORD = os.getenv('PGPASSWORD', 'TvqEqqIEIMZPFqEmIqgSgjoqQPwqzhfu')
PGDATABASE = os.getenv('PGDATABASE', 'railway')

# Формирование строки подключения
DATABASE_URL = f"postgresql+asyncpg://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}"

# Создание асинхронного движка и сессии
engine = create_async_engine(DATABASE_URL, echo=True)
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

# Функция для создания таблицы
async def create_table():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Таблица успешно создана!")

# Асинхронный запуск
async def main():
    await create_table()

if __name__ == "__main__":
    asyncio.run(main())
