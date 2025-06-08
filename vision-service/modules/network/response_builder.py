"""!
@file response_builder.py
@brief Provides utility functions for creating gRPC message objects.

This module defines the ResponseBuilder class, which contains static methods
to construct `VisionResponse`, `DetectedFace`, and `FaceRequest` protobuf messages
from processed data. This helps in centralizing the logic for response creation.
"""

import proto.vision_pb2 as vision_pb2
from ..config.logger_config import setup_logger

# Logger'ı yapılandır
logger = setup_logger()


class ResponseBuilder:
    """!
    @brief Utility class for creating gRPC message objects.

    This class provides static methods to construct various protobuf messages
    used in the Vision Service, such as `VisionResponse`, `DetectedFace`,
    and `FaceRequest`.
    """
    
    @staticmethod
    def create_vision_response(processed_faces):
        """!
        @brief Creates a VisionResponse protobuf message from processed face data.
        
        @param processed_faces A list of dictionaries, where each dictionary contains
                               data for a single processed face (e.g., id, bbox, landmarks, image).
            
        @return vision_pb2.VisionResponse: The constructed gRPC response message.
                                         Returns a default VisionResponse(person_detected=False) on error.
        """
        try:
            # Ana yanıtı oluştur
            response = vision_pb2.VisionResponse(
                person_detected=len(processed_faces) > 0
            )
            
            # Her işlenmiş yüzü yanıta ekle
            for face_data in processed_faces:
                try:
                    detected_face = ResponseBuilder._create_detected_face(face_data)
                    if detected_face:
                        response.faces.append(detected_face)
                except Exception as face_error:
                    logger.error(f"DetectedFace oluşturma hatası: {str(face_error)}")
                    continue
            
            return response
            
        except Exception as e:
            logger.error(f"VisionResponse oluşturma hatası: {str(e)}")
            return vision_pb2.VisionResponse(person_detected=False)
    
    @staticmethod
    def _create_detected_face(face_data):
        """!
        @brief Creates a DetectedFace protobuf message from individual face data.
        @internal
        
        @param face_data A dictionary containing data for a single processed face,
                         including 'id', 'x', 'y', 'width', 'height', 'landmarks', and 'face_image'.
            
        @return vision_pb2.DetectedFace: The constructed DetectedFace message.
                                         Returns None if an error occurs during creation.
        """
        try:
            # DetectedFace nesnesini oluştur
            detected_face = vision_pb2.DetectedFace()
            detected_face.id = face_data['id']
            detected_face.x = face_data['x']
            detected_face.y = face_data['y']
            detected_face.width = face_data['width']
            detected_face.height = face_data['height']
            
            # Yüz landmark'larını ekle
            if face_data['landmarks'] is not None:
                detected_face.landmarks.extend([
                    float(coord) for point in face_data['landmarks'] for coord in point
                ])
            
            # Yüz görüntüsünü ekle
            if face_data['face_image'] is not None:
                detected_face.face_image = face_data['face_image']
            
            return detected_face
            
        except Exception as e:
            logger.error(f"DetectedFace oluşturma detay hatası: {str(e)}")
            return None
    
    @staticmethod
    def create_face_request(detected_face):
        """!
        @brief Creates a FaceRequest protobuf message from a DetectedFace message.

        This is used to prepare data to be sent to other services like
        Emotion Service or Speech Service.
        
        @param detected_face A vision_pb2.DetectedFace protobuf message.
            
        @return vision_pb2.FaceRequest: The constructed FaceRequest message.
                                       Returns None if an error occurs.
        """
        try:
            face_request = vision_pb2.FaceRequest(
                face_image=detected_face.face_image,
                face_id=detected_face.id,
                landmarks=detected_face.landmarks
            )
            return face_request
            
        except Exception as e:
            logger.error(f"FaceRequest oluşturma hatası: {str(e)}")
            return None
