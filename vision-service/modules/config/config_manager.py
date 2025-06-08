"""!
@file config_manager.py
@brief Manages application configuration values for the Vision Service.

This module defines the ConfigManager class, which is responsible for
loading and providing access to various configuration settings from
environment variables or default values. These settings include paths for
models, thresholds for face detection, logging configurations, and debug flags.
"""

import os
from .logger_config import setup_logger

# Logger'ı yapılandır
logger = setup_logger()


class ConfigManager:
    """!
    @brief Manages application configuration values.

    This class loads configuration settings from environment variables
    upon initialization and provides them as attributes. It also offers
    properties to get specific configuration dictionaries for different
    components like FaceDetector and FaceTracker, and a summary method.
    """
    
    def __init__(self):
        """!
        @brief Initializes the ConfigManager and loads all configuration values.

        Calls the internal _load_configuration method to populate instance
        attributes with values derived from environment variables or defaults.
        """
        self._load_configuration()
        logger.info("Yapılandırma değerleri yüklendi")
    
    def _load_configuration(self):
        """!
        @brief Loads configuration values from environment variables.
        @internal

        This method reads various settings like face detection thresholds,
        model paths, logging level, and debug flags from environment
        variables. If an environment variable is not set, it uses a
        predefined default value.
        """
        
        # Yüz tespit yapılandırmaları
        self.face_match_threshold = float(os.getenv('FACE_MATCH_THRESHOLD', '0.4'))
        self.face_cleanup_timeout = float(os.getenv('FACE_CLEANUP_TIMEOUT', '5.0'))
        
        # Model dosya yolları
        self.cascade_path = os.getenv('CASCADE_PATH', 'haarcascade_frontalface_default.xml')
        self.model_path = os.getenv('MODEL_PATH', 'shape_predictor_68_face_landmarks.dat')
        
        # Logging yapılandırması
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.log_file = os.getenv('LOG_FILE', 'logs/vision_service.log')
        
        # Debug modları
        self.debug_mode = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
        self.save_debug_images = os.getenv('SAVE_DEBUG_IMAGES', 'False').lower() == 'true'
        
        logger.info(f"Yüz eşleştirme eşiği: {self.face_match_threshold}")
        logger.info(f"Yüz temizleme zaman aşımı: {self.face_cleanup_timeout}s")
        logger.info(f"Debug modu: {self.debug_mode}")
    
    @property
    def face_detector_config(self):
        """!
        @brief Provides configuration specific to the FaceDetector.
        @return A dictionary containing 'cascade_path' and 'model_path'.
        """
        return {
            'cascade_path': self.cascade_path,
            'model_path': self.model_path
        }
    
    @property
    def face_tracker_config(self):
        """!
        @brief Provides configuration specific to the FaceTracker.
        @return A dictionary containing 'similarity_threshold' and 'cleanup_timeout'.
        """
        return {
            'similarity_threshold': self.face_match_threshold,
            'cleanup_timeout': self.face_cleanup_timeout
        }
    
    def get_config_summary(self):
        """!
        @brief Returns a summary of the current configuration.
        @return A dictionary containing key configuration values.
        """
        return {
            'face_match_threshold': self.face_match_threshold,
            'face_cleanup_timeout': self.face_cleanup_timeout,
            'cascade_path': self.cascade_path,
            'model_path': self.model_path,
            'debug_mode': self.debug_mode,
            'log_level': self.log_level
        }
