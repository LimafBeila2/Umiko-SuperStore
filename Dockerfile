# Используем официальный образ Python
FROM python:3.12-slim

# Устанавливаем зависимости для работы с Chrome
RUN apt-get update && apt-get install -y \
    libxss1 \
    libappindicator3-1 \
    libindicator7 \
    fonts-liberation \
    libu2f-udev \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libgbm1 \
    xdg-utils \
    --no-install-recommends

# Устанавливаем pip и зависимости из requirements.txt
RUN python -m venv /opt/venv
RUN . /opt/venv/bin/activate && pip install --upgrade pip
COPY requirements.txt /app/requirements.txt
RUN . /opt/venv/bin/activate && pip install -r /app/requirements.txt

# Копируем приложение в контейнер
COPY . /app

# Устанавливаем переменные окружения для работы с виртуальным окружением
ENV PATH="/opt/venv/bin:$PATH"

# Указываем рабочую директорию
WORKDIR /app

# Запускаем ваше приложение
CMD ["python", "main.py"]
