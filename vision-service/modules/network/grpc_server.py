"""!
@file grpc_server.py
@brief Manages the gRPC server setup and lifecycle for the Vision Service.

This module defines the `GrpcServer` class, which is responsible for
configuring, creating, starting, and stopping the gRPC server that hosts
the Vision Service.
"""

import grpc
from concurrent import futures
import proto.vision_pb2_grpc as vision_pb2_grpc
from ..config.logger_config import setup_logger
from ..config.grpc_config import GrpcConfig
from ..core.vision_service import VisionServiceServicer

# Logger'ı yapılandır
logger = setup_logger()


class GrpcServer:
    """!
    @brief Class for managing the gRPC server.

    This class encapsulates the logic for the gRPC server lifecycle,
    including its creation, starting, stopping, and waiting for termination.
    It uses configurations defined in `GrpcConfig`.
    """
    
    def __init__(self):
        """!
        @brief Initializes the GrpcServer.

        Loads the gRPC configuration necessary for server setup.
        """
        self.config = GrpcConfig()
        self.server = None
        
    def create_server(self):
        """!
        @brief Creates the gRPC server instance.

        Initializes the `grpc.server` with a thread pool, adds the
        `VisionServiceServicer` to it, and binds the server to the
        configured address and port.
        @return True if server creation was successful, False otherwise.
        """
        try:
            # gRPC sunucusunu oluştur
            self.server = grpc.server(
                futures.ThreadPoolExecutor(max_workers=self.config.max_workers),
                options=self.config.grpc_options
            )
            
            # Vision service'i sunucuya ekle
            vision_pb2_grpc.add_VisionServiceServicer_to_server(
                VisionServiceServicer(), 
                self.server
            )
            
            # Port'u ekle
            self.server.add_insecure_port(self.config.address)
            
            logger.info(f"gRPC sunucu oluşturuldu: {self.config.address}")
            return True
            
        except Exception as e:
            logger.error(f"gRPC sunucu oluşturma hatası: {str(e)}")
            return False
    
    def start_server(self):
        """!
        @brief Starts the gRPC server.

        Creates the server if it hasn't been created yet, then starts it.
        @return True if server start was successful, False otherwise.
        """
        try:
            if not self.server:
                if not self.create_server():
                    return False
            
            self.server.start()
            logger.info(f"VisionService gRPC server is running on {self.config.address}...")
            return True
            
        except Exception as e:
            logger.error(f"gRPC sunucu başlatma hatası: {str(e)}")
            return False
    
    def stop_server(self, grace_period=5):
        """!
        @brief Stops the gRPC server.

        Allows ongoing RPCs to complete within the grace period before shutting down.
        @param grace_period The time in seconds to wait for pending RPCs to complete.
                            Defaults to 5 seconds.
        @return True if the server was stopped successfully or was not running, False on error.
        """
        try:
            if self.server:
                self.server.stop(grace_period)
                logger.info("gRPC sunucu durduruldu")
                return True
            return True # Considered success if server was not running
            
        except Exception as e:
            logger.error(f"gRPC sunucu durdurma hatası: {str(e)}")
            return False
    
    def wait_for_termination(self):
        """!
        @brief Waits until the server is terminated.

        Blocks execution until the server shuts down. Handles KeyboardInterrupt
        for graceful shutdown.
        """
        try:
            if self.server:
                self.server.wait_for_termination()
                
        except KeyboardInterrupt:
            logger.info("Klavye kesintisi algılandı, sunucu kapatılıyor...")
            self.stop_server()
        except Exception as e:
            logger.error(f"Sunucu bekleme hatası: {str(e)}")
    
    def serve(self):
        """!
        @brief Starts the server and waits for it to terminate.

        This is a convenience method that calls `start_server()` and then
        `wait_for_termination()`. It also ensures the server is stopped
        in a finally block.
        """
        if self.start_server():
            try:
                self.wait_for_termination()
            except Exception as e:
                logger.error(f"Sunucu servis hatası: {str(e)}")
            finally:
                self.stop_server()
