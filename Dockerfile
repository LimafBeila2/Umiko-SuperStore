# Используем официальный образ Python
FROM python:3.12-slim

# Устанавливаем зависимости для работы с Chromium и Selenium
RUN apt-get update && apt-get install -y \
    bash \
    libxss1 \
    libappindicator3-1 \
    fonts-liberation \
    libu2f-udev \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libgbm1 \
    xdg-utils \
    wget \
    curl \
    unzip \
    chromium \
    chromium-driver \
    libx11-6 \
    libglib2.0-0 \
    libnss3 \
    libgdk-pixbuf2.0-0 \
    libatk1.0-0 \
    libgtk-3-0 \
    xvfb \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*  # Очистка кэша apt для уменьшения размера образа

# Создаем виртуальное окружение для Python
RUN python -m venv /opt/venv

# Обновляем pip в виртуальном окружении
RUN /opt/venv/bin/pip install --upgrade pip

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt /app/requirements.txt
RUN /opt/venv/bin/pip install -r /app/requirements.txt

# Явно устанавливаем chromedriver-autoinstaller и selenium-stealth
RUN /opt/venv/bin/pip install chromedriver-autoinstaller selenium-stealth==1.0.6

# Копируем все файлы приложения в контейнер
COPY . /selenium

# Устанавливаем переменные окружения для работы с виртуальным окружением
ENV PATH="/opt/venv/bin:$PATH"

# Устанавливаем переменные для использования Chromium в Selenium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Указываем рабочую директорию
WORKDIR /selenium

# Запускаем скрипт
CMD ["python", "main.py"]
