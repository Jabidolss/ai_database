import openai
import json
import os
import logging
import httpx
from typing import Dict, List, Optional
from pydantic import BaseModel
from openai import AsyncOpenAI

# Прокси настройки из окружения (опционально)
PROXY_URL = os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")

# Схема БД для промптов (специализированная база данных очков)
DB_SCHEMA = """
Таблица products (очки):
- id (SERIAL PRIMARY KEY)
- images (TEXT) - ссылки на изображения очков в S3
- manufacturer_name (VARCHAR) - производитель очков
- part_number (VARCHAR) - артикул модели очков
- part_name (VARCHAR) - название модели очков
- category (VARCHAR) - бренд очков (Gucci, Ray-Ban, Prada и т.д.)
- type (VARCHAR) - тип очков (солнцезащитные, для чтения, компьютерные и т.д.)
- size (VARCHAR) - размер очков
- color (VARCHAR) - цвет оправы/линз
- brand (VARCHAR) - бренд (дублирует category для совместимости)
- producer (VARCHAR) - производитель (может отличаться от бренда)
- gender (VARCHAR) - пол (мужские, женские, унисекс)
- width (NUMERIC) - ширина оправы в мм
- height (NUMERIC) - высота линзы в мм
- age (VARCHAR) - возрастная группа
- shape (VARCHAR) - форма оправы (круглые, квадратные, авиаторы и т.д.)
- year (INTEGER) - год выпуска модели

ВАЖНО: Это база данных ТОЛЬКО для очков. Категории представляют бренды очков.
"""

class AiService:
    def __init__(self):
        # Настраиваем httpx клиент с жёстко указанным прокси
        logger = logging.getLogger(__name__)
        if PROXY_URL:
            logger.info(f"Используется прокси для OpenAI: {PROXY_URL}")
            http_client = httpx.AsyncClient(proxy=PROXY_URL, timeout=30)
        else:
            http_client = httpx.AsyncClient(timeout=30)

        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            http_client=http_client
        )
        if not self.client.api_key:
            raise ValueError("OPENAI_API_KEY не установлена")

    async def map_columns(self, excel_columns: List[str], user_mapping_rules: Dict[str, List[str]] = None) -> Dict[str, str]:
        """Маппинг колонок Excel к полям БД с помощью ИИ и пользовательских правил"""
        db_fields = [
            "images", "manufacturer_name", "part_number", "part_name", "category",
            "type", "size", "color", "brand", "producer", "gender", "width",
            "height", "age", "shape", "year"
        ]

        prompt = f"""
Ты эксперт по интеллектуальному маппингу данных очков. Твоя задача - точно сопоставить колонки Excel файла с полями базы данных очков.

ВАЖНО: Это база данных ИСКЛЮЧИТЕЛЬНО для очков. Все данные относятся к очкам (солнцезащитные, оптические, для чтения и т.д.).

СХЕМА БАЗЫ ДАННЫХ ОЧКОВ:
{DB_SCHEMA}

КОЛОНКИ ИЗ EXCEL: {excel_columns}

ПОЛЯ БД ДЛЯ МАППИНГА: {db_fields}

ПОЛЬЗОВАТЕЛЬСКИЕ ПРАВИЛА МАППИНГА:
{self._format_user_mapping_rules(user_mapping_rules) if user_mapping_rules else "Не настроены"}

СПЕЦИАЛЬНЫЕ ПРАВИЛА ДЛЯ ОЧКОВ:
1. category и brand часто означают БРЕНД очков (Gucci, Ray-Ban, Prada, Versace и т.д.)
2. type - тип очков (солнцезащитные, оптические, для чтения, компьютерные и т.д.)
3. shape - форма оправы (круглые, квадратные, авиаторы, кошачий глаз и т.д.)
4. gender - пол (мужские, женские, унисекс)
5. size - размер очков или размер оправы
6. width/height - размеры оправы в миллиметрах
7. part_number - артикул модели очков
8. part_name - название модели очков

ОБЩИЕ ПРАВИЛА МАППИНГА:
1. В ПЕРВУЮ ОЧЕРЕДЬ используй пользовательские правила маппинга, если они заданы
2. Анализируй семантику названий колонок (не только точные совпадения)
3. Учитывай синонимы и вариации названий для очков
4. Игнорируй регистр и пробелы
5. Если сомневаешься в соответствии - лучше не маппить
6. Возвращай ТОЛЬКО валидный JSON без дополнительных комментариев
7. Если колонка не соответствует ни одному полю БД - не включай её в результат

ФОРМАТ ОТВЕТА:
{{"excel_column_name": "db_field_name", ...}}

Проанализируй каждую колонку Excel в контексте очков и сопоставь с наиболее подходящим полем БД.
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-5-mini",
                messages=[{"role": "user", "content": prompt}],
            )
            mapping_str = response.choices[0].message.content.strip()
            # Очистка от markdown
            if mapping_str.startswith("```json"):
                mapping_str = mapping_str[7:]
            if mapping_str.endswith("```"):
                mapping_str = mapping_str[:-3]
            mapping = json.loads(mapping_str)
            return mapping
        except Exception as e:
            print(f"Ошибка маппинга: {e}")
            return {}

    async def generate_sql(self, natural_query: str, history: List[str] = None) -> str:
        """Генерация SQL из естественного языка с учетом контекста"""
        if history is None:
            history = []
        
        # Берем только последние 3 сообщения для контекста
        recent_history = history[-3:] if len(history) > 3 else history
        
        # Формируем контекст из предыдущих сообщений
        context = ""
        if recent_history:
            context = "\nПРЕДЫДУЩИЕ СООБЩЕНИЯ ПОЛЬЗОВАТЕЛЯ (для понимания контекста):\n"
            for i, msg in enumerate(recent_history, 1):
                context += f"{i}. \"{msg}\"\n"
            context += "\nУЧИТЫВАЙ ЭТИ ПРЕДЫДУЩИЕ ЗАПРОСЫ ПРИ ГЕНЕРАЦИИ SQL - ЭТО ПОСЛЕДОВАТЕЛЬНЫЕ УТОЧНЕНИЯ ОДНОГО ЗАПРОСА.\n\n"
        prompt = f"""
