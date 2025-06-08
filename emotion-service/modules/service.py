"""
"""!
@file service.py
@brief Implements the gRPC servicer for the Emotion Analysis Service.

This module defines the `EmotionServiceServicer` class, which handles
incoming gRPC requests for emotion analysis. It utilizes the `EmotionAnalyzer`
class to process facial images and determine emotions.
"""
import cv2
import numpy as np
import logging
import time
import grpc
import traceback
from typing import Dict, Any, Optional

from .emotion_analyzer import EmotionAnalyzer

# Proto içe aktarma
import proto.vision_pb2 as vision_pb2
import proto.vision_pb2_grpc as vision_pb2_grpc

# Eğer emotion_server modülü varsa istek sayacını içe aktar
try:
    from emotion_server import increment_request_counter
    has_request_counter = True
except ImportError:
    has_request_counter = False
    def increment_request_counter():
        return 0

# Logging
logger = logging.getLogger("emotion-service")

class EmotionServiceServicer(vision_pb2_grpc.EmotionServiceServicer):
    """!
    @brief Implements the EmotionService gRPC servicer.
    
    This class handles requests from the Vision Service (or other clients)
    to analyze emotions from face images. It uses an instance of `EmotionAnalyzer`
    to perform the actual analysis.
    """
    
    def __init__(self, confidence_threshold: float = 0.35):
        """!
        @brief Initializes the EmotionServiceServicer.
        
        @param confidence_threshold The minimum confidence threshold to be used by the
                                   underlying `EmotionAnalyzer`. Defaults to 0.35.
        """
        self.emotion_analyzer = EmotionAnalyzer(confidence_threshold=confidence_threshold)
        logger.info("Geliştirilmiş Emotion Service başlatıldı (Güven eşiği: %.2f)", confidence_threshold)
        
    def AnalyzeEmotion(self, request: vision_pb2.FaceRequest, context: grpc.ServicerContext) -> vision_pb2.EmotionResponse:
        """!
        @brief Analyzes a face image to determine emotion.

        This method is called by gRPC clients. It decodes the face image from
        the request, uses `EmotionAnalyzer` to predict the emotion, and returns
        the result.
        
        @param request The incoming gRPC request object (vision_pb2.FaceRequest),
                       containing the `face_image` (bytes) and `face_id` (str).
        @param context The gRPC context object for the request.
            
        @return vision_pb2.EmotionResponse: A protobuf message containing the predicted
                                          `emotion` (str), `confidence` (float), and
                                          the original `face_id` (str). Returns an "error"
                                          emotion on processing failure.
        """
        # İstek sayacını artır
        if has_request_counter:
            request_count = increment_request_counter()
            
        start_time = time.time()
        logger.info(f"Duygu analizi isteği alındı (Yüz ID: {request.face_id})")
        
        try:
            # Giriş doğrulama
            if not request.face_image:
                logger.error("Boş yüz görüntüsü alındı")
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Yüz görüntüsü boş olamaz")
                return vision_pb2.EmotionResponse(emotion="error", confidence=0.0, face_id=request.face_id)
            
            # Yüz görüntüsünü numpy array'e çevir
            nparr = np.frombuffer(request.face_image, np.uint8)
            face_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if face_img is None or face_img.size == 0:
                logger.error("Geçersiz yüz görüntüsü formatı")
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Geçersiz görüntü formatı")
                return vision_pb2.EmotionResponse(emotion="error", confidence=0.0, face_id=request.face_id)

            # Geliştirilmiş duygu analizi
            logger.debug("Duygu analizi için yüz ön işleme yapılıyor...")
            
            try:
                # Yüz ön işleme
                processed_face = self.emotion_analyzer.preprocess_face(face_img)
                
                # Duygu analizi
                result = self.emotion_analyzer.analyze_emotion(
                    processed_face, 
                    face_id=request.face_id
                )
                
                dominant_emotion = result["emotion"]
                emotion_confidence = result["confidence"]
                
                # İşlem süresini hesapla
                process_time = time.time() - start_time
                
                logger.info(f"Yüz ID {request.face_id} için duygu analizi: {dominant_emotion}, güven: {emotion_confidence:.2f}, süre: {process_time:.3f}s")

                # Sonucu döndür
                return vision_pb2.EmotionResponse(
                    emotion=dominant_emotion,
                    confidence=float(emotion_confidence),
                    face_id=request.face_id
                )
            except Exception as inner_e:
                logger.error(f"Duygu analizi işlem hatası: {str(inner_e)}")
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(f"Duygu analizi işlem hatası: {str(inner_e)}")
                return vision_pb2.EmotionResponse(
                    emotion="error", 
                    confidence=0.0,
                    face_id=request.face_id
                )
                
        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"Yüz analiz işleme hatası: {str(e)}\n{error_trace}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Genel işlem hatası: {str(e)}")
            return vision_pb2.EmotionResponse(
                emotion="error", 
                confidence=0.0,
                face_id=request.face_id
            )
        finally:
            # İstek sayısını güncelle
            if has_request_counter:
                logger.info(f"Toplam istek sayısı: {request_count}")
            
            # İşlem süresini logla
            end_time = time.time()
            logger.debug(f"İşlem süresi: {end_time - start_time:.3f} saniye")
            