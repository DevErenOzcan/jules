"""!
@file utils.py
@brief Utility functions for the Speech Detection Service.

This module provides helper functions for setting up logging,
adding protobuf paths to sys.path, and checking for essential dependencies.
"""
import logging
import sys
import os
from datetime import datetime

def setup_logging(log_level='INFO', log_to_file=True, log_file='speech_service.log'):
    """!
    @brief Configures logging for the Speech Detection Service.

    Sets up logging to both console (StreamHandler) and file(s).
    If `log_to_file` is True, it logs to a daily timestamped file (e.g., YYYYMMDD_speech_service.log)
    in a 'logs' directory (relative to the service root) and also to a general log file
    (e.g., speech_service.log) in the service root directory.
    It also sets the logging level for the 'grpc' logger to WARNING to reduce noise.
    
    @param log_level (str): The desired logging level string (e.g., "DEBUG", "INFO").
                           Defaults to "INFO".
    @param log_to_file (bool): Whether to enable file logging. Defaults to True.
    @param log_file (str): The base name for the log files. Defaults to "speech_service.log".
    @return logging.Logger: The configured logger instance for "speech-service".
    """
    # Log seviyesini ayarla
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    
    # Handlers listesi oluştur
    handlers = [logging.StreamHandler()]
    
    # Dosyaya yazma aktifse handler ekle
    if log_to_file:
        date_str = datetime.now().strftime('%Y%m%d')
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        
        # Log dizini yoksa oluştur
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Günlük log dosyası
        log_file_path = os.path.join(log_dir, f"{date_str}_{log_file}")
        handlers.append(logging.FileHandler(log_file_path))
        
        # Genel log dosyası
        general_log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), log_file)
        handlers.append(logging.FileHandler(general_log_path))
    
    # Loglama yapılandırması
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    # Bazı ek loggerların seviyelerini ayarla
    logging.getLogger('grpc').setLevel(logging.WARNING)
    
    return logging.getLogger("speech-service")

def add_proto_path():
    """!
    @brief Adds the 'proto' directory to `sys.path` for protobuf module imports.

    The 'proto' directory is assumed to be located one level above the 'modules'
    directory (where this utils.py file is expected to be).
    """
    # Assuming this file is in 'modules', os.path.dirname(__file__) is 'modules' path
    # os.path.dirname(os.path.dirname(__file__)) is the parent of 'modules' (service root)
    service_root_dir = os.path.dirname(os.path.dirname(__file__))
    proto_dir = os.path.join(service_root_dir, 'proto')
    if proto_dir not in sys.path:
        sys.path.append(proto_dir)
        
def check_dependencies():
    """!
    @brief Checks for essential Python package dependencies.

    Currently checks for "numpy" and "grpc". If any are missing,
    it prints an error message to stdout listing the missing dependencies
    and a suggested pip install command.
    
    @return bool: True if all checked dependencies are found, False otherwise.
    """
    dependencies = ["numpy", "grpc"]
    missing = []
    
    for dep in dependencies:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)
    
    if missing:
        print(f"Eksik bağımlılıklar: {', '.join(missing)}")
        print("Lütfen şu komutu çalıştırın: pip install " + " ".join(missing))
        return False
        
    return True
