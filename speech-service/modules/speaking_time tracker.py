"""!
@file speaking_time tracker.py
@brief Tracks and calculates speaking times for different face IDs.

This module defines the SpeakingTimeTracker class, which monitors when
each identified face (via face_id) starts and stops speaking. It accumulates
total speaking time and can manage session timeouts for inactive faces.
"""
import time
import logging
from collections import defaultdict
from typing import Dict, Optional

logger = logging.getLogger("speaking-time-tracker")


class SpeakingTimeTracker:
    """!
    @brief Tracks speaking duration for multiple individuals identified by face_id.

    This class maintains a record for each face_id, tracking whether they are
    currently speaking, the start time of their current speaking session,
    their total accumulated speaking time, and the time of their last activity.
    It can also clean up data for faces that have been inactive beyond a specified timeout.
    """

    def __init__(self, session_timeout: float = 300.0):
        """!
        @brief Initializes the SpeakingTimeTracker.

        @param session_timeout The duration in seconds after which an inactive face's
                               data will be cleaned up. Defaults to 300.0 (5 minutes).
        """
        self.session_timeout = session_timeout

        # Her face_id için konuşma durumu takibi
        self.speaking_sessions: Dict[int, Dict] = defaultdict(lambda: {
            'is_currently_speaking': False,
            'current_session_start': None,
            'total_speaking_time': 0.0,
            'session_count': 0,
            'last_activity': time.time(),
            'current_session_time': 0.0
        })

        logger.info("Speaking Time Tracker başlatıldı")

    def update_speaking_status(self, face_id: int, is_speaking: bool) -> float:
        """!
        @brief Updates the speaking status for a given face_id and returns total speaking time.

        If the status changes from not speaking to speaking, a new session starts.
        If the status changes from speaking to not speaking, the current session ends,
        and its duration is added to the total speaking time.
        The last activity time for the face_id is always updated.

        @param face_id The unique identifier for the face.
        @param is_speaking A boolean indicating whether the person is currently speaking.

        @return float: The total accumulated speaking time for the given face_id in seconds.
        """
        current_time = time.time()
        session = self.speaking_sessions[face_id]
        session['last_activity'] = current_time

        # Durum değişikliği kontrolü
        was_speaking = session['is_currently_speaking']

        if is_speaking and not was_speaking:
            # Konuşma başladı
            session['is_currently_speaking'] = True
            session['current_session_start'] = current_time
            session['session_count'] += 1
            session['current_session_time'] = 0.0

            logger.debug(f"Face {face_id}: Konuşma başladı (Oturum #{session['session_count']})")

        elif not is_speaking and was_speaking:
            # Konuşma durdu
            if session['current_session_start'] is not None:
                session_duration = current_time - session['current_session_start']
                session['total_speaking_time'] += session_duration
                session['current_session_time'] = 0.0

                logger.debug(
                    f"Face {face_id}: Konuşma durdu (Süre: {session_duration:.2f}s, Toplam: {session['total_speaking_time']:.2f}s)")

            session['is_currently_speaking'] = False
            session['current_session_start'] = None

        elif is_speaking and was_speaking:
            # Konuşma devam ediyor - mevcut oturum süresini güncelle
            if session['current_session_start'] is not None:
                session['current_session_time'] = current_time - session['current_session_start']

        return self.get_total_speaking_time(face_id)

    def get_total_speaking_time(self, face_id: int) -> float:
        """!
        @brief Returns the total accumulated speaking time for a specific face_id.

        If the person is currently speaking, the duration of the ongoing session
        is included in the returned total.

        @param face_id The unique identifier for the face.

        @return float: The total speaking time in seconds.
        """
        session = self.speaking_sessions[face_id]
        total_time = session['total_speaking_time']

        # Eğer şu anda konuşuyorsa, mevcut oturum süresini de ekle
        if session['is_currently_speaking'] and session['current_session_start'] is not None:
            current_session_duration = time.time() - session['current_session_start']
            total_time += current_session_duration

        return total_time

    def get_current_session_time(self, face_id: int) -> float:
        """!
        @brief Returns the duration of the current speaking session for a face_id.

        If the person is not currently speaking, returns 0.0.

        @param face_id The unique identifier for the face.

        @return float: The duration of the current speaking session in seconds,
                       or 0.0 if not currently speaking.
        """
        session = self.speaking_sessions[face_id]

        if session['is_currently_speaking'] and session['current_session_start'] is not None:
            return time.time() - session['current_session_start']

        return 0.0

    def get_speaking_stats(self, face_id: int) -> Dict:
        """!
        @brief Retrieves detailed speaking statistics for a specific face_id.

        @param face_id The unique identifier for the face.

        @return Dict: A dictionary containing:
                      'face_id', 'is_currently_speaking' (bool),
                      'total_speaking_time' (float), 'current_session_time' (float),
                      'session_count' (int), 'last_activity' (timestamp),
                      'time_since_last_activity' (float).
        """
        session = self.speaking_sessions[face_id]
        current_time = time.time()

        stats = {
            'face_id': face_id,
            'is_currently_speaking': session['is_currently_speaking'],
            'total_speaking_time': self.get_total_speaking_time(face_id),
            'current_session_time': self.get_current_session_time(face_id),
            'session_count': session['session_count'],
            'last_activity': session['last_activity'],
            'time_since_last_activity': current_time - session['last_activity']
        }

        return stats

    def is_currently_speaking(self, face_id: int) -> bool:
        """!
        @brief Checks if a person is currently marked as speaking.

        @param face_id The unique identifier for the face.

        @return bool: True if the person is currently speaking, False otherwise.
        """
        return self.speaking_sessions[face_id]['is_currently_speaking']

    def clear_face_data(self, face_id: int):
        """!
        @brief Clears all tracking data associated with a specific face_id.

        @param face_id The unique identifier for the face whose data is to be cleared.
        """
        if face_id in self.speaking_sessions:
            stats = self.get_speaking_stats(face_id)
            logger.info(f"Face {face_id} verileri temizleniyor - Son istatistikler: {stats}")
            del self.speaking_sessions[face_id]

    def cleanup_inactive_faces(self) -> int:
        """!
        @brief Removes data for faces that have been inactive longer than the session_timeout.

        Iterates through all tracked faces and removes those whose 'last_activity'
        timestamp is older than the configured `session_timeout`.

        @return int: The number of faces whose data was cleaned up.
        """
        current_time = time.time()
        faces_to_remove = []

        for face_id, session in self.speaking_sessions.items():
            time_since_activity = current_time - session['last_activity']

            if time_since_activity > self.session_timeout:
                faces_to_remove.append(face_id)

        for face_id in faces_to_remove:
            self.clear_face_data(face_id)

        if faces_to_remove:
            logger.info(f"{len(faces_to_remove)} inaktif yüz temizlendi: {faces_to_remove}")

        return len(faces_to_remove)

    def get_all_stats(self) -> Dict[int, Dict]:
        """!
        @brief Retrieves speaking statistics for all tracked faces.

        @return Dict[int, Dict]: A dictionary where keys are face_ids and values are
                                 their respective statistics dictionaries (as returned by
                                 `get_speaking_stats`).
        """
        all_stats = {}
        for face_id in list(self.speaking_sessions.keys()): # Use list for safe iteration if clear_face_data can be called
            all_stats[face_id] = self.get_speaking_stats(face_id)

        return all_stats

    def reset_all_data(self):
        """!
        @brief Resets all tracking data for all faces.

        Clears all stored speaking sessions and logs the action.
        """
        face_count = len(self.speaking_sessions)
        self.speaking_sessions.clear()
        logger.info(f"Tüm konuşma verileri sıfırlandı ({face_count} yüz)")
