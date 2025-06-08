"""!
@file config.py
@brief Configuration management for the Speech Detection Service.

This module defines the Config class, which handles loading configuration
settings from default values, a configuration file (JSON or YAML), and
environment variables. Environment variables take precedence.
"""
import os
import logging
from pathlib import Path
import json
try:
    import yaml
except ImportError:
    yaml = None
    logging.getLogger("speech-service").warning("yaml modülü bulunamadı, YAML konfigürasyon dosyaları kullanılamayacak.")

logger = logging.getLogger("speech-service")

class Config:
    """!
    @brief Manages configuration settings for the Speech Detection Service.

    This class loads settings in a hierarchical order:
    1. Default values.
    2. Values from a specified configuration file (JSON or YAML).
    3. Values from environment variables (which override file and defaults).
    """
    
    def __init__(self, config_path=None):
        """!
        @brief Initializes the Config object.
        
        Loads default configurations, then overrides them with values from
        a configuration file (if provided), and finally overrides with values
        from environment variables.

        @param config_path (str, optional): Path to the configuration file (JSON or YAML).
                                           Defaults to None, meaning no file is loaded.
        """
        self._config = self._load_default_config()
        self._load_from_file(config_path)
        self._load_from_env()
        
        logger.info("Konfigürasyon yüklendi")
        
    def _load_default_config(self) -> dict:
        """!
        @brief Loads the default configuration values.
        @internal
        @return A dictionary containing the default configuration settings.
        """
        return {
            # Servis ayarları
            'host': '0.0.0.0',
            'port': 50053,
            'max_workers': 10,
            
            # Konuşma tespiti parametreleri
            'variation_threshold': 0.03,       # Yüz landmarkları hareketi eşiği
            'confidence_threshold': 0.35,      # Konuşma tespit güven eşiği
            'cooldown_frames': 3,              # Konuşma sonrası bekleme karesi
            'history_length': 20,              # Tarihçe uzunluğu
            'adaptation_rate': 0.08,           # Adaptasyon hızı
            'mouth_area_weight': 0.7,          # Ağız alanı ağırlığı
            'mouth_aspect_ratio_weight': 0.3,  # Ağız en-boy oranı ağırlığı
            
            # Loglama ayarları
            'log_level': 'INFO',
            'log_to_file': True,
            'log_file': 'speech_service.log',
            'log_max_bytes': 10485760,         # 10MB
            'log_backup_count': 5
        }
    
    def _load_from_file(self, config_path: str = None):
        """!
        @brief Loads configuration from a JSON or YAML file.
        @internal
        Overrides default values with those found in the file.
        @param config_path Path to the configuration file. If None or invalid,
                           no file is loaded.
        """
        if not config_path:
            return
            
        config_file = Path(config_path)
        if not config_file.exists():
            logger.warning(f"Konfigürasyon dosyası bulunamadı: {config_path}")
            return
            
        try:
            ext = config_file.suffix.lower()
            if ext == '.json':
                with open(config_file, 'r', encoding='utf-8') as f:
                    custom_config = json.load(f)
            elif ext in ['.yml', '.yaml']:
                with open(config_file, 'r', encoding='utf-8') as f:
                    custom_config = yaml.safe_load(f)
            else:
                logger.warning(f"Desteklenmeyen konfigürasyon dosyası formatı: {ext}")
                return
                
            self._config.update(custom_config)
            logger.info(f"Konfigürasyon dosyası yüklendi: {config_path}")
        except Exception as e:
            logger.error(f"Konfigürasyon dosyası yüklenirken hata: {str(e)}", exc_info=True)
    
    def _load_from_env(self):
        """!
        @brief Loads configuration from environment variables.
        @internal
        Overrides existing configuration values (from defaults or file)
        with values from corresponding environment variables. Environment
        variable names are expected to be uppercase versions of the config keys.
        Type conversion is attempted for boolean, integer, and float values.
        """
        for key in self._config:
            env_key = key.upper()
            env_value = os.getenv(env_key)
            
            if not env_value:
                continue
                
            # Değer tipi dönüşümü
            if isinstance(self._config[key], bool):
                self._config[key] = env_value.lower() in ('true', '1', 't', 'y', 'yes')
            elif isinstance(self._config[key], int):
                try:
                    self._config[key] = int(env_value)
                except ValueError:
                    logger.warning(f"Çevre değişkeni {env_key} bir tamsayıya dönüştürülemedi.")
            elif isinstance(self._config[key], float):
                try:
                    self._config[key] = float(env_value)
                except ValueError:
                    logger.warning(f"Çevre değişkeni {env_key} bir ondalık sayıya dönüştürülemedi.")
            else:
                self._config[key] = env_value
    
    def get(self, key: str, default=None):
        """!
        @brief Retrieves a configuration value.
        
        @param key The key of the configuration value to retrieve.
        @param default The value to return if the key is not found. Defaults to None.
            
        @return The configuration value associated with the key, or the default value.
        """
        return self._config.get(key, default)
    
    def get_all(self) -> dict:
        """!
        @brief Retrieves all configuration values.
        
        @return A copy of the internal configuration dictionary.
        """
        return self._config.copy()
        
    def __getitem__(self, key: str):
        """!
        @brief Enables dictionary-like access to configuration values (e.g., `config['key']`).
        @param key The configuration key.
        @return The configuration value.
        @exception KeyError if the key is not found.
        """
        if key not in self._config:
            raise KeyError(f"Konfigürasyon anahtarı bulunamadı: {key}")
        return self._config[key]
        
    def __contains__(self, key: str) -> bool:
        """!
        @brief Enables the `in` operator for checking key existence (e.g., `'key' in config`).
        @param key The configuration key to check.
        @return True if the key exists, False otherwise.
        """
        return key in self._config
    
    # This logger.info call seems misplaced within the class definition,
    # it should ideally be called after an instance is created and configured.
    # However, I will keep it as is to match the original code structure,
    # but note it for potential refactoring.
    # logger.info("Konfigürasyon ayarları yüklendi")
    