Ты эксперт-аналитик SQL с глубоким пониманием русского языка и базы данных очков.

ВАЖНО: Это база данных ИСКЛЮЧИТЕЛЬНО для очков. Все запросы относятся к очкам (солнцезащитные, оптические, для чтения и т.д.).

СХЕМА БАЗЫ ДАННЫХ ОЧКОВ:
{DB_SCHEMA}

{context}

ТЕКУЩИЙ ЗАПРОС ПОЛЬЗОВАТЕЛЯ: "{natural_query}"

КРИТИЧЕСКИЕ ТРЕБОВАНИЯ:
1. Генерируй ТОЛЬКО исполняемый SQL без параметров-заполнителей
2. Используй прямые значения в запросах (НЕ %s, %1, $1)
3. Строковые значения заключай в одинарные кавычки
4. Числовые значения используй без кавычек
5. Для поиска используй LIKE с % для частичного совпадения
6. УЧИТЫВАЙ КОНТЕКСТ ПРЕДЫДУЩИХ СООБЩЕНИЙ - ЭТО ПОСЛЕДОВАТЕЛЬНЫЕ УТОЧНЕНИЯ
7. Возвращай ТОЛЬКО SQL запрос без комментариев и markdown

РАЗРЕШЕННЫЕ ОПЕРАЦИИ: SELECT, INSERT, UPDATE, DELETE
ЗАПРЕЩЕННЫЕ ОПЕРАЦИИ: DROP, TRUNCATE, ALTER, CREATE, GRANT, REVOKE

СПЕЦИАЛИЗИРОВАННЫЕ ШАБЛОНЫ ДЛЯ ОЧКОВ:

ПОИСК ОЧКОВ:
- "найди очки [бренда] X" → SELECT * FROM products WHERE category LIKE '%X%' OR brand LIKE '%X%'
- "покажи солнцезащитные очки" → SELECT * FROM products WHERE type LIKE '%солнцезащитные%'
- "очки для [пола]" → SELECT * FROM products WHERE gender LIKE '%[пол]%'
- "очки формы [форма]" → SELECT * FROM products WHERE shape LIKE '%[форма]%'
- "очки цвета [цвет]" → SELECT * FROM products WHERE color LIKE '%[цвет]%'
- "очки шириной больше X мм" → SELECT * FROM products WHERE width > X
- "покажи все очки" → SELECT * FROM products

БРЕНДЫ ОЧКОВ (примеры):
- Gucci, Ray-Ban, Prada, Versace, Dior, Chanel, Armani, Dolce & Gabbana, Tom Ford, Oakley

ТИПЫ ОЧКОВ:
- солнцезащитные, оптические, для чтения, компьютерные, антибликовые

ФОРМЫ ОПРАВЫ:
- круглые, квадратные, авиаторы, кошачий глаз, прямоугольные, овальные

ПРИМЕРЫ ПРАВИЛЬНЫХ ЗАПРОСОВ ДЛЯ ОЧКОВ:
- SELECT * FROM products WHERE category LIKE '%Gucci%'
- SELECT * FROM products WHERE type LIKE '%солнцезащитные%' AND gender = 'женские'
- SELECT * FROM products WHERE shape LIKE '%авиаторы%' AND color LIKE '%черный%'
- INSERT INTO products (part_name, category, type, gender) VALUES ('Модель XYZ', 'Ray-Ban', 'солнцезащитные', 'унисекс')
- UPDATE products SET color = 'золотой' WHERE category LIKE '%Gucci%' AND id = 1

ОБРАБОТКА НЕОДНОЗНАЧНОСТИ:
- "очки" подразумевает поиск в таблице products
- Для брендов ищи в category и brand одновременно
- При отсутствии ID для UPDATE/DELETE используй уникальные комбинации полей
- Если запрос неточен, выбирай наиболее вероятную интерпретацию для очков

Проанализируй запрос пользователя в контексте очков и сгенерируй соответствующий SQL:
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-5-mini",
                messages=[{"role": "user", "content": prompt}],
            )
            sql = response.choices[0].message.content.strip()
            # Удаление возможных markdown
            if sql.startswith("```sql"):
                sql = sql[6:]
            if sql.endswith("```"):
                sql = sql[:-3]
            return sql.strip()
        except Exception as e:
            print(f"Ошибка генерации SQL: {e}")
            return ""

    def _format_user_mapping_rules(self, user_mapping_rules: Dict[str, List[str]]) -> str:
        """Форматирует пользовательские правила маппинга для промпта"""
        if not user_mapping_rules:
            return "Не настроены"
        
        formatted_rules = []
        for db_column, patterns in user_mapping_rules.items():
            if patterns:  # Проверяем что есть паттерны
                patterns_str = ", ".join([f'"{pattern}"' for pattern in patterns])
                formatted_rules.append(f"- {patterns_str} → {db_column}")
        
        return "\n".join(formatted_rules) if formatted_rules else "Не настроены"

# Глобальный экземпляр
ai_service = AiService()
