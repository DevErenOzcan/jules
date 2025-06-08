import cv2
import dlib
import numpy as np
import os
import logging

logger = logging.getLogger("vision-service")

"""!
@file face_detector.py
@brief Provides the FaceDetector class for detecting faces and facial landmarks.

This module contains the `FaceDetector` class, which uses OpenCV and dlib
to perform face detection and identify key facial landmarks from an image.
It also includes functionality to extract basic feature vectors from face regions.
"""

class FaceDetector:
    """!
    @brief Class for face detection and landmark analysis.

    This class encapsulates the functionality for detecting human faces in images
    using Haar cascades and then finding facial landmarks using dlib's shape predictor.
    It also provides a method to extract simple image features from the detected face regions.
    """
    
    def __init__(self, cascade_path=None, landmark_path=None):
        """!
        @brief Initializes the FaceDetector.

        Loads the Haar cascade for face detection and the dlib shape predictor model
        for facial landmark detection.
        @param cascade_path Path to the Haar cascade XML file for face detection.
                            Defaults to `os.getenv('CASCADE_PATH', 'haarcascade_frontalface_default.xml')` if None.
        @param landmark_path Path to the dlib shape predictor model file for facial landmarks.
                             Defaults to `os.getenv('MODEL_PATH', 'shape_predictor_68_face_landmarks.dat')` if None.
        """
        # Parametreler verilmediyse varsayılan dosyaları kullan
        if cascade_path is None:
            cascade_path = os.getenv('CASCADE_PATH', 'haarcascade_frontalface_default.xml')
        if landmark_path is None:
            landmark_path = os.getenv('MODEL_PATH', 'shape_predictor_68_face_landmarks.dat')
            
        # Modelleri yükle
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        self.landmark_predictor = dlib.shape_predictor(landmark_path)
        
        logger.info(f"Yüz tespit modelleri yüklendi: {cascade_path} ve {landmark_path}")
        
    def detect_faces(self, image):
        """!
        @brief Detects faces in a given image.
        @param image The input image in OpenCV BGR format.
        @return faces A list of tuples, where each tuple `(x, y, w, h)` represents the bounding box of a detected face.
        @return gray The grayscale version of the input image, used for landmark detection.
        """
        # Gri tonlamaya çevir ve gürültü azalt
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Yüzleri tespit et
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.2, 
            minNeighbors=5, 
            minSize=(50, 50)
        )
        
        return faces, gray
    
    def get_landmarks(self, gray_image, face_rect):
        """!
        @brief Detects facial landmarks within a given face region.
        @param gray_image The grayscale image (output from `detect_faces`).
        @param face_rect A tuple `(x, y, w, h)` representing the bounding box of the face.
        @return A list of `(x,y)` coordinates for the detected facial landmarks. Returns an empty list on error.
        """
        try:
            x, y, w, h = face_rect
            rect = dlib.rectangle(int(x), int(y), int(x + w), int(y + h))
            dlib_landmarks = self.landmark_predictor(gray_image, rect)
            
            # dlib_landmarks nesnesini (x,y) koordinat çiftleri listesine dönüştür
            landmark_points = []
            for i in range(dlib_landmarks.num_parts):
                point = dlib_landmarks.part(i)
                landmark_points.append((point.x, point.y))
                
            return landmark_points
        except Exception as e:
            logger.error(f"Landmark tespiti hatası: {str(e)}")
            return []
        
    def extract_face_features(self, image, face_rect):
        """!
        @brief Extracts a feature vector from a detected face region.
        @param image The original color image.
        @param face_rect A tuple `(x, y, w, h)` representing the bounding box of the face.
        @return A NumPy array representing the extracted face features. Returns a zero vector if the face region is too small.
        """
        x, y, w, h = face_rect
        
        # Yüz bölgesini kes
        face_region = image[y:y+h, x:x+w]
        
        # Görüntü çok küçükse işleme
        if face_region.size == 0 or face_region.shape[0] < 10 or face_region.shape[1] < 10:
            return np.zeros(512)  # Boş öznitelik vektörü döndür #!< Return zero vector if face region is too small

        # Yüz bölgesini yeniden boyutlandır
        face_region = cv2.resize(face_region, (100, 100)) #!< Resize for consistent feature extraction
        
        # Histogram hesapla (RGB ve HSV uzayında daha gürbüz öznitelik)
        hist_rgb = cv2.calcHist([face_region], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256]) //!< Calculate RGB color histogram
        hist_rgb = cv2.normalize(hist_rgb, hist_rgb).flatten() //!< Normalize and flatten histogram
        
        # HSV renk uzayında da hesapla
        face_hsv = cv2.cvtColor(face_region, cv2.COLOR_BGR2HSV) //!< Convert to HSV color space
        hist_hsv = cv2.calcHist([face_hsv], [0, 1], None, [8, 8], [0, 180, 0, 256]) //!< Calculate HSV color histogram
        hist_hsv = cv2.normalize(hist_hsv, hist_hsv).flatten() //!< Normalize and flatten histogram
        
        # İki histogramı birleştir
        combined_features = np.concatenate((hist_rgb, hist_hsv)) //!< Combine RGB and HSV features
        
        return combined_features
