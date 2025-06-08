"""
Çok daha hassas konuşma tespiti modülü
Düşük eşikler ve hızlı tepki için optimize edildi.
"""
import numpy as np
from collections import defaultdict, deque
import logging

logger = logging.getLogger("speech-detector")

"""!
@file speech_detector.py
@brief Defines the SpeechDetector class for detecting speech from facial landmarks.

This module contains the SpeechDetector class, which analyzes sequences of
facial landmarks, particularly mouth movements, to determine if a person is speaking.
It employs dynamic thresholding, calibration, and state management with cooldowns
to provide a sensitive and responsive speech detection mechanism.
"""

class SpeechDetector:
    """!
    @brief Detects speech by analyzing facial landmark movements, focusing on the mouth.

    This class processes sequences of facial landmarks to determine if a person
    is speaking. Key features include:
    - Extraction of mouth features (width, height, aspect ratio).
    - Dynamic threshold calibration per face ID based on initial mouth movements.
    - Analysis of movement variance in mouth features.
    - State management (speaking/not speaking) with cooldowns to prevent rapid flickering.
    - Blending of base and dynamic thresholds.
    """
    def __init__(
        self,
        base_threshold: float = 0.08,
        history_size: int = 8,
        cooldown_frames: int = 1,
        max_silence_frames: int = 10,
        calibration_frames: int = 10,
        alpha: float = 1.0,
        blend_factor: float = 0.8,
        min_opening_threshold: float = 0.1,
        smooth_window: int = 1,
    ):
        """!
        @brief Initializes the SpeechDetector.

        @param base_threshold Fallback threshold for movement detection if dynamic thresholding is not yet active.
        @param history_size The number of recent mouth feature sets to store per face ID for analysis.
        @param cooldown_frames Number of frames with movement required to transition to speaking,
                               or frames with no movement to transition to not-speaking.
        @param max_silence_frames Maximum number of consecutive frames without movement before forcing
                                  a transition to not-speaking, even if cooldown_frames is not met.
        @param calibration_frames Number of initial frames used to calibrate the dynamic threshold for each face ID.
        @param alpha Multiplier for standard deviation in dynamic threshold calculation (mu + alpha * sigma).
        @param blend_factor Factor to blend base_threshold and dynamic_threshold (0.0 = all base, 1.0 = all dynamic).
        @param min_opening_threshold Minimum average mouth aspect ratio required to be considered speaking,
                                     acting as a secondary check.
        @param smooth_window Size of the smoothing window for movement analysis (currently set to 1 for an instant response).
        """
        self.base_threshold = base_threshold
        self.history_size = history_size
        self.cooldown_frames = cooldown_frames
        self.max_silence_frames = max_silence_frames

        # Kalibrasyon
        self.calibration_frames = calibration_frames
        self.alpha = alpha
        self.calib_counts = defaultdict(int)
        self.calib_history = defaultdict(list)
        self.dynamic_threshold = {}

        # Eşik karışımı
        self.blend_factor = blend_factor
        self.min_opening_threshold = min_opening_threshold

        # Hareket filtresi
        self.smooth_window = smooth_window
        self.movement_history = defaultdict(lambda: deque(maxlen=smooth_window))

        # Kişi bazlı veri
        self.mouth_history = defaultdict(lambda: deque(maxlen=history_size))
        self.speaking_states = defaultdict(bool)
        self.cooldown_counters = defaultdict(int)
        self.silence_counters = defaultdict(int)

        logger.info("SpeechDetector (çok hassas) başlatıldı")

    def _extract_mouth_features(self, landmarks: list) -> dict or None:
        """!
        @brief Extracts mouth features (width, height, aspect ratio) from facial landmarks.
        @internal

        Assumes landmarks are provided as a flat list [x1, y1, x2, y2, ...].
        Specifically uses landmarks 48-67 (0-indexed) for mouth region.

        @param landmarks A flat list of landmark coordinates.
        @return A dictionary `{'width': float, 'height': float, 'ratio': float}`
                or None if landmarks are insufficient.
        """
        if not landmarks or len(landmarks) < 136: # Expecting 68 landmarks * 2 coordinates
            return None
        # Mouth landmarks are typically 48-67 (0-indexed for a 68-point model)
        # Convert flat list to list of (x,y) points for mouth
        pts = np.array([[landmarks[i*2], landmarks[i*2+1]] for i in range(48, 68)])
        w = np.linalg.norm(pts[6] - pts[0])
        top = np.mean(pts[13:16], axis=0)
        bot = np.mean(pts[16:20], axis=0)
        h = np.linalg.norm(top - bot)
        return {'width': w, 'height': h, 'ratio': h/(w+1e-6)}

    def detect_speaking(self, face_id: any, landmarks: list) -> bool:
        """!
        @brief Detects if a person is speaking based on their facial landmarks.

        This is the main public method for speech detection. It processes landmarks,
        performs calibration if needed, analyzes movement, and updates the speaking state.

        @param face_id The unique identifier for the face.
        @param landmarks A flat list of facial landmark coordinates.
        @return True if the person is determined to be speaking, False otherwise.
        """
        feats = self._extract_mouth_features(landmarks)
        if feats is None:
            logger.warning(f"Face{face_id}: Could not extract mouth features, insufficient landmarks.")
            return False

        # 1) Kalibrasyon
        if self.calib_counts[face_id] < self.calibration_frames:
            self.calib_history[face_id].append(feats['ratio'])
            self.calib_counts[face_id] += 1
            if self.calib_counts[face_id] == self.calibration_frames:
                arr = np.array(self.calib_history[face_id])
                mu, sigma = arr.mean(), arr.std()
                self.dynamic_threshold[face_id] = mu + self.alpha * sigma
                logger.info(f"Face{face_id} dinamik eşik: {self.dynamic_threshold[face_id]:.4f}")
            return False

        # 2) Geçmişe ekle
        self.mouth_history[face_id].append(feats)
        if len(self.mouth_history[face_id]) < 3:
            return False

        # 3) Hareket analizi
        moving = self._analyze_movement(face_id)

        # 4) Durumu güncelle
        self._update_state(face_id, moving)
        return self.speaking_states[face_id]

    def _analyze_movement(self, face_id: any) -> bool:
        """!
        @brief Analyzes mouth movement based on historical feature data.
        @internal

        Calculates variances of mouth height, aspect ratio, and width from recent history.
        Compares a smoothed movement score against a blended dynamic/base threshold.
        Also checks if the average mouth opening ratio exceeds a minimum threshold.

        @param face_id The unique identifier for the face.
        @return True if significant movement indicative of speech is detected, False otherwise.
        """
        recent = list(self.mouth_history[face_id])[-5:] # Analyze last 5 frames of features
        if not recent:
            return False
        heights = [f['height'] for f in recent]
        vars_h = np.var(heights) if len(heights)>1 else 0
        ratios = [f['ratio'] for f in recent]
        vars_r = np.var(ratios) if len(ratios)>1 else 0
        widths = [f['width'] for f in recent]
        vars_w = np.var(widths) if len(widths)>1 else 0

        raw = vars_h + vars_r + 0.5*vars_w
        # Anlık pencere → smooth_window=1
        mh = self.movement_history[face_id]
        mh.append(raw)
        smooth = sum(mh)/len(mh)

        # Eşik karışımı
        dyn = self.dynamic_threshold.get(face_id, self.base_threshold)
        thr = self.base_threshold*(1-self.blend_factor) + dyn*self.blend_factor

        # Çoklu koşullar
        cond1 = vars_h > thr*0.3
        cond2 = vars_r > thr*0.3
        cond3 = vars_w > thr*0.1
        primary = ((cond1 and cond2) or cond3) and (smooth > thr)

        # Düşük açılma eşiği
        opening_ok = np.mean(ratios) > self.min_opening_threshold

        moving = primary and opening_ok
        logger.debug(f"Face{face_id}: smooth={smooth:.4f}, thr={thr:.4f}, moving={moving}")
        return moving

    def _update_state(self, face_id: any, move: bool):
        """!
        @brief Updates the speaking state (speaking/not speaking) for a face ID.
        @internal

        Manages transitions between speaking and not-speaking states based on
        detected movement (`move`), cooldown counters, and silence counters.

        @param face_id The unique identifier for the face.
        @param move Boolean indicating if significant movement was detected in the current frame.
        """
        curr = self.speaking_states[face_id]
        if move:
            self.silence_counters[face_id] = 0
            if not curr:
                self.cooldown_counters[face_id] += 1
                if self.cooldown_counters[face_id] >= self.cooldown_frames:
                    self.speaking_states[face_id] = True
                    self.cooldown_counters[face_id] = 0
                    logger.info(f"Face{face_id} konuşma başladı")
            else:
                self.cooldown_counters[face_id] = 0
        else:
            self.silence_counters[face_id] += 1
            if curr:
                self.cooldown_counters[face_id] += 1
                if (self.cooldown_counters[face_id] >= self.cooldown_frames or
                    self.silence_counters[face_id] >= self.max_silence_frames):
                    self.speaking_states[face_id] = False
                    self.cooldown_counters[face_id] = 0
                    self.silence_counters[face_id] = 0
                    logger.info(f"Face{face_id} konuşma durdu")
            else:
                self.cooldown_counters[face_id] = 0

    def is_speaking(self, face_id: any) -> bool:
        """!
        @brief Returns the current speaking state for a given face ID.

        @param face_id The unique identifier for the face.
        @return True if the person is currently considered speaking, False otherwise.
                 Defaults to False if the face_id is unknown.
        """
        return self.speaking_states.get(face_id, False)

    def get_stats(self, face_id: any) -> dict:
        """!
        @brief Retrieves debugging statistics for a specific face ID.

        @param face_id The unique identifier for the face.
        @return A dictionary containing current state information:
                'speaking' (bool), 'frame_count' (int in history),
                'cooldown' (int), 'silence' (int), 'threshold' (float).
        """
        history = self.mouth_history.get(face_id, [])
        thr = self.dynamic_threshold.get(face_id, self.base_threshold)
        return {
            'speaking': self.speaking_states.get(face_id, False),
            'frame_count': len(history),
            'cooldown': self.cooldown_counters.get(face_id, 0),
            'silence': self.silence_counters.get(face_id, 0),
            'threshold': thr
        }

    def clear_face(self, face_id: any):
        """!
        @brief Clears all data associated with a specific face ID.
        @param face_id The identifier of the face to clear.
        """
        keys_to_clear_from = [
            self.mouth_history, self.speaking_states, self.cooldown_counters,
            self.silence_counters, self.movement_history,
            self.calib_history, self.calib_counts, self.dynamic_threshold
        ]
        for store in keys_to_clear_from:
            if face_id in store:
                del store[face_id]
        logger.info(f"Face{face_id} verileri temizlendi (SpeechDetector).")


    def clear_all(self):
        """!
        @brief Clears all stored data for all face IDs.

        Resets all internal dictionaries tracking mouth history, speaking states,
        cooldowns, silence counters, movement history, calibration data, and dynamic thresholds.
        """
        for d in (
            self.mouth_history, self.speaking_states, self.cooldown_counters,
            self.silence_counters, self.movement_history,
            self.calib_history, self.calib_counts, self.dynamic_threshold
        ):
            d.clear()
        logger.info("Tüm veriler temizlendi (SpeechDetector)")
