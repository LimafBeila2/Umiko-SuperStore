import asyncio
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine import reflection
from datetime import datetime
import os


# Установите переменные окружения
PGHOST = os.getenv('PGHOST', 'postgres.railway.internal')
PGPORT = os.getenv('PGPORT', '5432')
PGUSER = os.getenv('PGUSER', 'postgres')
PGPASSWORD = os.getenv('PGPASSWORD', 'ilJVkITTuilDrVCNGqBaTzaMRMxhwOuI')
PGDATABASE = os.getenv('PGDATABASE', 'railway')


# Настройки базы данных PostgreSQL
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

# Функция для проверки наличия таблицы и создания ее, если нужно
async def create_table():
    # Подключаемся к базе и проверяем наличие таблицы
    async with engine.connect() as conn:
        insp = reflection.Inspector.from_engine(conn)
        if 'products' not in insp.get_table_names():
            # Если таблицы нет, создаем
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
