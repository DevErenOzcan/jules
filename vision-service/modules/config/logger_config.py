"""!
@file logger_config.py
@brief Configures logging for the Vision Service.

This module provides functions to set up and retrieve a logger instance
with a specified format, level, and output handlers (console and file).
It ensures that log messages are consistently formatted and stored.
"""
import logging
import os
from pathlib import Path


def setup_logger(name="vision-service", log_file="vision_service.log", level=logging.INFO):
    """!
    @brief Configures and returns a logger.
    
    Sets up a logger with both console (StreamHandler) and file (FileHandler)
    outputs. The log file is created in a 'logs' directory relative to the
    module's parent directory.
    
    @param name The name for the logger. Defaults to "vision-service".
    @param log_file The name of the log file. Defaults to "vision_service.log".
    @param level The logging level (e.g., logging.INFO, logging.DEBUG). Defaults to logging.INFO.

    @return logging.Logger: The configured logger instance.
    """
    # logs klasörünün tam yolunu oluştur
    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)  # logs klasörünü oluştur (yoksa)
    
    # Log dosyasının tam yolunu oluştur
    log_path = logs_dir / log_file
    
    # Logging yapılandırması
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_path)
        ]
    )
    
    return logging.getLogger(name)


def get_logger(name="vision-service"):
    """!
    @brief Retrieves an existing logger instance.

    This function is a simple wrapper around `logging.getLogger(name)`.
    
    @param name The name of the logger to retrieve. Defaults to "vision-service".
    
    @return logging.Logger: The logger instance.
    """
    return logging.getLogger(name)
