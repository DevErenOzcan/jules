"""!
@file emotion_server.py
@brief Main launcher for the Emotion Analysis gRPC Service.

This script initializes and starts the gRPC server for emotion analysis.
It handles command-line arguments for server configuration, sets up logging,
configures paths, and manages graceful shutdown via signal handling.
The server utilizes the EmotionServiceServicer for handling analysis requests.

Usage:
    python emotion_server.py [--host HOST] [--port PORT] [--workers WORKERS] [--confidence CONFIDENCE]

Example:
    python emotion_server.py --port 50052 --host 0.0.0.0 --workers 10 --confidence 0.35
"""
import grpc
from concurrent import futures
import os
import signal
import sys
import argparse
import time
import threading
from datetime import datetime

# Modüllerimizi import et
from modules.utils import configure_logging, configure_paths, get_server_address, get_system_info
from modules.service import EmotionServiceServicer
import proto.vision_pb2_grpc as vision_pb2_grpc

# Proje path'lerini yapılandır
configure_paths()

# Logger'ı yapılandır
logger = configure_logging()

# Sağlık monitörü için global değişkenler
server = None
start_time = None
request_counter = 0
request_counter_lock = threading.Lock()

def signal_handler(sig, frame):
    """!
    @brief Handles termination signals for graceful shutdown.
    @param sig The signal number.
    @param frame The current stack frame.
    """
    if server:
        logger.info("Sunucu kapatma sinyali alındı, servis sonlandırılıyor...")
        server.stop(5)  # 5 saniye içinde mevcut istekleri tamamla
        logger.info("Sunucu başarıyla durduruldu.")
    sys.exit(0)

def increment_request_counter():
    """!
    @brief Increments the global request counter safely.
    @return The new value of the request counter.
    """
    global request_counter
    with request_counter_lock:
        request_counter += 1
        return request_counter

def health_monitor(interval=60):
    """!
    @brief Periodically logs server health information.

    Logs uptime, total requests, and system information at specified intervals.
    @param interval The logging interval in seconds. Defaults to 60.
    """
    global start_time, request_counter
    
    while True:
        uptime = time.time() - start_time
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        with request_counter_lock:
            current_count = request_counter
            
        logger.info(f"Sağlık durumu: Çalışma süresi: {int(hours)}s {int(minutes)}d {int(seconds)}s, "
                   f"Toplam istek: {current_count}")
        
        # Sistem bilgilerini log
        system_info = get_system_info()
        logger.debug(f"Sistem bilgileri: {system_info}")
        
        time.sleep(interval)

def parse_arguments():
    """!
    @brief Parses command-line arguments for server configuration.
    @return An argparse.Namespace object containing the parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Duygu Analizi gRPC Servisi")
    parser.add_argument('--host', default='0.0.0.0', help='Sunucu host adresi')
    parser.add_argument('--port', type=int, default=50052, help='Sunucu port numarası')
    parser.add_argument('--workers', type=int, default=10, help='İş parçacığı sayısı')
    parser.add_argument('--confidence', type=float, default=0.35, help='Duygu tespiti güven eşiği (0.0-1.0)')
    return parser.parse_args()

def serve(args=None):
    """!
    @brief Initializes and starts the gRPC server for emotion analysis.

    This function sets up signal handlers, creates the gRPC server instance,
    adds the EmotionServiceServicer, starts the server, and then waits for
    termination signals. It also starts a background health monitoring thread.
    @param args Optional argparse.Namespace object. If None, arguments are parsed from command line.
    @exception Exception Logs and re-raises any exception during service startup or execution,
                       leading to server stop and system exit.
    """
    global server, start_time
    
    if args is None:
        args = parse_arguments()
    
    # Environment variables'dan veya argümanlardan adres bilgilerini al
    host = os.getenv('HOST', args.host)
    port = os.getenv('PORT', args.port)
    address = f"{host}:{port}"
    
    # Başlangıç zamanını kaydet
    start_time = time.time()
    
    # Sinyal yakalayıcıları tanımla
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Sunucuyu başlat
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=args.workers),
        interceptors=[]  # Burada gerekli interceptor'lar eklenebilir
    )
    
    # Servis nesnesi oluştur ve sunucuya ekle
    service = EmotionServiceServicer(confidence_threshold=args.confidence)
    vision_pb2_grpc.add_EmotionServiceServicer_to_server(service, server)
    
    # Sunucuyu belirtilen adreste başlat
    server.add_insecure_port(address)
    server.start()
    
    # Sistem bilgilerini log'la
    system_info = get_system_info()
    logger.info(f"Sistem bilgileri: {system_info}")
    
    # Sunucu başlangıç bilgilerini log'la
    logger.info(f"EmotionService gRPC servisi başlatıldı:")
    logger.info(f" - Adres: {address}")    
    logger.info(f" - İş parçacığı sayısı: {args.workers}")
    logger.info(f" - Güven eşiği: {args.confidence}")
    logger.info(f" - Başlangıç zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
      # Sağlık monitörünü ayrı bir thread'de başlat
    health_thread = threading.Thread(target=health_monitor, args=(300,), daemon=True)
    health_thread.start()
    
    # Sunucuyu çalışır durumda tut
    try:
        logger.info("Sunucu hazır, istekleri bekliyor...")
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Klavye kesintisi alındı, servis kapatılıyor...")
        server.stop(0) # Graceful stop with 0 wait time for keyboard interrupt
    except Exception as e:
        logger.error(f"Beklenmeyen bir hata oluştu: {str(e)}")
        if server:
            server.stop(0) # Ensure server is stopped
        sys.exit(1)

if __name__ == "__main__":
    # Note: The main execution block itself is not typically Doxygen documented
    # as it's an entry point. The 'serve()' function it calls is documented.
    serve()
