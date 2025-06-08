"""!
@file vision_service.py
@brief Implements the gRPC servicer for the Vision Service.

This module defines the `VisionServiceServicer` class, which handles
incoming gRPC requests for the Vision Service. It orchestrates the
face detection, tracking, and feature analysis processes, and communicates
with other backend services as needed.
"""

import proto.vision_pb2 as vision_pb2
import proto.vision_pb2_grpc as vision_pb2_grpc
from ..config.logger_config import setup_logger
from ..config.config_manager import ConfigManager
from ..config.grpc_config import GrpcConfig
from ..vision.face_detector import FaceDetector
from ..vision.face_tracker import FaceTracker
from ..vision.frame_processor import FrameProcessor
from ..network.service_client import ServiceClient
from ..network.response_builder import ResponseBuilder

# Logger'ı yapılandır
logger = setup_logger()


class VisionServiceServicer(vision_pb2_grpc.VisionServiceServicer):
    """!
    @brief Vision Service gRPC servicer implementation.

    This class implements the server-side logic for the VisionService gRPC interface.
    It handles requests to analyze video frames, detects faces, and coordinates
    further processing.
    """
    def __init__(self):
        """!
        @brief Initializes the VisionServiceServicer.

        Sets up configuration by loading application and gRPC settings.
        Initializes the FaceDetector for identifying faces in frames,
        FaceTracker for tracking faces across frames, FrameProcessor
        for orchestrating detection and tracking, and ServiceClient for
        communicating with other microservices.
        """
        
        # Yapılandırma yöneticisini başlat
        self.app_config = ConfigManager()
        
        # gRPC yapılandırmasını yükle
        self.config = GrpcConfig()
        
        # Alt modülleri başlat
        self.face_detector = FaceDetector(
            self.app_config.cascade_path,
            self.app_config.model_path
        )
        self.face_tracker = FaceTracker(
            similarity_threshold=self.app_config.face_match_threshold,
            cleanup_timeout=self.app_config.face_cleanup_timeout
        )
        
        # Frame işleyiciyi başlat
        self.frame_processor = FrameProcessor(self.face_detector, self.face_tracker)
        
        # Servis client'ını başlat
        self.service_client = ServiceClient(self.config)
        
        logger.info("Vision Service başlatıldı")

    def AnalyzeFrame(self, request, context):
        """!
        @brief Analyzes a single video frame for faces and other visual features.

        Processes the provided image data from the request, performs face detection
        and tracking, and then sends detected face information for further analysis
        by other services.
        @param request The incoming request object containing the image data (vision_pb2.VisionRequest).
        @param context The gRPC context object for the request.
        @return vision_pb2.VisionResponse containing detected faces and analysis results.
        @note Logs errors and returns a default VisionResponse (person_detected=False) on processing failure.
        """
        try:
            # Frame'i işle
            processed_faces, success = self.frame_processor.process_frame(request.image)
            
            if not success:
                logger.error("Frame işleme başarısız.")
                return vision_pb2.VisionResponse(person_detected=False)
            
            # ResponseBuilder kullanarak yanıt oluştur
            response = ResponseBuilder.create_vision_response(processed_faces)
            
            # Her tespit edilen yüzü diğer servislere gönder
            for detected_face in response.faces:
                self._process_detected_face(detected_face)
            
            return response
            
        except Exception as e:
            logger.error(f"AnalyzeFrame hatası: {str(e)}")
            return vision_pb2.VisionResponse(person_detected=False)
        
    def _process_detected_face(self, detected_face):
        """!
        @brief Processes a detected face by sending its information to other services (e.g., emotion, speech).
        @internal This method is intended for internal use within the servicer.

        Takes a `DetectedFace` object and forwards it to configured downstream
        services (like emotion or speech services) for further processing.
        @param detected_face A vision_pb2.DetectedFace object representing the detected face.
        """
        
        # ResponseBuilder kullanarak FaceRequest oluştur
        face_request = ResponseBuilder.create_face_request(detected_face)
        
        if face_request:
            # ServiceClient kullanarak asenkron olarak gönder
            self.service_client.process_detected_face_async(face_request)
