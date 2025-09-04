import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from io import BytesIO
import re

class AdvancedExcelProcessor:
    def __init__(self):
        self.header_keywords = [
            'name', 'код', 'артикул', 'бренд', 'производитель', 'категория', 
            'цвет', 'размер', 'тип', 'материал', 'описание', 'цена',
            'upc', 'style', 'brand', 'color', 'size', 'material', 'description',
            'picture', 'image', 'фото', 'изображение', 'gender', 'пол'
        ]
    
    def detect_header_row(self, df: pd.DataFrame, max_rows_to_check: int = 10) -> int:
        """
        Определяет строку с заголовками колонок
        Возвращает индекс строки с заголовками
        """
        best_row = 0
        best_score = 0
        
        for row_idx in range(min(max_rows_to_check, len(df))):
            score = 0
            row_values = df.iloc[row_idx].astype(str).str.lower()
            
            # Подсчитываем количество ключевых слов в строке
            for value in row_values:
                if pd.notna(value) and value != 'nan':
                    for keyword in self.header_keywords:
                        if keyword in value:
                            score += 1
                            break
            
            # Дополнительные критерии:
            # - Количество непустых ячеек
            non_empty = row_values[row_values != 'nan'].count()
            score += non_empty * 0.1
            
            # - Уникальность значений (заголовки обычно уникальны)
            unique_ratio = len(row_values.unique()) / len(row_values)
            score += unique_ratio * 2
            
            if score > best_score:
                best_score = score
                best_row = row_idx
        
        return best_row
    


    def detect_data_structure(self, df: pd.DataFrame, header_row: int) -> Dict[str, Any]:
        """
        Анализирует структуру данных в Excel файле
        """
        structure_info = {
            'header_row': header_row,
            'data_start_row': header_row + 1,
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'merged_cells': [],
            'empty_rows': []
        }
        
        # Находим пустые строки
        for idx in range(header_row + 1, len(df)):
            row = df.iloc[idx]
            if row.isna().all() or (row.astype(str) == '').all():
                structure_info['empty_rows'].append(idx)
        
        return structure_info
    
    def clean_and_prepare_dataframe(self, df: pd.DataFrame, header_row: int) -> pd.DataFrame:
        """
        Очищает и подготавливает DataFrame для обработки
        """
        # Устанавливаем заголовки
        headers = df.iloc[header_row].astype(str)
        df.columns = headers
        
        # Удаляем строки до заголовков и саму строку заголовков
        df = df.iloc[header_row + 1:].reset_index(drop=True)
        
        # Удаляем полностью пустые строки
        df = df.dropna(how='all')
        
        # Удаляем полностью пустые колонки
        df = df.dropna(axis=1, how='all')
        
        # Очищаем названия колонок от лишних символов
        df.columns = [str(col).strip() if pd.notna(col) else f'Column_{i}' 
                     for i, col in enumerate(df.columns)]
        
        return df
    
    def process_excel_advanced(self, file_content: bytes, filename: str = None) -> Dict[str, Any]:
        """
        Расширенная обработка Excel файла с автоопределением структуры
        """
        try:
            # Читаем Excel с заголовками None для анализа структуры
            df = pd.read_excel(BytesIO(file_content), header=None)
            
            # Определяем строку с заголовками
            header_row = self.detect_header_row(df)
            
            # Анализируем структуру данных
            structure_info = self.detect_data_structure(df, header_row)
            
            # Очищаем и подготавливаем DataFrame
            cleaned_df = self.clean_and_prepare_dataframe(df, header_row)
            
            # Получаем колонки для маппинга
            available_columns = list(cleaned_df.columns)
            
            result = {
                'dataframe': cleaned_df,
                'structure_info': structure_info,
                'available_columns': available_columns,
                'sample_data': cleaned_df.head(3).to_dict('records') if not cleaned_df.empty else []
            }
            
            return result
            
        except Exception as e:
            raise ValueError(f"Ошибка обработки Excel файла: {e}")
    
    def suggest_column_mapping(self, available_columns: List[str]) -> Dict[str, str]:
        """
        Базовый маппинг колонок - возвращает пустой словарь
        Теперь мы полагаемся на ИИ и пользовательские правила
        """
        return {}

# Глобальный экземпляр
advanced_excel_processor = AdvancedExcelProcessor()
