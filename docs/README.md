# AI База Данных Товаров

Веб-платформа для управления базой данных товаров с использованием искусственного интеллекта.

## 🚀 Возможности

- **Чат с ИИ**: Общение на естественном языке для поиска, добавления и редактирования товаров
- **Умная загрузка данных**: Автоматическое маппинг колонок Excel с помощью ИИ
- **Управление товарами**: Просмотр, редактирование и фильтрация товаров в удобной таблице
- **Экспорт данных**: Скачивание отчетов в Excel формате
- **Хранение изображений**: Автоматическая загрузка фото товаров в S3

## 🛠 Технологии

### Backend
- **Python 3.9+** с FastAPI
- **PostgreSQL** для базы данных
- **SQLAlchemy** для ORM
- **OpenAI API** для ИИ-функций
- **Amazon S3** для хранения изображений

### Frontend
- **Vue.js 3** с Composition API
- **PrimeVue V4** для UI компонентов
- **Axios** для API запросов
- **Vue Router** для навигации

## 📋 Требования

- Python 3.9+
- Node.js 16+
- PostgreSQL 13+
- OpenAI API ключ
- AWS аккаунт (для S3)

## 🚀 Быстрый запуск

### 1. Клонирование репозитория
```bash
git clone <repository-url>
cd ai-database
```

### 2. Backend

```bash
# Установка зависимостей
cd backend
pip install -r requirements.txt

# Настройка переменных окружения
cp .env.example .env
# Отредактируйте .env файл с вашими ключами

# Создание базы данных
createdb ai_database

# Применение схемы
psql -d ai_database -f ../database/schema.sql

# Запуск сервера
uvicorn app:app --reload
```

### 3. Frontend

```bash
# Установка зависимостей
cd frontend
npm install

# Запуск dev сервера
npm run serve
```

### 4. Доступ

- **Frontend**: http://localhost:8080
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## ⚙️ Настройка

### Переменные окружения (.env)

```env
# OpenAI
OPENAI_API_KEY=your_openai_api_key

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ai_database

# AWS S3
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=us-east-1
S3_BUCKET=your-bucket-name
```

## 📖 Использование

### Загрузка данных
1. Перейдите на страницу "Файлы"
2. Загрузите Excel файл с товарами
3. ИИ автоматически предложит маппинг колонок
4. Проверьте и скорректируйте маппинг при необходимости
5. Подтвердите загрузку

### Работа с данными
1. Перейдите на страницу "Данные"
2. Используйте фильтры для поиска товаров
3. Редактируйте товары inline или через диалог
4. Экспортируйте данные в Excel

### Чат с ИИ
1. Перейдите на страницу "Чат"
2. Введите запрос на естественном языке
3. Примеры запросов:
   - "Найди все товары красного цвета"
   - "Добавь новый товар с названием X"
   - "Покажи товары бренда Adidas"

## 🏗 Архитектура

```
ai-database/
├── backend/
│   ├── app.py                 # Основное приложение
│   ├── models.py             # SQLAlchemy модели
│   ├── routes/
│   │   ├── api.py           # CRUD операции
│   │   ├── chat.py          # Чат с ИИ
│   │   └── files.py         # Загрузка файлов
│   └── services/
│       ├── ai_service.py     # OpenAI интеграция
│       ├── excel_processor.py # Обработка Excel
│       └── s3_service.py     # AWS S3
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── DataEditor.vue    # Редактор данных
│   │   │   └── ColumnMapper.vue  # Маппинг колонок
│   │   ├── pages/
│   │   │   ├── ChatPage.vue      # Чат
│   │   │   ├── DataPage.vue      # Данные
│   │   │   └── FilesPage.vue     # Файлы
│   │   └── services/
│   │       └── apiService.js     # API клиент
│   └── public/
└── database/
    ├── schema.sql           # Схема БД
    └── migrations/          # Миграции
```

## 🔒 Безопасность

- SQL-инъекции предотвращены через параметризованные запросы
- Валидация входных данных
- Ограничение размера файлов
- CORS настройки для frontend

## 📝 API Endpoints

### Продукты
- `GET /api/products` - Получение списка товаров
- `POST /api/products` - Создание товара
- `PUT /api/products/{id}` - Обновление товара
- `DELETE /api/products/{id}` - Удаление товара
- `GET /api/products/export` - Экспорт в Excel

### Чат
- `POST /api/chat/query` - Отправка запроса ИИ

### Файлы
- `POST /api/upload/excel` - Загрузка Excel
- `POST /api/upload/images` - Загрузка изображений
- `POST /api/upload/confirm-mapping` - Подтверждение маппинга

## 🤝 Contributing

1. Fork проект
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## 📄 Лицензия

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE) для деталей.

## 📞 Контакты

- Email: your-email@example.com
- Project Link: [https://github.com/your-username/ai-database](https://github.com/your-username/ai-database)
