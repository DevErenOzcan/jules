"""!
@file vision_server.py
@brief Vision Service main launcher.

This script is responsible for initializing and starting the Vision Service.
It loads necessary configurations, sets up logging, and launches the gRPC server
to handle incoming requests for vision analysis.
"""

import sys
import os
import dotenv
from pathlib import Path

# .env dosyasını yükle
dotenv.load_dotenv(Path(__file__).parent / '.env')

# Dinamik proto klasörü ekle
sys.path.append(os.path.join(os.path.dirname(__file__), 'proto'))

# Özel modülleri içe aktar
from modules import setup_logger, GrpcServer

# Logger'ı yapılandır
logger = setup_logger()


def main():
    """!
    @brief Main entry point for the Vision Service.

    Initializes the logger and the gRPC server. It then starts the server
    and waits for termination signals (like KeyboardInterrupt) for a graceful shutdown.
    Any exceptions encountered during the startup or execution phase are logged.
    @exception Exception Logs and re-raises any exception that occurs, ensuring issues are recorded.
    """
    try:
        logger.info("Vision Service başlatılıyor...")
        server = GrpcServer()
        server.serve()
    except KeyboardInterrupt:
        logger.info("Vision Service kapatılıyor...")
    except Exception as e:
        logger.error(f"Vision Service başlatma hatası: {str(e)}")
        raise


if __name__ == "__main__":
    main()
