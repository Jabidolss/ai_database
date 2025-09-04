import pandas as pd
from typing import List, Dict, Any
from io import BytesIO

class ExcelProcessor:
    def __init__(self):
        pass

    def process_excel(self, file_content: bytes, mapping: Dict[str, str]) -> List[Dict[str, Any]]:
        """Обработка Excel файла с маппингом колонок"""
        try:
            df = pd.read_excel(BytesIO(file_content))
        except Exception as e:
            raise ValueError(f"Ошибка чтения Excel: {e}")

        # Переименование колонок по маппингу
        df = df.rename(columns=mapping)

        # Оставить только маппинг колонки
        mapped_columns = list(mapping.values())
        existing_columns = [col for col in mapped_columns if col in df.columns]
        df = df[existing_columns]

        # Преобразование в list of dict, игнорируя NaN
        df = df.where(pd.notnull(df), None)
        records = df.to_dict('records')

        return records

    def validate_data(self, records: List[Dict[str, Any]]) -> List[str]:
        """Валидация данных перед вставкой"""
        errors = []
        for i, record in enumerate(records):
            row_num = i + 2  # +2 потому что заголовок + индекс

            # Проверка width
            if 'width' in record and record['width'] is not None:
                try:
                    float(record['width'])
                except (ValueError, TypeError):
                    errors.append(f"Строка {row_num}: width должен быть числом")

            # Проверка height
            if 'height' in record and record['height'] is not None:
                try:
                    float(record['height'])
                except (ValueError, TypeError):
                    errors.append(f"Строка {row_num}: height должен быть числом")

            # Проверка year
            if 'year' in record and record['year'] is not None:
                try:
                    int(record['year'])
                except (ValueError, TypeError):
                    errors.append(f"Строка {row_num}: year должен быть целым числом")

            # Проверка размеров строк
            for field in ['manufacturer_name', 'part_number', 'part_name', 'category', 'type', 'size', 'color', 'brand', 'producer', 'gender', 'age', 'shape']:
                if field in record and record[field] is not None:
                    if len(str(record[field])) > 255:
                        errors.append(f"Строка {row_num}: {field} слишком длинный (макс 255 символов)")

        return errors

# Глобальный экземпляр
excel_processor = ExcelProcessor()
