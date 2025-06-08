import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import logging
import time

logger = logging.getLogger("vision-service")

"""!
@file face_tracker.py
@brief Provides the FaceTracker class for identifying and tracking faces over time.

This module contains the FaceTracker class, which assigns unique IDs to detected
faces based on their feature encodings. It maintains a database of known faces
and can clean up old entries that haven't been seen for a specified timeout.
"""

class FaceTracker:
    """!
    @brief Class for tracking faces using feature encodings.

    This class manages a database of face encodings and assigns an ID to each
    unique face. It uses cosine similarity to compare new face encodings with
    stored ones. Faces that are not seen for a certain period are removed
    from the database.
    """

    def __init__(self, similarity_threshold=0.4, cleanup_timeout=5.0):
        """!
        @brief Initializes the FaceTracker.

        @param similarity_threshold The minimum cosine similarity score to consider
                                   a face as a match to an existing one. Defaults to 0.4.
        @param cleanup_timeout The time in seconds after which an unseen face is
                               removed from the database. Defaults to 5.0.
        """
        self.face_match_threshold = similarity_threshold
        self.face_cleanup_timeout = cleanup_timeout

        self.face_database = {}
        self.next_id = 1
        self.last_seen = {}

        logger.info("Yüz takip modülü başlatıldı")

    def identify_face(self, face_encoding, current_time):
        """!
        @brief Identifies a face based on its encoding or assigns a new ID.

        Compares the given face encoding with the stored encodings in the database.
        If a match above the similarity threshold is found, the existing ID is returned
        and the stored encoding is updated using a moving average. Otherwise, a new
        ID is assigned, and the encoding is added to the database.

        @param face_encoding The feature vector (NumPy array) of the detected face.
        @param current_time The current timestamp (e.g., `time.time()`).
        @return The integer ID assigned to the face.
        """
        best_match_id = None
        best_match_score = -1

        # Kayıtlı yüzlerle karşılaştır
        for face_id, stored_encoding in self.face_database.items():
            # Benzerlik skoru hesapla (cosine similarity)
            similarity = cosine_similarity([face_encoding], [stored_encoding])[0][0]

            if similarity > self.face_match_threshold and similarity > best_match_score:
                best_match_id = face_id
                best_match_score = similarity

        # Eşleşme bulunamadıysa yeni ID ata
        if best_match_id is None:
            best_match_id = self.next_id
            self.face_database[best_match_id] = face_encoding
            self.next_id += 1
            logger.info(f"Yeni yüz tespit edildi. ID: {best_match_id}")
        else:
            # Kayan ortalama ile öznitelikleri güncelle
            self.face_database[best_match_id] = 0.7 * self.face_database[best_match_id] + 0.3 * face_encoding

        # Son görülme zamanını güncelle
        self.last_seen[best_match_id] = current_time

        return best_match_id

    def clean_old_faces(self, current_time, callback=None):
        """!
        @brief Removes faces from the database that haven't been seen for a while.

        Iterates through the tracked faces and removes any face whose last seen time
        exceeds the `cleanup_timeout`. An optional callback can be invoked for each
        removed face.

        @param current_time The current timestamp (e.g., `time.time()`).
        @param callback An optional function to call when a face is removed.
                        It will be called with the face_id as an argument.
        @return A list of IDs of the faces that were removed.
        """
        ids_to_remove = []
        for face_id, last_time in self.last_seen.items():
            if current_time - last_time > self.face_cleanup_timeout:
                ids_to_remove.append(face_id)

        for face_id in ids_to_remove:
            if face_id in self.face_database:
                del self.face_database[face_id]
            if face_id in self.last_seen:
                del self.last_seen[face_id]

            # Callback fonksiyonu varsa çağır
            if callback is not None:
                callback(face_id)

            logger.info(f"Yüz {face_id} artık görünmediği için temizlendi")

        return ids_to_remove
