/**
 * @file index.js
 * @module GatewayApplication
 * @brief Main entry point and application starter for the Gateway.
 *
 * This module initializes and starts the core components of the gateway application,
 * including the data cache cleanup timer, the WebSocket server, and global error handlers.
 * It differs from `gateway/server.js` and appears to be a more structured approach
 * to starting the application, likely intended as the primary entry point for this `src` structure.
 */

const logger = require("./utils/logger");
const dataCache = require("./cache/dataCache");
const websocketServer = require("./server/websocket");

/**
 * @brief Starts the gateway application.
 *
 * Initializes the data cache cleanup, creates the WebSocket server,
 * and sets up global error handlers.
 * @function startApplication
 * @returns {Object} The WebSocket server instance (wss).
 * @throws {Error} If the application fails to start, logs the error and exits the process.
 */
function startApplication() {
  try {
    dataCache.startCleanupTimer();

    const wss = websocketServer.createWebSocketServer();

    setupErrorHandlers();

    return wss;
  } catch (error) {
    logger.error(`Uygulama başlatılamadı: ${error.message}`);
    process.exit(1);
  }
}

/**
 * @brief Sets up global error handlers for the application.
 *
 * Handles uncaught exceptions, unhandled promise rejections, and SIGINT (Ctrl+C)
 * for graceful shutdown.
 * @function setupErrorHandlers
 */
function setupErrorHandlers() {
  process.on("uncaughtException", (err) => {
    logger.error(`Yakalanmayan İstisna: ${err.message}`);
    logger.error(err.stack);
    // Consider a more graceful shutdown or restart mechanism here
  });

  process.on("unhandledRejection", (reason, promise) => {
    logger.error("İşlenmeyen Promise Reddi:", promise);
    logger.error("Sebep:", reason);
  });

  process.on("SIGINT", () => {
    logger.info("Uygulama kapatma isteği alındı (SIGINT)");
    dataCache.stopCleanupTimer();
    // Perform any other necessary cleanup before exiting
    process.exit(0);
  });
}

// Uygulamayı başlat
const server = startApplication();

/**
 * @brief The main WebSocket server instance.
 * Exported primarily for testing purposes.
 * @type {Object}
 */
module.exports = server;
