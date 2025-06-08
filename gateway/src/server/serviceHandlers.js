/**
 * @file serviceHandlers.js
 * @module ServiceHandlers
 * @brief Handles interactions with backend gRPC services, including request throttling, retries, and data processing.
 *
 * This module provides functions to process incoming video frames, call various
 * gRPC services (Vision, Emotion, Speech) with added reliability features like
 * throttling and retries, and then update a central data cache with the results.
 * It also includes utilities for batch processing and health checks.
 */

const clients = require("../services/clients");
const dataCache = require("../cache/dataCache");
const logger = require("../utils/logger");

/**
 * @class RequestThrottler
 * @brief Limits the rate of outgoing requests to a service.
 * Ensures that the number of requests sent per second does not exceed a specified maximum.
 */
class RequestThrottler {
  /**
   * @constructor
   * @brief Initializes the RequestThrottler.
   * @param {number} maxRequestsPerSecond - The maximum number of requests allowed per second.
   */
  constructor(maxRequestsPerSecond) {
    this.maxRequestsPerSecond = maxRequestsPerSecond;
    this.requestCount = 0;
    this.lastResetTime = Date.now();
  }

  /**
   * @brief Pauses execution if the request limit has been reached, until the next second window.
   * Increments the request count after ensuring the request can proceed.
   * @async
   * @returns {Promise<boolean>} A promise that resolves to true when the request can proceed.
   */
  async throttle() {
    const now = Date.now();

    if (now - this.lastResetTime > 1000) { // Reset counter every second
      this.requestCount = 0;
      this.lastResetTime = now;
    }

    if (this.requestCount >= this.maxRequestsPerSecond) {
      const waitTime = 1000 - (now - this.lastResetTime);
      if (waitTime > 0) {
        await new Promise((resolve) => setTimeout(resolve, waitTime));
        return this.throttle(); // Re-check after waiting
      }
    }

    this.requestCount++;
    return true;
  }
}

const visionThrottler = new RequestThrottler(10); // Max 10 vision requests/sec
const emotionThrottler = new RequestThrottler(15); // Max 15 emotion requests/sec
const speechThrottler = new RequestThrottler(15);  // Max 15 speech requests/sec

/**
 * @brief Processes a single video frame received from the frontend.
 *
 * It calls the Vision service to detect faces, then for each detected face,
 * it calls the Emotion and Speech services. Results are stored in the data cache.
 * Includes throttling for Vision service calls.
 * @async
 * @function processFrame
 * @param {Buffer} frameData - The raw image data of the video frame.
 * @returns {Promise<Object>} A promise that resolves to the Vision service response.
 * @throws {Error} If any critical error occurs during processing.
 */
async function processFrame(frameData) {
  logger.debug("Frontend'den bir frame alındı");
  const frameRequest = { image: frameData };

  try {
    await visionThrottler.throttle();
    const visionResponse = await callVisionServiceWithRetry(frameRequest); // Retries included
    if (validateResponse(visionResponse, "VisionService")) {
        dataCache.updateVisionData(visionResponse.faces);
        if (visionResponse.faces && visionResponse.faces.length > 0) {
            await batchProcessFaces(visionResponse.faces);
        }
    }
    return visionResponse;
  } catch (error) {
    logger.error("Frame işleme hatası:", error.message);
    throw error;
  }
}

/**
 * @brief Calls the Vision Service's AnalyzeFrame method.
 * @function callVisionService
 * @param {Object} frameRequest - The request object for AnalyzeFrame, containing image data.
 * @returns {Promise<Object>} A promise that resolves with the Vision service response.
 * @throws {Error} If the gRPC call fails.
 * @deprecated Use callVisionServiceWithRetry for added reliability.
 */
function callVisionService(frameRequest) {
  return new Promise((resolve, reject) => {
    clients.visionClient.AnalyzeFrame(frameRequest, (err, response) => {
      if (err) {
        logGrpcError("AnalyzeFrame", err);
        reject(err);
        return;
      }
      resolve(response);
    });
  });
}

/**
 * @brief Processes a single detected face by calling Emotion and Speech services.
 * Includes throttling for both service calls.
 * @async
 * @function processDetectedFace
 * @param {Object} face - A face object, typically from the Vision service response.
 *                        Expected to have `id`, `face_image`, and `landmarks`.
 */
async function processDetectedFace(face) {
  const faceRequest = {
    face_id: face.id,
    face_image: face.face_image,
    landmarks: face.landmarks,
  };

  try {
    await emotionThrottler.throttle();
    const emotionResponse = await callWithRetry(
      (req, cb) => clients.emotionClient.AnalyzeEmotion(req, cb),
      faceRequest
    );
    if (validateResponse(emotionResponse, "EmotionService")) {
        dataCache.updateEmotionData(emotionResponse);
    }
  } catch (err) {
    logger.error(`Duygu analizi hatası - Yüz ID ${face.id}: ${err.message}`);
  }

  try {
    await speechThrottler.throttle();
    const speechResponse = await callWithRetry(
      (req, cb) => clients.speechClient.DetectSpeech(req, cb),
      faceRequest
    );
    if (validateResponse(speechResponse, "SpeechService")) {
        dataCache.updateSpeechData(speechResponse);
    }
  } catch (err) {
    logger.error(`Konuşma tespiti hatası - Yüz ID ${face.id}: ${err.message}`);
  }
}

/**
 * @brief Logs detailed information about a gRPC error.
 * @function logGrpcError
 * @param {string} serviceName - The name of the service or method where the error occurred.
 * @param {Error} err - The gRPC error object.
 */
