import asyncio
import os
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
from dotenv import load_dotenv  # Для загрузки переменных из .env файла
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy import BigInteger, String, DateTime, Column
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Установите переменные окружения
PGHOST = os.getenv('PGHOST', 'postgres.railway.internal')
PGPORT = os.getenv('PGPORT', '5432')
PGUSER = os.getenv('PGUSER', 'postgres')
PGPASSWORD = os.getenv('PGPASSWORD', 'ilJVkITTuilDrVCNGqBaTzaMRMxhwOuI')
PGDATABASE = os.getenv('PGDATABASE', 'railway')

# Формирование строки подключения
DATABASE_URL = f"postgresql+asyncpg://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}"

# Создание двигателя и сессии
engine = create_async_engine(DATABASE_URL)

async_session = async_sessionmaker(engine)


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

# Создаем асинхронный движок и сессию для PostgreSQL
engine = create_async_engine(DATABASE_URL, echo=True, future=True)
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Функция для создания таблицы, если её нет
async def create_table():
    # Создаем таблицу только если она не существует
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Таблица успешно создана!")

# Пример асинхронной работы с базой
async def main():
    await create_table()

# Запуск асинхронного кода
if __name__ == "__main__":
    asyncio.run(main())
