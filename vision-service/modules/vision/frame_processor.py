
import cv2
import numpy as np
import time
from ..config.logger_config import setup_logger

logger = setup_logger()

"""!
@file frame_processor.py
@brief Provides the FrameProcessor class for processing video frames.

This module defines the FrameProcessor class, which orchestrates the decoding
of image data, face detection, landmark extraction, feature extraction,
face tracking, and encoding of processed face images.
"""

class FrameProcessor:
    """!
    @brief Class for processing individual video frames.

    This class uses a FaceDetector and a FaceTracker to identify and process
    faces within a given video frame. It handles decoding of the input image,
    extracting face regions, and encoding processed face data.
    """
    
    def __init__(self, face_detector, face_tracker):
        """!
        @brief Initializes the FrameProcessor.
        
        @param face_detector An instance of FaceDetector for face and landmark detection.
        @param face_tracker An instance of FaceTracker for identifying and tracking faces.
        """
        self.face_detector = face_detector
        self.face_tracker = face_tracker
        logger.info("Frame işleyici başlatıldı")
    
    def decode_frame(self, image_data):
        """!
        @brief Decodes image data into an OpenCV image (NumPy array).
        
        @param image_data Binary image data (e.g., from a JPEG or PNG file).
            
        @return tuple: (img, success) - The decoded OpenCV image (BGR format)
                      and a boolean indicating success. Returns (None, False) on failure.
        """
        try:
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                logger.error("Gelen görüntü decode edilemedi.")
                return None, False
                
            return img, True
        except Exception as e:
            logger.error(f"Frame decode hatası: {str(e)}")
            return None, False
    
    def extract_face_region(self, img, face_coords):
        """!
        @brief Extracts a region of interest (face) from an image.
        
        @param img The source OpenCV image.
        @param face_coords A tuple (x, y, w, h) representing the bounding box of the face.
            
        @return numpy.ndarray: The cropped face image.
        """
        x, y, w, h = face_coords
        return img[y:y+h, x:x+w].copy()
    
    def encode_face_image(self, face_img):
        """!
        @brief Encodes a face image into JPEG format.
        
        @param face_img The OpenCV image of the face.
            
        @return tuple: (encoded_data, success) - The JPEG encoded image data (bytes)
                      and a boolean indicating success. Returns (None, False) on failure.
        """
        try:
            is_success, encoded_img = cv2.imencode('.jpg', face_img)
            if is_success:
                return bytes(encoded_img), True
            else:
                logger.warning("Yüz görüntüsü encode edilemedi")
                return None, False
        except Exception as e:
            logger.error(f"Yüz görüntüsü encode hatası: {str(e)}")
            return None, False
    
    def process_frame(self, image_data):
        """!
        @brief Processes a complete video frame.

        This method decodes the image, detects faces, processes each detected face
        (extracts landmarks, features, assigns ID), and cleans up old tracked faces.
        
        @param image_data Binary image data for the frame.
            
        @return tuple: (processed_faces, success) - A list of dictionaries, where each
                      dictionary contains data for a processed face, and a boolean
                      indicating overall success. Returns ([], False) on major failure.
        """
        # Frame'i decode et
        img, decode_success = self.decode_frame(image_data)
        if not decode_success:
            return [], False
        
        current_time = time.time()
        processed_faces = []
        
        try:
            # Yüzleri tespit et
            faces, gray = self.face_detector.detect_faces(img)
            logger.info(f"Frame analizi: {len(faces)} yüz tespit edildi")
            
            # Her yüzü işle
            for (x, y, w, h) in faces:
                try:
                    face_data = self._process_single_face(img, gray, (x, y, w, h), current_time)
                    if face_data:
                        processed_faces.append(face_data)
                except Exception as face_error:
                    logger.error(f"Yüz işleme hatası: {str(face_error)}")
                    continue
            
            # Eski yüzleri temizle
            self.face_tracker.clean_old_faces(current_time)
            
            return processed_faces, True
            
        except Exception as e:
            logger.error(f"Frame işleme hatası: {str(e)}")
            return [], False
    
    def _process_single_face(self, img, gray, face_coords, current_time):
        """!
        @brief Processes a single detected face within a frame.
        @internal

        This method extracts landmarks, features, identifies the face using the
        face tracker, crops the face image, and encodes it.
        
        @param img The full color OpenCV image of the frame.
        @param gray The grayscale OpenCV image of the frame.
        @param face_coords A tuple (x, y, w, h) for the detected face's bounding box.
        @param current_time The current timestamp.
            
        @return dict: A dictionary containing the processed face data including ID,
                      bounding box, landmarks, and the encoded face image. Returns None on error.
        """
        x, y, w, h = face_coords
        
        # Yüz landmark noktalarını al
        landmarks = self.face_detector.get_landmarks(gray, face_coords)
        
        # Yüz özniteliklerini çıkar
        face_encoding = self.face_detector.extract_face_features(img, face_coords)
        
        # Yüzü tanımla
        face_id = self.face_tracker.identify_face(face_encoding, current_time)
        
        # Yüz bölgesini kes
        face_img = self.extract_face_region(img, face_coords)
        
        # Yüz görüntüsünü encode et
        encoded_face, encode_success = self.encode_face_image(face_img)
        
        return {
            'id': face_id,
            'x': x,
            'y': y,
            'width': w,
            'height': h,
            'landmarks': landmarks,
            'face_image': encoded_face if encode_success else None
        }
