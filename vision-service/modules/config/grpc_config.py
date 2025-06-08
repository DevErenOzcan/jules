import os
import logging

logger = logging.getLogger("vision-service")

"""!
@file grpc_config.py
@brief Defines gRPC client/server configurations for the Vision Service.

This module contains the GrpcConfig class, which centralizes
gRPC related settings like server address, max workers, message size limits,
and addresses for other services.
"""

class GrpcConfig:
    """!
    @brief Holds gRPC configuration parameters.

    This class loads gRPC settings from environment variables or uses defaults.
    It provides these settings as attributes and properties for easy access
    by the gRPC server and client components.
    """
    
    def __init__(self):
        """!
        @brief Initializes the GrpcConfig with values from environment variables or defaults.

        Loads settings such as:
        - Server host and port
        - Maximum number of worker threads for the server
        - Maximum gRPC message size
        - Addresses for external services (Emotion, Speech)
        """
        self.host = os.getenv('HOST', '0.0.0.0')
        self.port = os.getenv('PORT', '50051')
        self.max_workers = int(os.getenv('MAX_WORKERS', '10'))
        
        # Mesaj boyut limitleri
        self.max_message_size = 50 * 1024 * 1024  # 50MB
        
        # Diğer servis adresleri
        self.emotion_service_address = os.getenv('EMOTION_SERVICE_ADDRESS', 'localhost:50052')
        self.speech_service_address = os.getenv('SPEECH_SERVICE_ADDRESS', 'localhost:50053')
        
        logger.info(f"gRPC yapılandırması yüklendi: {self.host}:{self.port}")
    
    @property
    def address(self):
        """!
        @brief Provides the full server address string.
        @return A string in the format 'host:port'.
        """
        return f"{self.host}:{self.port}"
    
    @property
    def grpc_options(self):
        """!
        @brief Provides gRPC server options.
        @return A list of tuples representing gRPC options, including max message sizes.
        """
        return [
            ('grpc.max_send_message_length', self.max_message_size),
            ('grpc.max_receive_message_length', self.max_message_size)
        ]
    
    @property
    def grpc_channel_options(self):
        """!
        @brief Provides gRPC channel options for clients.
        @return A list of tuples representing gRPC channel options, including max message sizes.
        """
        return [
            ('grpc.max_send_message_length', 10 * 1024 * 1024),  # 10MB
            ('grpc.max_receive_message_length', 10 * 1024 * 1024)  # 10MB
        ]
