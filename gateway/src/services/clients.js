const grpc = require("@grpc/grpc-js");
const protoLoader = require("@grpc/proto-loader");
const path = require("path");
const config = require("../config");
/**
 * @file clients.js
 * @module GrpcClients
 * @brief Initializes and exports gRPC service clients for Vision, Emotion, and Speech services.
 *
 * This module loads the protocol buffer definitions for the services and creates
 * gRPC client instances configured to connect to the respective backend services
 * based on settings from the application configuration.
 */

const logger = require("../utils/logger");

/**
 * @brief Loads the vision.proto protocol buffer definition.
 * @function loadProtoDefinitions
 * @returns {Object} The loaded gRPC package definition for the vision proto.
 */
function loadProtoDefinitions() {
  const VISION_PROTO_PATH = path.join(
    __dirname, // current directory: 'src/services'
    "..",
    "..",
    "protos",
    "vision.proto"
  );
  return protoLoader.loadSync(VISION_PROTO_PATH, {
    keepCase: true,
    longs: String,
    enums: String,
    defaults: true,
    oneofs: true,
  });
}

/**
 * @brief Initializes and configures gRPC clients for backend services.
 *
 * Loads proto definitions and creates client instances for VisionService,
 * EmotionService, and SpeechDetectionService using connection details
 * from the application configuration.
 * @function initializeClients
 * @returns {Object} An object containing the initialized gRPC clients:
 *                   `visionClient`, `emotionClient`, and `speechClient`.
 */
function initializeClients() {
  const visionPackageDefinition = loadProtoDefinitions();
  const visionProto = grpc.loadPackageDefinition(
    visionPackageDefinition
  ).vision; // Assuming 'vision' is the package name in the .proto file

  const visionClient = new visionProto.VisionService(
    `${config.vision.host}:${config.vision.port}`,
    grpc.credentials.createInsecure() // Using insecure channel for simplicity
  );

  const emotionClient = new visionProto.EmotionService(
    `${config.emotion.host}:${config.emotion.port}`,
    grpc.credentials.createInsecure()
  );

  const speechClient = new visionProto.SpeechDetectionService(
    `${config.speech.host}:${config.speech.port}`,
    grpc.credentials.createInsecure()
  );

  logger.info(
    `Vision servisi bağlantısı kuruluyor: ${config.vision.host}:${config.vision.port}`
  );
  logger.info(
    `Emotion servisi bağlantısı kuruluyor: ${config.emotion.host}:${config.emotion.port}`
  );
  logger.info(
    `Speech Detection servisi bağlantısı kuruluyor: ${config.speech.host}:${config.speech.port}`
  );

  return {
    visionClient,
    emotionClient,
    speechClient,
  };
}

/**
 * Exports the initialized gRPC client instances.
 * @type {Object}
 * @property {visionProto.VisionService} visionClient - Client for VisionService.
 * @property {visionProto.EmotionService} emotionClient - Client for EmotionService.
 * @property {visionProto.SpeechDetectionService} speechClient - Client for SpeechDetectionService.
 */
module.exports = initializeClients();