function logGrpcError(serviceName, err) {
  logger.error(`${serviceName} çağrısında hata:`, err.message);
  if (err.code) logger.error(`HATA KODU: ${err.code}`);
  if (err.details) logger.error(`HATA DETAYI: ${err.details}`);
  if (err.stack) logger.error(`HATA STACK: ${err.stack}`);
}

/**
 * @brief Generic function to call a gRPC service method with retry logic.
 * @async
 * @function callWithRetry
 * @param {function} serviceFn - The gRPC client method to call (e.g., `clients.visionClient.AnalyzeFrame`).
 *                               It should accept a request and a callback.
 * @param {Object} request - The request object to send to the service method.
 * @param {number} [maxRetries=3] - Maximum number of retry attempts.
 * @param {number} [delay=1000] - Delay in milliseconds between retries.
 * @returns {Promise<Object>} A promise that resolves with the service response.
 * @throws {Error} The last error encountered after all retries have failed.
 */
async function callWithRetry(serviceFn, request, maxRetries = 3, delay = 1000) {
  let lastError;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await new Promise((resolve, reject) => {
        // Ensure serviceFn is called in the context of its client if necessary
        // This might require binding or careful passing if serviceFn is a class method.
        // For simple client methods like `clients.visionClient.AnalyzeFrame`, direct call is fine.
        serviceFn(request, (err, response) => {
          if (err) reject(err);
          else resolve(response);
        });
      });
    } catch (error) {
      lastError = error;
      logger.warn(
        `Deneme ${attempt}/${maxRetries} başarısız (Servis: ${serviceFn.name || 'Bilinmeyen Servis'}): ${error.message}`
      );

      if (attempt < maxRetries) {
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }
  logGrpcError(serviceFn.name || 'Bilinmeyen Servis (Retry Sonrası)', lastError);
  throw lastError;
}

/**
 * @brief Calls the Vision Service's AnalyzeFrame method with retry logic.
 * @async
 * @function callVisionServiceWithRetry
 * @param {Object} frameRequest - The request object for AnalyzeFrame.
 * @returns {Promise<Object>} A promise that resolves with the Vision service response.
 */
async function callVisionServiceWithRetry(frameRequest) {
  return callWithRetry(
    (req, cb) => clients.visionClient.AnalyzeFrame(req, cb), // Correctly pass client method
    frameRequest
  );
}

/**
 * @brief Processes a batch of detected faces by calling `processDetectedFace` for each.
 * Faces are processed in chunks to manage concurrency.
 * @async
 * @function batchProcessFaces
 * @param {Array<Object>} faces - An array of face objects from the Vision service.
 */
async function batchProcessFaces(faces) {
  if (!faces || faces.length === 0) return;

  const BATCH_SIZE = 5; // Process 5 faces concurrently as a batch
  const faceChunks = [];

  for (let i = 0; i < faces.length; i += BATCH_SIZE) {
    faceChunks.push(faces.slice(i, i + BATCH_SIZE));
  }

  // Process each chunk of faces
  for (const chunk of faceChunks) {
    // Process faces within a chunk concurrently
    await Promise.all(chunk.map((face) => processDetectedFace(face)));
  }
}

/**
 * @brief Validates if a service response is non-null. Logs a warning if it is.
 * @function validateResponse
 * @param {Object|null|undefined} response - The service response to validate.
 * @param {string} serviceName - The name of the service for logging purposes.
 * @returns {boolean} True if the response is valid (not null/undefined), false otherwise.
 */
function validateResponse(response, serviceName) {
  if (!response) {
    logger.warn(`${serviceName} boş yanıt döndürdü`);
    return false;
  }
  return true;
}

/**
 * @brief Checks the health of backend gRPC services.
 * Currently, only checks the Vision service. Can be extended for other services.
 * @async
 * @function checkServicesHealth
 * @returns {Promise<Object>} A promise that resolves to an object indicating the health status
 *                            of each checked service (e.g., `{ vision: true, emotion: false }`).
 */
async function checkServicesHealth() {
  const healthStatus = {
    vision: false,
    emotion: false, // Placeholder for future implementation
    speech: false,  // Placeholder for future implementation
  };

  try {
    // Vision service health check (assuming HealthCheck RPC exists)
    // If HealthCheck is not standard, this might need adjustment or a different method.
    await callWithRetry(
      (req, cb) => {
        // Assuming HealthCheck method exists on visionClient.
        // If not, this will fail or a dummy request to an existing method might be used.
        // For a real health check, the service should expose a HealthCheck RPC.
        // This is a placeholder if vision.proto doesn't define HealthCheck.
        if (clients.visionClient.HealthCheck) {
            clients.visionClient.HealthCheck(req, cb);
        } else {
            // Fallback: try a lightweight, existing method or assume healthy if no check method
            cb(null, { status: 'SERVING' }); // Simulate a successful health check response
            logger.warn("VisionService HealthCheck RPC'si bulunamadı, varsayılan olarak sağlıklı kabul ediliyor.");
        }
      },
      {}, // Empty request for HealthCheck
      1 // Only one attempt for health check
    );
    healthStatus.vision = true;
  } catch (err) {
    logger.error("Vision servisi sağlık kontrolü başarısız:", err.message);
  }

  // TODO: Implement health checks for Emotion and Speech services similarly
  // For example:
  // try {
  //   await callWithRetry((req, cb) => clients.emotionClient.HealthCheck({}, cb), {}, 1);
  //   healthStatus.emotion = true;
  // } catch (err) { logger.error("Emotion servisi sağlık kontrolü başarısız:", err.message); }

  return healthStatus;
}

module.exports = {
  processFrame,
  callWithRetry, // Exporting for potential use elsewhere or testing
  batchProcessFaces,
  checkServicesHealth,
  RequestThrottler, // Exporting class for potential use elsewhere or testing
};
