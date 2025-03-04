import asyncio
import os
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
from dotenv import load_dotenv  # Для загрузки переменных из .env файла

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем строку подключения из переменных окружения
PGHOST = os.getenv('PGHOST', 'postgres.railway.internal')
PGPORT = os.getenv('PGPORT', '5432')
PGUSER = os.getenv('PGUSER', 'postgres')
PGPASSWORD = os.getenv('PGPASSWORD', 'ilJVkITTuilDrVCNGqBaTzaMRMxhwOuI')
PGDATABASE = os.getenv('PGDATABASE', 'railway')

# Формирование строки подключения
DATABASE_URL = f"postgresql+asyncpg://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}"

# Выводим переменные для проверки
print(f"PGHOST: {PGHOST}")
print(f"PGPORT: {PGPORT}")
print(f"PGUSER: {PGUSER}")
print(f"PGDATABASE: {PGDATABASE}")

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
    async with engine.connect() as conn:
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
