"""!
@file service_client.py
@brief Manages gRPC client connections to other microservices.

This module defines the ServiceClient class, which is responsible for
creating and managing gRPC stubs (clients) for communicating with
external services like EmotionService and SpeechDetectionService.
It supports sending requests both synchronously and asynchronously.
"""

import grpc
import threading
from ..config.logger_config import setup_logger
import proto.vision_pb2_grpc as vision_pb2_grpc

# Logger'ı yapılandır
logger = setup_logger()


class ServiceClient:
    """!
    @brief Manages gRPC client connections to other microservices.

    This class initializes and holds gRPC stubs for external services
    based on the provided GrpcConfig. It offers methods to send requests
    to these services, including an asynchronous option for processing
    detected faces.
    """
    
    def __init__(self, config):
        """!
        @brief Initializes the ServiceClient.
        
        @param config A GrpcConfig object containing the addresses and options
                      for external gRPC services.
        """
        self.config = config
        self.emotion_stub = None
        self.speech_stub = None
        
        # Servis bağlantılarını oluştur
        self._create_service_stubs()
    
    def _create_service_stubs(self):
        """!
        @brief Creates gRPC stubs for connecting to other services.
        @internal

        Initializes `emotion_stub` and `speech_stub` for communication
        with EmotionService and SpeechDetectionService respectively, using
        addresses and options from the GrpcConfig.
        """
        try:
            # Emotion Service'e bağlantı
            emotion_channel = grpc.insecure_channel(
                self.config.emotion_service_address,
                options=self.config.grpc_channel_options
            )
            self.emotion_stub = vision_pb2_grpc.EmotionServiceStub(emotion_channel)
            logger.info(f"Emotion Service'e bağlantı hazırlandı: {self.config.emotion_service_address}")
            
            # Speech Service'e bağlantı
            speech_channel = grpc.insecure_channel(
                self.config.speech_service_address,
                options=self.config.grpc_channel_options
            )
            self.speech_stub = vision_pb2_grpc.SpeechDetectionServiceStub(speech_channel)
            logger.info(f"Speech Detection Service'e bağlantı hazırlandı: {self.config.speech_service_address}")
            
        except Exception as e:
            logger.error(f"Servis bağlantıları oluşturulurken hata: {str(e)}")
            # Hata durumunda stub'ları None olarak ayarla
            self.emotion_stub = None
            self.speech_stub = None
    
    def send_to_emotion_service(self, face_request):
        """!
        @brief Sends a FaceRequest to the Emotion Service.

        @param face_request A vision_pb2.FaceRequest protobuf message.
        @return The response from EmotionService (vision_pb2.EmotionResponse) or None on failure.
        """
        try:
            if self.emotion_stub:
                logger.info(f"Emotion Service'e istek gönderiliyor (Yüz ID: {face_request.face_id})")
                response = self.emotion_stub.AnalyzeEmotion(face_request)
                logger.info(f"Emotion Service'den yanıt alındı: {response.emotion} ({response.confidence:.2f})")
                return response
        except Exception as e:
            logger.error(f"Emotion Service isteği başarısız: {str(e)}")
            return None
    
    def send_to_speech_service(self, face_request):
        """!
        @brief Sends a FaceRequest to the Speech Detection Service.

        @param face_request A vision_pb2.FaceRequest protobuf message.
        @return The response from SpeechDetectionService (vision_pb2.SpeechResponse) or None on failure.
        """
        try:
            if self.speech_stub:
                logger.info(f"Speech Detection Service'e istek gönderiliyor (Yüz ID: {face_request.face_id})")
                response = self.speech_stub.DetectSpeech(face_request)
                logger.info(f"Speech Service'den yanıt alındı: Konuşuyor: {response.is_speaking}, Süre: {response.speaking_time:.2f}s")
                return response
        except Exception as e:
            logger.error(f"Speech Service isteği başarısız: {str(e)}")
            return None
    
    def process_detected_face_async(self, face_request):
        """!
        @brief Asynchronously sends a FaceRequest to both Emotion and Speech services.

        This method spawns new threads to send requests to the EmotionService
        and SpeechDetectionService concurrently.

        @param face_request A vision_pb2.FaceRequest protobuf message containing
                            the face image, ID, and landmarks.
        """
        
        # Duygu analizi için isteği gönder
        try:
            if self.emotion_stub:
                threading.Thread(
                    target=self.send_to_emotion_service,
                    args=(face_request,)
                ).start()
        except Exception as e:
            logger.error(f"Emotion Service'e gönderme hatası: {str(e)}")
        
        # Konuşma tespiti için isteği gönder
        try:
            if self.speech_stub:
                threading.Thread(
                    target=self.send_to_speech_service,
                    args=(face_request,)
                ).start()
        except Exception as e:
            logger.error(f"Speech Service'e gönderme hatası: {str(e)}")
