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
        self._health_check_interval = 30  # seconds
    
    @classmethod
    def get_instance(cls, name: str = "telegram_music_downloader"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(name)
        return cls._instance
    
    def setup(self, level: str = "INFO", log_file: Optional[str] = None, 
              console: bool = True, max_file_size: int = 10) -> logging.Logger:
        """Configure logging with fallback mechanisms and specific setup for 'downloader' logger."""
        log_level = getattr(logging, level.upper(), logging.INFO)
        
        with self._lock:
            # Clear existing handlers for this logger instance
            self._clear_handlers()
            
            # Configure root logger minimally to avoid interference
            root_logger = logging.getLogger()
            
            # Clear any existing handlers from the root logger to prevent duplication
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            
            # IMPORTANT: Set root logger level higher (e.g., WARNING) to prevent it
            # from processing and duplicating logs from more specific, lower-level loggers.
            root_logger.setLevel(logging.WARNING) # Prevents root from handling INFO/DEBUG from our loggers
            
            formatter = logging.Formatter(
                fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # Set level for the specific logger (e.g., 'telegram_music_downloader')
            self.logger.setLevel(log_level)
            
            # Important: disable log propagation from this specific logger to the root logger
            # to avoid duplicate messages if root also has handlers.
            self.logger.propagate = False
            
            # Configure a separate logger specifically for the 'downloader' module
            downloader_logger = logging.getLogger('downloader')
            downloader_logger.setLevel(log_level)
            downloader_logger.propagate = False  # Important! Prevent double logging by root
            
            # Console handler setup for both loggers
            if console:
                self._setup_console_handler(log_level, formatter) # Adds to self.logger
                
                # Add a similar console handler to the 'downloader' logger
                # to ensure it also outputs to console if self.logger does.
                console_handler_for_downloader = logging.StreamHandler(sys.stdout)
                console_handler_for_downloader.setLevel(log_level)
                console_handler_for_downloader.setFormatter(formatter)
                downloader_logger.addHandler(console_handler_for_downloader)
            
            # File handler with rotation for both loggers
            if log_file:
                self._setup_file_handler(log_file, log_level, formatter, max_file_size) # Adds to self.logger
                
                # Add a similar file handler to the 'downloader' logger
                log_path_for_downloader = Path(log_file) # Ensure path is prepared
                log_path_for_downloader.parent.mkdir(parents=True, exist_ok=True)
                
                max_bytes = max_file_size * 1024 * 1024  # MB to bytes
                file_handler_for_downloader = RotatingFileHandler(
                    log_file, 
                    maxBytes=max_bytes,
                    backupCount=5,
                    encoding='utf-8'
                )
                
                file_handler_for_downloader.setLevel(log_level)
                file_handler_for_downloader.setFormatter(formatter)
                downloader_logger.addHandler(file_handler_for_downloader)
            
            self._test_logging()
            
            return self.logger
    
    def _clear_handlers(self):
        """Safely clear existing handlers from this logger instance."""
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
        """Setup console handler for this logger instance."""
        try:
            self._console_handler = logging.StreamHandler(sys.stdout)
            self._console_handler.setLevel(log_level)
            self._console_handler.setFormatter(formatter)
            self.logger.addHandler(self._console_handler)
        except Exception as e:
            print(f"Warning: Failed to setup console logging: {e}", file=sys.stderr)
    
    def _setup_file_handler(self, log_file: str, log_level, formatter, max_file_size: int):
        """Setup file handler with rotation for this logger instance."""
        try:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # RotatingFileHandler for automatic rotation
            max_bytes = max_file_size * 1024 * 1024  # MB to bytes
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
        """Test logging functionality after setup."""
        try:
            self.logger.info("Logger initialized successfully")
            self._force_flush()
        except Exception as e:
            self._log_to_console(f"Warning: Logger test failed: {e}")
    
    def _force_flush(self):
        """Force flush all handler buffers for this logger instance."""
        for handler in self.logger.handlers:
            try:
                handler.flush()
            except Exception:
                pass # Ignore errors on flush
    
    def _log_to_console(self, message: str):
        """Emergency logging to console if regular logging fails."""
        try:
            print(f"[LOGGER] {message}", file=sys.stderr)
        except Exception:
            pass # Utmost effort, but if this fails, nothing more can be done
    
    def health_check(self):
        """Periodically check the health of the logging system, especially the file handler."""
        current_time = time.time()
        
        if current_time - self._last_health_check < self._health_check_interval:
            return True # Skip check if done recently
        
        try:
            # Primarily check the file handler as it's most prone to external issues
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
            # Attempt to rebuild the file handler
            self._rebuild_file_handler()
            return False
    
    def _rebuild_file_handler(self):
        """Attempt to rebuild the file handler if it failed."""
        if not self._file_handler:
            return
        
        try:
            # Save parameters
            log_file = self._file_handler.baseFilename
            log_level = self._file_handler.level
            formatter = self._file_handler.formatter
            
            # Remove old handler
            self.logger.removeHandler(self._file_handler)
            self._file_handler.close()
            
            # Create new
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
        """Get the logger instance with health check."""
        self.health_check()
        return self.logger


def setup_logging(config_loader) -> logging.Logger:
    """Setup and return a configured RobustLogger instance based on ConfigLoader settings."""
    logger_instance = RobustLogger.get_instance()
    
    log_level = config_loader.get_log_level()
    log_file = config_loader.get_log_file()
    console_enabled = config_loader.is_console_logging_enabled()
    
    # Main logger setup
    logger = logger_instance.setup(
        level=log_level,
        log_file=log_file,
        console=console_enabled,
        max_file_size=10  # 10 MB before rotation
    )
    
    # Add separate setup for media_filter
    media_filter_logger = logging.getLogger('media_filter')
    media_filter_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    media_filter_logger.propagate = False  # Prevent duplication
    
    # Add console handler
    if console_enabled:
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        console_handler.setFormatter(formatter)
        media_filter_logger.addHandler(console_handler)
    
    # Add file handler
    if log_file:
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        max_bytes = 10 * 1024 * 1024  # 10 MB before rotation
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=max_bytes,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        file_handler.setFormatter(formatter)
        media_filter_logger.addHandler(file_handler)
    
    logger.info(f"Robust logger initialized - Level: {log_level}, File: {log_file}, Console: {console_enabled}")
    return logger