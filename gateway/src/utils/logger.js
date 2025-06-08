/**
 * @file logger.js
 * @module Logger
 * @brief Provides a simple logging utility for the Gateway application.
 *
 * This module wraps `console.log`, `console.error`, `console.warn` for standard
 * logging levels (INFO, ERROR, WARN) and uses the `debug` library for debug messages.
 * The debug messages are enabled based on the `DEBUG` environment variable,
 * configured via `config.debug`.
 */

const debug = require("debug");
const config = require("../config");

// Initialize debug logger instance with namespace from config
const debugLog = debug(config.debug);

/**
 * @brief Logger object with methods for different log levels.
 * @type {Object}
 * @property {function(string): void} info - Logs an informational message.
 * @property {function(string): void} error - Logs an error message.
 * @property {function(string): void} warn - Logs a warning message.
 * @property {function(string): void} debug - Logs a debug message (output depends on DEBUG env var).
 */
const logger = {
  /**
   * @brief Logs an informational message to the console.
   * @param {string} message - The message to log.
   */
  info: (message) => console.log(`[INFO] ${message}`),
  /**
   * @brief Logs an error message to the console.
   * @param {string} message - The message to log.
   */
  error: (message) => console.error(`[ERROR] ${message}`),
  /**
   * @brief Logs a warning message to the console.
   * @param {string} message - The message to log.
   */
  warn: (message) => console.warn(`[WARN] ${message}`),
  /**
   * @brief Logs a debug message using the 'debug' library.
   * Output is controlled by the DEBUG environment variable (e.g., `DEBUG=gateway:*`).
   * @param {string} message - The message to log.
   */
  debug: (message) => debugLog(message),
};

module.exports = logger;
