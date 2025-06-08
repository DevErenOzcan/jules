import os
import logging
import sys
import platform
from datetime import datetime
from typing import Dict, Any

"""!
@file utils.py
@brief Provides utility functions for the Emotion Service.

This module contains helper functions for logging configuration,
path management, server address retrieval, and system information gathering.
"""

def configure_logging(log_file: str = "emotion_service.log", level: int = logging.INFO):
    """!
    @brief Configures the logging system for the application.
    
    Sets up logging to both console (StreamHandler) and a timestamped file (FileHandler)
    within a 'logs' directory. It also sets higher logging levels for noisy libraries
    like deepface, matplotlib, and PIL to reduce log spam.

    @param log_file The base name for the log file. A timestamp will be prepended.
                    Defaults to "emotion_service.log".
    @param level The minimum logging level for the application's main logger
                 (e.g., logging.DEBUG, logging.INFO). Defaults to logging.INFO.
        
    @return logging.Logger: The configured root logger instance for "emotion-service".
    """
    # Log klasörü oluştur
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    # Logging yapılandırma - dosya adına tarih ekle
    timestamp = datetime.now().strftime("%Y%m%d")
    log_filename = os.path.join(log_dir, f"{timestamp}_{log_file}")
    
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_filename)
        ]
    )
    
    # Alt modüller için logger'ları yapılandır
    logger = logging.getLogger("emotion-service")
    logger.setLevel(logging.INFO)
    
    # Deepface ve OpenCV gibi kütüphanelerin gereksiz loglarını kapat
    logging.getLogger("deepface").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    
    return logger

def configure_paths():
    """!
    @brief Configures Python import paths for the project.

    Adds the 'proto' directory (located one level above the 'modules' directory)
    and the current 'modules' directory to `sys.path` if they are not already present.
    This ensures that protobuf-generated modules and other project modules can be imported.
    """
    # Dinamik proto klasörü ekle
    # Assuming this file is in 'modules', so os.path.dirname(__file__) is 'modules' path
    # Then os.path.dirname(os.path.dirname(__file__)) is the parent of 'modules'
    proto_dir_parent = os.path.dirname(os.path.dirname(__file__))
    proto_dir = os.path.join(proto_dir_parent, 'proto')
    if proto_dir not in sys.path:
        sys.path.append(proto_dir)
    
    # Projenin diğer modüllerini de ekle
    module_dir = os.path.dirname(__file__) # This is the 'modules' directory itself
    if module_dir not in sys.path:
        sys.path.append(module_dir)
        
def get_server_address() -> str:
    """!
    @brief Retrieves the server address from environment variables or defaults.
    
    Uses `HOST` and `PORT` environment variables.
    Defaults to '0.0.0.0:50052' if variables are not set.

    @return str: The server address in 'host:port' format.
    """
    port = os.getenv('PORT', '50052')
    host = os.getenv('HOST', '0.0.0.0')
    return f"{host}:{port}"
    
def get_system_info() -> Dict[str, Any]:
    """!
    @brief Collects various system information.
    
    @return Dict[str, Any]: A dictionary containing details such as OS, OS version,
                            Python version, processor, hostname, and current timestamp.
    """
    info = {
        'os': platform.system(),
        'os_version': platform.version(),
        'python_version': platform.python_version(),
        'processor': platform.processor(),
        'hostname': platform.node(),
        'timestamp': datetime.now().isoformat()
    }
    return info
