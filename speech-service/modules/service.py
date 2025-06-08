"""!
@file service.py
@brief Implements the gRPC servicer for the Speech Detection Service.

This module defines the `SpeechDetectionServicer` class, which handles
incoming gRPC requests for speech detection based on facial landmarks.
It utilizes `SpeechDetector` for instant speech detection and
`SpeakingTimeTracker` to accumulate speaking duration.
"""
import time
import logging
import os
from .speech_detector import SpeechDetector
from .speaking_time_tracker import SpeakingTimeTracker

# Proto dosyalarını import et
import proto.vision_pb2 as vision_pb2
import proto.vision_pb2_grpc as vision_pb2_grpc

logger = logging.getLogger("speech-service")

class SpeechDetectionServicer(vision_pb2_grpc.SpeechDetectionServiceServicer):
    """!
    @brief Implements the SpeechDetectionService gRPC servicer.

    This class handles requests for speech detection. It uses `SpeechDetector`
    to determine if a person is currently speaking based on facial landmarks,
    and `SpeakingTimeTracker` to track the cumulative speaking time for each face ID.
    """
    def __init__(self, config=None):
        """!
        @brief Initializes the SpeechDetectionServicer.
        
        Initializes instances of `SpeechDetector` and `SpeakingTimeTracker`.
        The `config` parameter is present but not currently used for specific
        configurations in this version, relying on defaults within the helper classes.

        @param config (dict, optional): Configuration settings. Currently unused but
                                      retained for future compatibility.
        """
        # Varsayılan konfigürasyon değerleri
        # Note: The original code had a comment here but no actual use of 'config'.
        # If config were used, it would be documented here.

        # Speech detector nesnesini oluştur
        self.speech_detector = SpeechDetector()

        # Speaking time tracker nesnesini oluştur
        self.time_tracker = SpeakingTimeTracker(session_timeout=300.0)  # 5 dakika timeout


    def DetectSpeech(self, request: vision_pb2.FaceRequest, context: grpc.ServicerContext) -> vision_pb2.SpeechResponse:
        """!
        @brief Detects speech based on facial landmarks from a FaceRequest.

        Processes a `FaceRequest` containing facial landmarks and a face ID.
        It determines if the person is speaking and updates their total speaking time.

        @param request The incoming gRPC request (vision_pb2.FaceRequest), which includes
                       `face_id` and `landmarks`.
        @param context The gRPC context object for the request.

        @return vision_pb2.SpeechResponse: A response containing `is_speaking` (bool),
                                         `speaking_time` (float), and `face_id` (str).
                                         Returns a default response with `is_speaking=False`
                                         on error or invalid input.
        """
        try:
            face_id = request.face_id
            landmarks = list(request.landmarks)

            logger.info(f"Konuşma tespiti isteği alındı (Yüz ID: {face_id}, Landmark sayısı: {len(landmarks)})")


            # Ayrıntı seviyesini ayarlamak için giriş doğrulama
            if not face_id or not landmarks:
                logger.warning("Geçersiz istek: face_id veya landmarks eksik")
                return vision_pb2.SpeechResponse(
                    is_speaking=False,
                    speaking_time=0.0,
                    face_id=request.face_id
                )
            logger.debug(f"Konuşma tespiti isteği alındı (Yüz ID: {face_id})")
              # Konuşma durumunu tespit et
            is_speaking = self.speech_detector.detect_speaking(face_id, landmarks)

            # Konuşma süresini güncelle ve al
            total_speaking_time = self.time_tracker.update_speaking_status(face_id, is_speaking)

            # İstatistikleri al
            stats = self.speech_detector.get_stats(face_id)
            time_stats = self.time_tracker.get_speaking_stats(face_id)

            logger.info(f"Yüz ID {face_id} için konuşma durumu: {is_speaking}, Toplam süre: {total_speaking_time:.2f}s")

            # Yanıt oluştur
            return vision_pb2.SpeechResponse(
                is_speaking=is_speaking,
                speaking_time=total_speaking_time,
                face_id=face_id
            )

        except Exception as e:
            logger.error(f"Konuşma tespiti hatası: {str(e)}", exc_info=True)
            return vision_pb2.SpeechResponse(
                is_speaking=False,
                speaking_time=0.0,
                face_id=request.face_id
            )
    def clear_face_data(self, face_id: str):
        """!
        @brief Clears data associated with a specific face ID from both detector and tracker.

        This method is primarily for internal management or explicit cleanup calls if needed.

        @param face_id The identifier of the face whose data needs to be cleared.
        """
        self.speech_detector.clear_face(face_id)
        self.time_tracker.clear_face_data(face_id)
        logger.info(f"Yüz ID {face_id} için veriler temizlendi.")

    def cleanup_inactive_data(self) -> int:
        """!
        @brief Cleans up data for inactive faces from the SpeakingTimeTracker.

        This method relies on the SpeakingTimeTracker's internal logic to identify
        and remove data for faces that have not been updated for a certain timeout period.

        @return int: The number of faces whose data was cleaned up.
        """
        cleaned_count = self.time_tracker.cleanup_inactive_faces()
        if cleaned_count > 0:
            logger.info(f"{cleaned_count} inaktif yüz verisi temizlendi.")
        return cleaned_count
