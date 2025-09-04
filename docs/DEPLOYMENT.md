# Руководство по развертыванию AI Database Platform

## Обзор
Это руководство описывает процесс развертывания AI-платформы управления базой данных товаров на сервере Ubuntu с использованием Docker.

## Требования к серверу
- Ubuntu 20.04+ (рекомендуется 22.04 LTS)
- Минимум 2GB RAM, 20GB диск
- Доступ по SSH
- Зарегистрированный домен (databaseprotrade.ru)

## Предварительная подготовка

### 1. Обновление системы
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Установка Docker и Docker Compose
```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Перезагрузка для применения группы docker
newgrp docker
```

### 3. Установка Git
```bash
sudo apt install git -y
```

### 4. Настройка firewall (UFW)
```bash
sudo ufw allow OpenSSH
sudo ufw allow 80
sudo ufw allow 443
sudo ufw --force enable
```

## Развертывание приложения

### 1. Клонирование репозитория
```bash
cd ~
git clone https://github.com/your-username/ai-database.git
cd ai-database
```

### 2. Настройка переменных окружения
```bash
cp .env.example .env
nano .env
```

Заполните следующие переменные:
```env
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password_here

# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here

# S3 Storage (TWC Storage)
AWS_ACCESS_KEY_ID=acbf9e7f-efdb1b36-1938-485f-b86a-dc6b003ee974
AWS_SECRET_ACCESS_KEY=5BO23VCSBOCQZWIYZI87
S3_ENDPOINT_URL=https://s3.twcstorage.ru
S3_BUCKET_NAME=your_bucket_name_here
S3_REGION=ru-1

# Application
DOMAIN=databaseprotrade.ru
SERVER_IP=5.129.243.122
```

### 3. Настройка SSL сертификатов

#### Вариант 1: Let's Encrypt (рекомендуется)
```bash
# Установка certbot
sudo apt install snapd -y
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot

# Получение сертификатов
sudo certbot certonly --standalone -d databaseprotrade.ru -d www.databaseprotrade.ru

# Создание символических ссылок для nginx
sudo mkdir -p /home/$USER/ai-database/nginx/ssl
sudo ln -s /etc/letsencrypt/live/databaseprotrade.ru/fullchain.pem /home/$USER/ai-database/nginx/ssl/fullchain.pem
sudo ln -s /etc/letsencrypt/live/databaseprotrade.ru/privkey.pem /home/$USER/ai-database/nginx/ssl/privkey.pem
```

#### Вариант 2: Самоподписанный сертификат (для тестирования)
```bash
sudo mkdir -p /home/$USER/ai-database/nginx/ssl
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /home/$USER/ai-database/nginx/ssl/privkey.pem \
    -out /home/$USER/ai-database/nginx/ssl/fullchain.pem \
    -subj "/C=RU/ST=State/L=City/O=Organization/CN=databaseprotrade.ru"
```

### 4. Запуск приложения
```bash
# Сборка и запуск в фоне
docker-compose -f docker-compose.prod.yml up -d --build

# Проверка статуса
docker-compose -f docker-compose.prod.yml ps
```

### 5. Проверка развертывания
```bash
# Проверка логов
docker-compose -f docker-compose.prod.yml logs -f

# Проверка доступности
curl -k https://databaseprotrade.ru/health
curl -k https://databaseprotrade.ru/
```

## Настройка домена

### 1. DNS записи
Добавьте следующие A-записи в DNS вашего домена:
```
databaseprotrade.ru     A     5.129.243.122
www.databaseprotrade.ru A     5.129.243.122
```

### 2. Проверка DNS
```bash
nslookup databaseprotrade.ru
```

## Мониторинг и обслуживание

### Просмотр логов
```bash
# Все сервисы
docker-compose -f docker-compose.prod.yml logs -f

# Конкретный сервис
docker-compose -f docker-compose.prod.yml logs -f backend
```

### Обновление приложения
```bash
# Остановка
docker-compose -f docker-compose.prod.yml down

# Обновление кода
git pull origin main

# Перезапуск
docker-compose -f docker-compose.prod.yml up -d --build
```

### Резервное копирование базы данных
```bash
# Создание бэкапа
docker exec -t ai-database_db_1 pg_dump -U postgres -d ai_database > backup_$(date +%Y%m%d_%H%M%S).sql

# Восстановление из бэкапа
docker exec -i ai-database_db_1 psql -U postgres -d ai_database < backup_file.sql
```

## Безопасность

### 1. Регулярные обновления
```bash
# Обновление Docker образов
docker-compose -f docker-compose.prod.yml pull

# Обновление системы
sudo apt update && sudo apt upgrade -y
```

### 2. Мониторинг ресурсов
```bash
# Использование диска
df -h

# Использование памяти
docker stats

# Логи nginx
docker-compose -f docker-compose.prod.yml logs nginx
```

## Troubleshooting

### Проблема: Сервис не запускается
```bash
# Проверка логов
docker-compose -f docker-compose.prod.yml logs <service_name>

# Перезапуск сервиса
docker-compose -f docker-compose.prod.yml restart <service_name>
```

### Проблема: Ошибка подключения к БД
```bash
# Проверка статуса БД
docker-compose -f docker-compose.prod.yml ps db

# Проверка логов БД
docker-compose -f docker-compose.prod.yml logs db
```

### Проблема: SSL сертификат истек
```bash
# Продление Let's Encrypt
sudo certbot renew

# Перезапуск nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

## Контакты
При возникновении проблем обратитесь к разработчику или создайте issue в репозитории.
