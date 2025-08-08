# Dockerfile для test automation framework
FROM mcr.microsoft.com/playwright/python:v1.45.0-focal

# Установка рабочей директории
WORKDIR /app

# Копирование файлов проекта
COPY pyproject.toml poetry.lock ./

# Установка Poetry
RUN pip install poetry==1.7.1

# Настройка Poetry для не создания виртуального окружения в контейнере
RUN poetry config virtualenvs.create false

# Установка зависимостей
RUN poetry install --no-dev --no-interaction --no-ansi

# Установка Playwright браузеров (уже установлены в базовом образе)
# RUN playwright install

# Копирование исходного кода
COPY src/ ./src/
COPY tests/ ./tests/
COPY .env.example ./.env

# Создание директорий для отчетов и логов
RUN mkdir -p /app/reports /app/logs

# Установка переменных окружения для контейнера
ENV ENVIRONMENT=testing
ENV BROWSER__HEADLESS=true
ENV BROWSER__ARGS="--no-sandbox,--disable-dev-shm-usage,--disable-gpu"
ENV LOG_LEVEL=INFO

# Создание пользователя для запуска тестов (безопасность)
RUN groupadd -r testuser && useradd -r -g testuser testuser
RUN chown -R testuser:testuser /app
USER testuser

# Healthcheck для проверки готовности контейнера
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.config.settings import get_settings; get_settings()" || exit 1

# Команда по умолчанию
CMD ["python", "-m", "pytest", "tests/", "-v", "--tb=short"]

# docker-compose.yml
---
version: '3.8'

services:
  # Основное приложение Sock Shop для тестирования
  sock-shop:
    image: microservicesdemomesh/front-end:latest
    ports:
      - "8080:8080"
    environment:
      - NODE_ENV=production
    depends_on:
      - catalogue
      - user
      - cart
      - orders
      - payment
      - shipping
    networks:
      - sock-shop-net
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Catalogue service
  catalogue:
    image: microservicesdemomesh/catalogue:latest
    ports:
      - "8081:80"
    networks:
      - sock-shop-net
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:80/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # User service
  user:
    image: microservicesdemomesh/user:latest
    ports:
      - "8082:80"
    networks:
      - sock-shop-net
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:80/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Cart service
  cart:
    image: microservicesdemomesh/carts:latest
    ports:
      - "8083:80"
    networks:
      - sock-shop-net

  # Orders service
  orders:
    image: microservicesdemomesh/orders:latest
    ports:
      - "8084:80"
    networks:
      - sock-shop-net

  # Payment service
  payment:
    image: microservicesdemomesh/payment:latest
    ports:
      - "8085:80"
    networks:
      - sock-shop-net

  # Shipping service
  shipping:
    image: microservicesdemomesh/shipping:latest
    ports:
      - "8086:80"
    networks:
      - sock-shop-net

  # Test automation framework
  test-framework:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - ENVIRONMENT=testing
      - SOCK_SHOP_BASE_URL=http://sock-shop:8080
      - API_BASE_URL=http://sock-shop:8080/api
      - BROWSER__HEADLESS=true
      - BROWSER__NAME=chromium
      - TEST__PARALLEL_WORKERS=4
      - LOG_LEVEL=INFO
    volumes:
      - ./reports:/app/reports
      - ./logs:/app/logs
      - ./test-results:/app/test-results
    depends_on:
      sock-shop:
        condition: service_healthy
      catalogue:
        condition: service_healthy
      user:
        condition: service_healthy
    networks:
      - sock-shop-net
    command: >
      sh -c "
        echo 'Waiting for Sock Shop to be ready...' &&
        sleep 10 &&
        python -m pytest tests/
          -v
          --tb=short
          --html=reports/report.html
          --self-contained-html
          --alluredir=reports/allure-results
          --maxfail=5
      "

  # Test framework в режиме разработки с возможностью отладки
  test-framework-dev:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - ENVIRONMENT=development
      - SOCK_SHOP_BASE_URL=http://sock-shop:8080
      - API_BASE_URL=http://sock-shop:8080/api
      - BROWSER__HEADLESS=false
      - BROWSER__NAME=chromium
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    volumes:
      - .:/app
      - ./reports:/app/reports
      - ./logs:/app/logs
    depends_on:
      sock-shop:
        condition: service_healthy
    networks:
      - sock-shop-net
    ports:
      - "5678:5678"  # Для remote debugging
    command: >
      sh -c "
        echo 'Development mode - interactive shell' &&
        /bin/bash
      "

  # Allure reporting service
  allure-ui:
    image: frankescobar/allure-docker-service-ui:latest
    environment:
      - ALLURE_DOCKER_PUBLIC_API_URL=http://allure:5050
    ports:
      - "5252:5252"
    depends_on:
      - allure
    networks:
      - sock-shop-net

  allure:
    image: frankescobar/allure-docker-service:latest
    environment:
      - CHECK_RESULTS_EVERY_SECONDS=3
      - KEEP_HISTORY=25
    ports:
      - "5050:5050"
    volumes:
      - ./reports/allure-results:/app/allure-results
      - ./reports/allure-reports:/app/default-reports
    networks:
      - sock-shop-net

networks:
  sock-shop-net:
    driver: bridge

volumes:
  test-results:
  allure-results:
  allure-reports: