import logging
import sys
import threading
import time
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


class RobustLogger:
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self, name: str = "telegram_music_downloader"):
        self.name = name
        self.logger = logging.getLogger(name)
        self._file_handler = None
        self._console_handler = None
        self._last_health_check = 0
        self._health_check_interval = 30  # секунды
    
    @classmethod
    def get_instance(cls, name: str = "telegram_music_downloader"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(name)
        return cls._instance
    
    def setup(self, level: str = "INFO", log_file: Optional[str] = None, 
              console: bool = True, max_file_size: int = 10) -> logging.Logger:
        """Настройка логирования с защитой от сбоев"""
        log_level = getattr(logging, level.upper(), logging.INFO)
        
        with self._lock:
            # Очистка существующих handlers
            self._clear_handlers()
            
            # Настройка корневого логгера для влияния на все модули
            root_logger = logging.getLogger()
            
            # Очистка существующих обработчиков в корневом логгере
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            
            # ВАЖНОЕ ИЗМЕНЕНИЕ: Устанавливаем уровень корневого логгера чуть выше,
            # чтобы он не дублировал сообщения из явно настроенных логгеров
            root_logger.setLevel(logging.WARNING)
            
            # Форматтер
            formatter = logging.Formatter(
                fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # Установка уровня для конкретного логгера
            self.logger.setLevel(log_level)
            
            # Важно: отключаем распространение логов от конкретного логгера к родителям
            self.logger.propagate = False
            
            # Настраиваем логгер для модуля downloader
            downloader_logger = logging.getLogger('downloader')
            downloader_logger.setLevel(log_level)
            downloader_logger.propagate = False  # Важно!
            
            # Консольный handler для конкретных логгеров
            if console:
                self._setup_console_handler(log_level, formatter)
                
                # Добавляем такой же обработчик к логгеру downloader
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setLevel(log_level)
                console_handler.setFormatter(formatter)
                downloader_logger.addHandler(console_handler)
            
            # Файловый handler с ротацией
            if log_file:
                self._setup_file_handler(log_file, log_level, formatter, max_file_size)
                
                # Добавляем такой же файловый обработчик к логгеру downloader
                log_path = Path(log_file)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                
                # RotatingFileHandler для автоматической ротации
                max_bytes = max_file_size * 1024 * 1024  # MB в байты
                file_handler = RotatingFileHandler(
                    log_file, 
                    maxBytes=max_bytes,
                    backupCount=5,
                    encoding='utf-8'
                )
                
                file_handler.setLevel(log_level)
                file_handler.setFormatter(formatter)
                downloader_logger.addHandler(file_handler)
            
            # Тест записи
            self._test_logging()
            
            return self.logger
    
    def _clear_handlers(self):
        """Безопасная очистка handlers"""
        for handler in self.logger.handlers[:]:
            try:
                handler.flush()
                handler.close()
                self.logger.removeHandler(handler)
            except Exception:
                pass
        
        self._file_handler = None
        self._console_handler = None
    
    def _setup_console_handler(self, log_level, formatter):
        """Настройка консольного handler"""
        try:
            self._console_handler = logging.StreamHandler(sys.stdout)
            self._console_handler.setLevel(log_level)
            self._console_handler.setFormatter(formatter)
            self.logger.addHandler(self._console_handler)
        except Exception as e:
            print(f"Warning: Failed to setup console logging: {e}", file=sys.stderr)
    
    def _setup_file_handler(self, log_file: str, log_level, formatter, max_file_size: int):
        """Настройка файлового handler с ротацией"""
        try:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # RotatingFileHandler для автоматической ротации
            max_bytes = max_file_size * 1024 * 1024  # MB в байты
            self._file_handler = RotatingFileHandler(
                log_file, 
                maxBytes=max_bytes,
                backupCount=5,
                encoding='utf-8'
            )
            
            self._file_handler.setLevel(log_level)
            self._file_handler.setFormatter(formatter)
            self.logger.addHandler(self._file_handler)
            
        except Exception as e:
            self._log_to_console(f"Warning: Failed to setup file logging: {e}")
    
    def _test_logging(self):
        """Тест работоспособности логирования"""
        try:
            self.logger.info("Logger initialized successfully")
            self._force_flush()
        except Exception as e:
            self._log_to_console(f"Warning: Logger test failed: {e}")
    
    def _force_flush(self):
        """Принудительная очистка буферов"""
        for handler in self.logger.handlers:
            try:
                handler.flush()
            except Exception:
                pass
    
    def _log_to_console(self, message: str):
        """Аварийное логирование в консоль"""
        try:
            print(f"[LOGGER] {message}", file=sys.stderr)
        except Exception:
            pass
    
    def health_check(self):
        """Проверка здоровья системы логирования"""
        current_time = time.time()
        
        if current_time - self._last_health_check < self._health_check_interval:
            return True
        
        try:
            # Проверка файлового handler
            if self._file_handler:
                test_record = logging.LogRecord(
                    name=self.logger.name,
                    level=logging.DEBUG,
                    pathname="",
                    lineno=0,
                    msg="Health check",
                    args=(),
                    exc_info=None
                )
                
                self._file_handler.handle(test_record)
                self._file_handler.flush()
            
            self._last_health_check = current_time
            return True
            
        except Exception as e:
            self._log_to_console(f"Logger health check failed: {e}")
            # Попытка пересоздать файловый handler
            self._rebuild_file_handler()
            return False
    
    def _rebuild_file_handler(self):
        """Пересоздание файлового handler при сбоях"""
        if not self._file_handler:
            return
        
        try:
            # Сохранить параметры
            log_file = self._file_handler.baseFilename
            log_level = self._file_handler.level
            formatter = self._file_handler.formatter
            
            # Удалить старый handler
            self.logger.removeHandler(self._file_handler)
            self._file_handler.close()
            
            # Создать новый
            self._file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,
                backupCount=5,
                encoding='utf-8'
            )
            
            self._file_handler.setLevel(log_level)
            self._file_handler.setFormatter(formatter)
            self.logger.addHandler(self._file_handler)
            
            self._log_to_console("File handler rebuilt successfully")
            
        except Exception as e:
            self._log_to_console(f"Failed to rebuild file handler: {e}")
            self._file_handler = None
    
    def get_logger(self) -> logging.Logger:
        """Получение логгера с проверкой здоровья"""
        self.health_check()
        return self.logger


def setup_logging(config_loader) -> logging.Logger:
    """Настройка логирования из конфига с улучшенной обработкой ошибок"""
    logger_instance = RobustLogger.get_instance()
    
    log_level = config_loader.get_log_level()
    log_file = config_loader.get_log_file()
    console_enabled = config_loader.is_console_logging_enabled()
    
    logger = logger_instance.setup(
        level=log_level,
        log_file=log_file,
        console=console_enabled,
        max_file_size=10  # 10 MB перед ротацией
    )
    
    logger.info(f"Robust logger initialized - Level: {log_level}, File: {log_file}, Console: {console_enabled}")
    return logger