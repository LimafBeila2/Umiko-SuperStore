import asyncio
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import os

# Получаем строку подключения из переменной окружения
DATABASE_URL = os.getenv('Postgres_DATABASE_URL')

# Если строка подключения не найдена, можно подставить дефолтные значения
if DATABASE_URL is None:
    PGHOST = os.getenv('PGHOST', 'postgres.railway.internal')
    PGPORT = os.getenv('PGPORT', '5432')
    PGUSER = os.getenv('PGUSER', 'postgres')
    PGPASSWORD = os.getenv('PGPASSWORD', 'ilJVkITTuilDrVCNGqBaTzaMRMxhwOuI')
    PGDATABASE = os.getenv('PGDATABASE', 'railway')
    
    DATABASE_URL = f"postgresql+asyncpg://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}"
# Создаем базовый класс для таблиц
Base = declarative_base()

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

# Функция для проверки наличия таблицы и создания её, если нужно
async def create_table():
    async with engine.begin() as conn:
        # Проверка, существует ли таблица
        result = await conn.execute("SELECT to_regclass('public.products');")
        table_exists = result.scalar() is not None

        if not table_exists:
            # Если таблицы нет, создаем её
            await conn.run_sync(Base.metadata.create_all)
            print("Таблица успешно создана!")
        else:
            print("Таблица уже существует.")

# Пример асинхронной работы с базой
async def main():
    await create_table()

# Запуск асинхронного кода
if __name__ == "__main__":
    asyncio.run(main())
