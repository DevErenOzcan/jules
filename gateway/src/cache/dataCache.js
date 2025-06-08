/**
 * @file dataCache.js
 * @module DataCache
 * @brief Manages an in-memory cache for face, emotion, and speech data.
 *
 * This module defines the DataCache class, which stores data received from
 * backend services (Vision, Emotion, Speech). It provides methods to update
 * and retrieve this data, and includes a mechanism for periodically cleaning up
 * stale entries based on a timeout.
 */

const logger = require("../utils/logger");
const config = require("../config");

/**
 * @class DataCache
 * @brief Manages an in-memory cache for real-time data from various services.
 *
 * Stores data related to detected faces, their emotions, and speech status.
 * Includes a cleanup mechanism to remove stale data.
 */
class DataCache {
  /**
   * @constructor
   * @brief Initializes the DataCache.
   * Sets up the internal data structure and prepares the cleanup timer (but does not start it).
   */
  constructor() {
    this.data = {
      faces: {},       // Stores face bounding box and image data
      emotions: {},    // Stores emotion analysis results
      speechStatus: {},// Stores speech detection results
      lastUpdate: {},  // Stores timestamps of the last update for each faceId
    };
    this.cleanupTimer = null;
  }

  /**
   * @brief Starts the periodic cache cleanup timer.
   * The interval and data timeout values are sourced from the application configuration.
   */
  startCleanupTimer() {
    const cleanupInterval = config.cache.cleanupInterval || 10000;
    this.cleanupTimer = setInterval(() => this.cleanup(), cleanupInterval);
    logger.debug(
      `Önbellek temizleme zamanlayıcısı başlatıldı (aralık: ${cleanupInterval}ms)`
    );
  }

  /**
   * @brief Performs the cleanup of stale data from the cache.
   * Iterates through `lastUpdate` timestamps and removes entries older than the configured timeout.
   * @method cleanup
   */
  cleanup() {
    const now = Date.now();
    const timeout = config.cache.dataTimeout || 10000;

    for (const faceId in this.data.lastUpdate) {
      if (now - this.data.lastUpdate[faceId] > timeout) {
        this.removeFace(faceId);
      }
    }
  }

  /**
   * @brief Removes a specific face and all its associated data from the cache.
   * @param {string|number} faceId - The ID of the face to remove.
   */
  removeFace(faceId) {
    delete this.data.faces[faceId];
    delete this.data.emotions[faceId];
    delete this.data.speechStatus[faceId];
    delete this.data.lastUpdate[faceId];
    logger.debug(`Yüz ID ${faceId} önbellekten temizlendi (timeout)`);
  }

  /**
   * @brief Updates the cache with vision data (detected faces).
   * @param {Array<Object>} faces - An array of face objects from the Vision Service.
   * Each face object should contain `id`, `face_image`, `x`, `y`, `width`, `height`.
   */
  updateVisionData(faces) {
    if (!faces) return;

    const now = Date.now();
    faces.forEach((face) => {
      const faceId = face.id;

      this.data.faces[faceId] = {
        id: faceId,
        face_image: face.face_image, // This is raw bytes
        x: face.x,
        y: face.y,
        width: face.width,
        height: face.height,
      };

      this.data.lastUpdate[faceId] = now;
    });
  }

  /**
   * @brief Updates the cache with emotion data for a specific face.
   * @param {Object} emotionResponse - The emotion response object from the Emotion Service.
   * Expected to have `face_id`, `emotion`, and `confidence`.
   */
  updateEmotionData(emotionResponse) {
    if (!emotionResponse) return;

    const faceId = emotionResponse.face_id;
    const now = Date.now();

    this.data.emotions[faceId] = {
      emotion: emotionResponse.emotion,
      confidence: emotionResponse.confidence,
    };

    this.data.lastUpdate[faceId] = now;
    logger.debug(
      `Duygu analizi güncellendi - Yüz ID: ${faceId}, Duygu: ${emotionResponse.emotion}`
    );
  }

  /**
   * @brief Updates the cache with speech data for a specific face.
   * @param {Object} speechResponse - The speech response object from the Speech Service.
   * Expected to have `face_id`, `is_speaking`, and `speaking_time`.
   */
  updateSpeechData(speechResponse) {
    if (!speechResponse) return;

    const faceId = speechResponse.face_id;
    const now = Date.now();

    this.data.speechStatus[faceId] = {
      is_speaking: speechResponse.is_speaking,
      speaking_time: speechResponse.speaking_time,
    };

    this.data.lastUpdate[faceId] = now;
    logger.debug(
      `Konuşma durumu güncellendi - Yüz ID: ${faceId}, Konuşuyor: ${speechResponse.is_speaking}`
    );
  }

  /**
   * @brief Retrieves combined data for all currently active faces in the cache.
   *
   * For each face, it combines face data, emotion data (or defaults if not present),
   * and speech data (or defaults if not present). Face images are converted to Base64 strings.
   * @returns {Object} An object containing a `speakers` array. Each element in the
   *                   `speakers` array represents a face and includes its `id`, `face_image` (Base64),
   *                   `emotion`, `emotion_confidence`, `is_speaking`, and `speaking_time`.
   *                   Returns `{ speakers: [] }` if no faces are active.
   */
  getCombinedData() {
    const activeFaceIds = Object.keys(this.data.faces);

    if (activeFaceIds.length === 0) {
      return { speakers: [] };
    }

    return {
      speakers: activeFaceIds.map((faceId) => {
        const faceData = this.data.faces[faceId] || {};
        const emotionData = this.data.emotions[faceId] || {
          emotion: "unknown",
          confidence: 0.0,
        };
        const speechData = this.data.speechStatus[faceId] || {
          is_speaking: false,
          speaking_time: 0.0,
        };

        let base64FaceImage = null;
        if (faceData.face_image) {
          const buffer = Buffer.isBuffer(faceData.face_image)
            ? faceData.face_image
            : Buffer.from(faceData.face_image);
          base64FaceImage = buffer.toString("base64");
        }

        return {
          id: parseInt(faceId),
          face_image: base64FaceImage,
          emotion: emotionData.emotion,
          emotion_confidence: emotionData.confidence,
          is_speaking: speechData.is_speaking,
          speaking_time: speechData.speaking_time,
        };
      }),
    };
  }

  /**
   * @brief Stops the periodic cache cleanup timer.
   */
  stopCleanupTimer() {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = null;
      logger.debug("Önbellek temizleme zamanlayıcısı durduruldu");
    }
  }
}

/**
 * Exports a singleton instance of the DataCache.
 * @type {DataCache}
 */
module.exports = new DataCache();
