/**
 * @file index.js
 * @module GatewayConfig
 * @brief Configuration settings for the Gateway application.
 *
 * This module loads environment variables using `dotenv` and exports a
 * configuration object with settings for the server (WebSocket), backend gRPC services
 * (Vision, Emotion, Speech), data cache, YouTube streaming, and debugging.
 * Default values are provided for most settings if corresponding environment
 * variables are not set.
 */

const dotenv = require("dotenv");
dotenv.config(); // Load environment variables from .env file

/**
 * @brief Configuration object for the Gateway application.
 * @type {Object}
 * @property {Object} server - WebSocket server settings.
 * @property {number} server.port - Port for the WebSocket server.
 * @property {string} server.host - Host for the WebSocket server.
 * @property {string} server.wsPath - Path for the WebSocket endpoint.
 * @property {number} server.pingInterval - Interval for WebSocket keep-alive pings (ms).
 * @property {number} server.updateInterval - Interval for sending data updates to clients (ms).
 * @property {Object} vision - Vision gRPC service connection settings.
 * @property {string} vision.host - Host for the Vision service.
 * @property {number} vision.port - Port for the Vision service.
 * @property {Object} emotion - Emotion gRPC service connection settings.
 * @property {string} emotion.host - Host for the Emotion service.
 * @property {number} emotion.port - Port for the Emotion service.
 * @property {Object} speech - Speech Detection gRPC service connection settings.
 * @property {string} speech.host - Host for the Speech service.
 * @property {number} speech.port - Port for the Speech service.
 * @property {Object} cache - Data cache settings.
 * @property {number} cache.cleanupInterval - Interval for cleaning up stale cache data (ms).
 * @property {number} cache.dataTimeout - Duration after which cache data is considered stale (ms).
 * @property {Object} youtube - YouTube streaming settings.
 * @property {number} youtube.maxConcurrentStreams - Maximum number of concurrent YouTube streams.
 * @property {number} youtube.frameRate - Frame rate for capturing from YouTube streams.
 * @property {string} youtube.quality - Quality setting for YouTube streams (e.g., 'highestvideo').
 * @property {number} youtube.timeout - Timeout for YouTube stream processing (ms).
 * @property {string} debug - Debug string for the 'debug' library (e.g., 'gateway:*').
 */
module.exports = {
  server: {
    port: process.env.PORT || 8080,
    host: process.env.HOST || "localhost",
    wsPath: process.env.WS_PATH || "/ws",
    pingInterval: parseInt(process.env.WS_PING_INTERVAL || "30000"),
    updateInterval: parseInt(process.env.UPDATE_INTERVAL || "100"),
  },
  vision: {
    host: process.env.VISION_SERVICE_HOST || "localhost",
    port: process.env.VISION_SERVICE_PORT || 50051,
  },
  emotion: {
    host: process.env.EMOTION_SERVICE_HOST || "localhost",
    port: process.env.EMOTION_SERVICE_PORT || 50052,
  },
  speech: {
    host: process.env.SPEECH_SERVICE_HOST || "localhost",
    port: process.env.SPEECH_SERVICE_PORT || 50053,
  },
  cache: {
    cleanupInterval: 10000, // Default: 10 seconds
    dataTimeout: 10000,     // Default: 10 seconds
  },
  youtube: {
    maxConcurrentStreams: parseInt(process.env.MAX_CONCURRENT_STREAMS || "3"),
    frameRate: parseInt(process.env.YOUTUBE_FRAME_RATE || "1"), // Default: 1 FPS
    quality: process.env.YOUTUBE_QUALITY || "highestvideo",
    timeout: parseInt(process.env.YOUTUBE_TIMEOUT || "30000"), // Default: 30 seconds
  },
  debug: process.env.DEBUG || "gateway:*",
};
