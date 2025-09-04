import os
import subprocess
import asyncio
from datetime import datetime
from pathlib import Path

class BackupService:
    def __init__(self):
        self.backup_dir = Path(__file__).parent.parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        self.backup_file = self.backup_dir / "latest_backup.sql"

        # Параметры подключения к БД
        database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/ai_database")
        
        print(f"DATABASE_URL: {database_url}")
        
        # Парсим URL для получения параметров
        from urllib.parse import urlparse
        parsed = urlparse(database_url)
        
        self.db_host = parsed.hostname or "localhost"
        self.db_port = str(parsed.port) if parsed.port else "5432"
        self.db_name = parsed.path.lstrip('/') if parsed.path else "ai_database"
        self.db_user = parsed.username or "postgres"
        self.db_password = parsed.password or "password"

        print(f"Параметры БД: host={self.db_host}, port={self.db_port}, db={self.db_name}, user={self.db_user}")

    async def create_backup(self):
        """Создание бэкапа базы данных"""
        try:
            # Используем pg_dump для создания SQL дампа
            env = os.environ.copy()
            env["PGPASSWORD"] = self.db_password

            command = [
                "pg_dump",
                "-h", self.db_host,
                "-p", self.db_port,
                "-U", self.db_user,
                "-d", self.db_name,
                "-f", str(self.backup_file),
                "--no-password",
                "--format=plain",  # Изменено на plain для совместимости
                "--clean",  # Добавляем --clean для очистки перед восстановлением
                "--if-exists"
            ]

            print(f"Создание бэкапа: {' '.join(command)}")
            print(f"Файл бэкапа: {self.backup_file}")

            # Запуск в отдельном потоке, так как subprocess.run не асинхронный
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._run_command, command, env)

            print(f"Бэкап создан: {self.backup_file}")
            return True

        except Exception as e:
            print(f"Ошибка создания бэкапа: {e}")
            return False

    async def restore_backup(self):
        """Восстановление базы данных из бэкапа"""
        try:
            if not self.backup_file.exists():
                raise FileNotFoundError(f"Файл бэкапа не найден: {self.backup_file}")

            # Проверяем размер файла
            file_size = self.backup_file.stat().st_size
            print(f"Размер файла бэкапа: {file_size} байт")

            if file_size == 0:
                raise ValueError("Файл бэкапа пустой")

            print(f"Восстановление из бэкапа: {self.backup_file}")

            # Сначала очищаем базу данных
            await self._clear_database()

            # Восстанавливаем из бэкапа с помощью psql (для plain формата)
            env = os.environ.copy()
            env["PGPASSWORD"] = self.db_password

            command = [
                "psql",
                "-h", self.db_host,
                "-p", self.db_port,
                "-U", self.db_user,
                "-d", self.db_name,
                "-f", str(self.backup_file)
            ]

            print(f"Команда восстановления: {' '.join(command)}")

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._run_command, command, env)

            print("База данных восстановлена из бэкапа")
            return True

        except Exception as e:
            print(f"Ошибка восстановления: {e}")
            return False

    async def _clear_database(self):
        """Очистка базы данных перед восстановлением"""
        try:
            env = os.environ.copy()
            env["PGPASSWORD"] = self.db_password

            # Удаляем все таблицы и пересоздаем схему
            commands = [
                "DROP SCHEMA public CASCADE;",
                "CREATE SCHEMA public;",
                "GRANT ALL ON SCHEMA public TO postgres;",
                "GRANT ALL ON SCHEMA public TO public;"
            ]

            for sql_cmd in commands:
                command = [
                    "psql",
                    "-h", self.db_host,
                    "-p", self.db_port,
                    "-U", self.db_user,
                    "-d", self.db_name,
                    "-c", sql_cmd
                ]

                print(f"Выполнение: {sql_cmd}")
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._run_command, command, env)

        except Exception as e:
            print(f"Ошибка очистки БД: {e}")
            raise

    def _run_command(self, command, env):
        """Запуск команды в subprocess"""
        try:
            result = subprocess.run(
                command,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            print(f"Команда выполнена успешно: {' '.join(command)}")
            return result
        except subprocess.CalledProcessError as e:
            print(f"Ошибка выполнения команды: {' '.join(command)}")
            print(f"Код выхода: {e.returncode}")
            print(f"Stdout: {e.stdout}")
            print(f"Stderr: {e.stderr}")
            raise

# Глобальный экземпляр сервиса
backup_service = BackupService()
