# -*- coding: utf-8 -*-
"""!
@file speech_server.py
@brief Main launcher for the Speech Detection gRPC Service.

This script initializes and starts the gRPC server for speech detection.
It loads environment variables, sets up logging, configures paths for protobuf
modules, and manages the server lifecycle including graceful shutdown.
The server utilizes the SpeechDetectionServicer for handling analysis requests.

Usage:
    python speech_server.py
    (Configuration is primarily via environment variables: HOST, PORT, MAX_WORKERS, LOG_LEVEL, LOG_FILE)
"""
import os
import grpc
import sys
from concurrent import futures
from pathlib import Path

# .env dosyasını yükle (varsa)
dotenv_path = Path(__file__).parent / '.env'
if dotenv_path.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path)

# Modülleri import et
from modules.utils import setup_logging, add_proto_path
from modules.service import SpeechDetectionServicer

# Proto dosyaları dizinini ekle
add_proto_path()

# Proto dosyalarını import et
sys.path.append(os.path.join(os.path.dirname(__file__), 'proto'))
import proto.vision_pb2_grpc as vision_pb2_grpc

# Logger oluştur
logger = setup_logging(
    log_level=os.getenv('LOG_LEVEL', 'INFO'),
    log_to_file=True,
    log_file=os.getenv('LOG_FILE', 'speech_service.log')
)


def serve():
    """!
    @brief Initializes and starts the gRPC server for speech detection.

    This function retrieves server configuration from environment variables,
    creates the gRPC server instance with specified options, adds the
    SpeechDetectionServicer, starts the server, and then waits for
    termination signals (like KeyboardInterrupt) for a graceful shutdown.
    @exception Exception Logs any exception during server startup or execution
                       and attempts to stop the server.
    """
    # Sunucu parametrelerini environment variable'lardan al
    host = os.getenv('HOST', '0.0.0.0')
    port = os.getenv('PORT', '50053')
    address = f"{host}:{port}"
    max_workers = int(os.getenv('MAX_WORKERS', '10'))
    
    logger.info(f"Speech Detection Service başlatılıyor...")
    logger.info(f"Host: {host}, Port: {port}, Max Workers: {max_workers}")
    
    # gRPC sunucusu oluştur
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=max_workers),
        options=[
            ('grpc.max_send_message_length', 10 * 1024 * 1024),  # 10MB
            ('grpc.max_receive_message_length', 10 * 1024 * 1024)  # 10MB
        ]
    )
    
    # Speech Detection Service ekle
    speech_service = SpeechDetectionServicer()
    vision_pb2_grpc.add_SpeechDetectionServiceServicer_to_server(speech_service, server)
    
    # Portu bağla ve sunucuyu başlat
    server.add_insecure_port(address)
    server.start()
    
    logger.info(f"SpeechDetectionService gRPC sunucusu {address} adresinde çalışıyor...")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Sunucu kapatılıyor...")
        server.stop(0)
        logger.info("Sunucu kapatıldı.")


if __name__ == "__main__":
    serve()
