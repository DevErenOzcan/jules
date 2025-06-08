/**
 * @file websocket.js
 * @module WebSocketServer
 * @brief Manages the WebSocket server, client connections, and message handling for the Gateway.
 *
 * This module sets up a WebSocket server that listens for client connections.
 * It handles incoming messages, which can be either binary video frames for analysis
 * or JSON commands (e.g., to start/stop YouTube video analysis). It orchestrates
 * the processing of this data via `serviceHandlers` and broadcasts aggregated
 * analysis results from `dataCache` back to connected clients. It also manages
 * YouTube stream processing using `ytdl-core` and `ffmpeg`.
 */

const WebSocket = require("ws");
const config = require("../config");
const logger = require("../utils/logger");
const dataCache = require("../cache/dataCache");
const serviceHandlers = require("./serviceHandlers");
const ytdl = require("@distube/ytdl-core");
const ffmpeg = require("fluent-ffmpeg");
const ffmpegInstaller = require("@ffmpeg-installer/ffmpeg");
ffmpeg.setFfmpegPath(ffmpegInstaller.path);

/**
 * @brief Creates and initializes the WebSocket server.
 *
 * Configures the server with port, path, ping interval, and client verification.
 * Sets up event listeners for server errors and new client connections.
 * Also handles graceful shutdown on SIGINT.
 * @function createWebSocketServer
 * @returns {WebSocket.Server} The configured WebSocket server instance.
 */
function createWebSocketServer() {
  const wss = new WebSocket.Server({
    port: config.server.port,
    path: config.server.wsPath, // Ensure this path is correctly configured
    pingInterval: config.server.pingInterval,
    verifyClient: (info) => {
      const origin = info.origin || info.req.headers.origin;
      logger.debug(`WebSocket bağlantı isteği: ${origin}`);
      return true;
    },
  });

  logger.info(
    `WebSocket sunucusu çalışıyor: ws://<host>:${config.server.port}${config.server.wsPath}`
  );

  wss.on("error", (error) => {
    logger.error(`WebSocket sunucu hatası: ${error.message}`);
  });

  wss.on("connection", handleClientConnection);
  // Uygulama kapatılırken temizlik
  process.on("SIGINT", () => {
    logger.info("WebSocket sunucusu kapatılıyor...");
    wss.close();
  });

  return wss;
}

/**
 * @brief Handles a new client WebSocket connection.
 *
 * Sets up message handlers for binary frames and JSON commands (YouTube analysis).
 * Also handles 'close' and 'error' events for the client connection and
 * starts a timer to periodically send aggregated data to the client.
 * @function handleClientConnection
 * @param {WebSocket} ws - The WebSocket instance for the connected client.
 * @param {http.IncomingMessage} req - The HTTP GET request that initiated the WebSocket connection.
 */
function handleClientConnection(ws, req) {
  const clientIP = req.socket.remoteAddress;
  logger.info(`İstemci WebSocket ile bağlandı: ${clientIP}`);

  let clientData = {
    activeYouTubeStreams: new Map(), // Stores active ffmpeg processes for this client
    updateTimer: null,
  };

  clientData.updateTimer = setInterval(() => {
    sendDataToClient(ws);
  }, config.server.updateInterval);

  ws.on("message", async (data, isBinary) => {
    if (isBinary) {
      try {
        await serviceHandlers.processFrame(data);
        // Data is sent periodically by updateTimer, but an immediate send might be desired here too.
        // sendDataToClient(ws); // Optional: send immediate update
      } catch (err) {
        handleError(err, ws); // Send error to client
      }
      return;
    }

    // Process text messages (JSON commands)
    let parsedMessage;
    try {
      parsedMessage = JSON.parse(data.toString());
    } catch (e) {
      logger.warn(`Geçersiz JSON mesajı alındı: ${data.toString()}`);
      ws.send(JSON.stringify({ error: "Geçersiz JSON mesaj formatı" }));
      return;
    }

    try {
      switch (parsedMessage.type) {
        case "analyzeYoutube":
          if (parsedMessage.youtubeUrl) {
            await handleYouTubeAnalysis(parsedMessage, ws, clientData);
          } else {
            ws.send(JSON.stringify({ error: "YouTube URL eksik" }));
          }
          break;
        case "stopYoutubeAnalysis":
          if (parsedMessage.streamId) {
            handleStopYouTubeAnalysis(parsedMessage, ws, clientData);
          } else {
            ws.send(JSON.stringify({ error: "Stream ID eksik" }));
          }
          break;
        case "getActiveStreams":
          ws.send(JSON.stringify({
            event: "activeStreamsCount",
            count: clientData.activeYouTubeStreams.size,
            clientStreams: Array.from(clientData.activeYouTubeStreams.keys()),
          }));
          break;
        default:
          ws.send(JSON.stringify({ error: "Bilinmeyen komut tipi" }));
      }
    } catch (error) {
      logger.error(`Komut işleme hatası (${parsedMessage.type}): ${error.message}`);
      ws.send(JSON.stringify({ error: `Komut işleme hatası: ${error.message}` }));
    }
  });

  ws.on("close", () => {
    logger.info(`İstemci bağlantısı kesildi: ${clientIP}`);
    cleanup(clientData); // Clean up resources associated with this client
  });

  ws.on("error", (error) => {
    logger.error(`WebSocket client hatası (${clientIP}): ${error.message}`);
    cleanup(clientData); // Clean up resources on error as well
  });
}

/**
 * @brief Handles a request to analyze a YouTube video.
 *
 * Validates the URL, fetches video info, starts an ffmpeg process to extract frames,
 * and processes these frames using `serviceHandlers.processFrame`.
 * Manages the lifecycle of the ffmpeg process and communicates status updates
 * (started, video info, completed, error) back to the client.
 * @async
 * @function handleYouTubeAnalysis
 * @param {Object} parsedMessage - The parsed JSON message from the client.
 *                                 Expected to have `youtubeUrl`.
 * @param {WebSocket} ws - The WebSocket client instance.
 * @param {Object} clientData - Client-specific data, including `activeYouTubeStreams` map.
 */
async function handleYouTubeAnalysis(parsedMessage, ws, clientData) {
  const { youtubeUrl } = parsedMessage;

  try {
    if (!ytdl.validateURL(youtubeUrl)) {
      ws.send(JSON.stringify({ error: "Geçersiz YouTube linki" }));
      return;
    }

    ws.send(JSON.stringify({ event: "analysisStarted", youtubeUrl }));
    logger.info(`YouTube analizi başlatılıyor: ${youtubeUrl}`);

    let info;
    try {
      info = await ytdl.getInfo(youtubeUrl);
      ws.send(JSON.stringify({
        event: "videoInfo",
        youtubeUrl,
        info: {
          title: info.videoDetails.title,
          duration: info.videoDetails.lengthSeconds,
          thumbnail: info.videoDetails.thumbnails[0]?.url,
        },
      }));
    } catch (infoError) {
      logger.error(`Video bilgisi alınamadı (${youtubeUrl}): ${infoError.message}`);
      ws.send(JSON.stringify({ error: `Video bilgisi alınamadı: ${infoError.message}` }));
      return;
    }

    const streamId = `yt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const videoStream = ytdl(youtubeUrl, { quality: config.youtube.quality, filter: "videoonly" });

    const ffmpegProcess = ffmpeg(videoStream)
      .format("image2pipe")
      .outputOptions([
        "-vf", `fps=${config.youtube.frameRate}`,
        "-q:v", "2", // High quality JPEG
      ])
      .on("start", (commandLine) => {
        logger.info(`FFmpeg başlatıldı (${streamId}): ${youtubeUrl}`);
        clientData.activeYouTubeStreams.set(streamId, ffmpegProcess);
        ws.send(JSON.stringify({ event: "streamStarted", youtubeUrl, streamId }));
      })
      .on("end", () => {
        logger.info(`YouTube analizi tamamlandı (${streamId}): ${youtubeUrl}`);
        clientData.activeYouTubeStreams.delete(streamId);
        ws.send(JSON.stringify({ event: "analysisComplete", streamId, youtubeUrl }));
      })
      .on("error", (err) => {
        logger.error(`FFmpeg hatası (${streamId}): ${err.message}`);
        clientData.activeYouTubeStreams.delete(streamId);
        ws.send(JSON.stringify({ error: `Video işleme hatası: ${err.message}`, streamId }));
      })
      .pipe(); // Returns a PassThrough stream

    let frameBufferAccumulator = Buffer.alloc(0);
    ffmpegProcess.on("data", (chunk) => {
      frameBufferAccumulator = Buffer.concat([frameBufferAccumulator, chunk]);
      let jpegStartIdx, jpegEndIdx;
      while (
        (jpegStartIdx = frameBufferAccumulator.indexOf(Buffer.from([0xff, 0xd8]))) !== -1 &&
        (jpegEndIdx = frameBufferAccumulator.indexOf(Buffer.from([0xff, 0xd9]), jpegStartIdx + 2)) !== -1
      ) {
        const completeFrame = frameBufferAccumulator.slice(jpegStartIdx, jpegEndIdx + 2);
        frameBufferAccumulator = frameBufferAccumulator.slice(jpegEndIdx + 2);

        (async () => { // Process frame asynchronously
          try {
            await serviceHandlers.processFrame(completeFrame);
            // Data is sent by periodic timer, no immediate send here to avoid flooding
          } catch (frameProcessingError) {
            logger.error(`Frame işleme hatası (${streamId}): ${frameProcessingError.message}`);
          }
        })();
      }
    });
  } catch (error) {
    logger.error(`YouTube analizi genel hatası (${youtubeUrl}): ${error.message}`);
    ws.send(JSON.stringify({ error: `YouTube analizi başarısız: ${error.message}` }));
  }
}

/**
 * @brief Handles a request to stop an ongoing YouTube video analysis.
 *
 * Kills the corresponding ffmpeg process and removes it from the active streams map.
 * @function handleStopYouTubeAnalysis
 * @param {Object} parsedMessage - The parsed JSON message from the client. Expected to have `streamId`.
 * @param {WebSocket} ws - The WebSocket client instance.
 * @param {Object} clientData - Client-specific data, including `activeYouTubeStreams` map.
 */
function handleStopYouTubeAnalysis(parsedMessage, ws, clientData) {
  const { streamId } = parsedMessage;
  try {
    const ffmpegProcess = clientData.activeYouTubeStreams.get(streamId);
    if (ffmpegProcess) {
      ffmpegProcess.kill("SIGTERM"); // Send SIGTERM to gracefully stop ffmpeg
      clientData.activeYouTubeStreams.delete(streamId);
      ws.send(JSON.stringify({ event: "streamStopped", streamId }));
      logger.info(`YouTube stream durduruldu: ${streamId}`);
    } else {
      ws.send(JSON.stringify({ error: "Durdurulacak stream bulunamadı", streamId }));
    }
  } catch (error) {
    logger.error(`Stream durdurma hatası (${streamId}): ${error.message}`);
    ws.send(JSON.stringify({ error: `Stream durdurma hatası: ${error.message}`, streamId }));
  }
}

/**
 * @brief Cleans up resources associated with a disconnected WebSocket client.
 *
 * Stops the periodic data update timer and terminates any active YouTube stream
 * ffmpeg processes initiated by this client.
 * @function cleanup
 * @param {Object} clientData - The client-specific data object containing `updateTimer`
 *                              and `activeYouTubeStreams`.
 */
function cleanup(clientData) {
  if (clientData.updateTimer) {
    clearInterval(clientData.updateTimer);
    clientData.updateTimer = null;
  }

  if (clientData.activeYouTubeStreams && clientData.activeYouTubeStreams.size > 0) {
    logger.info(`Client kapanırken ${clientData.activeYouTubeStreams.size} aktif YouTube stream temizleniyor.`);
    for (const [streamId, ffmpegProcess] of clientData.activeYouTubeStreams) {
      try {
        ffmpegProcess.kill("SIGTERM");
        logger.info(`Stream durduruldu (client disconnect): ${streamId}`);
      } catch (err) {
        logger.error(`Stream durdurulamadı (client disconnect): ${streamId}, Hata: ${err.message}`);
      }
    }
    clientData.activeYouTubeStreams.clear();
  }
}

/**
 * @brief Sends combined analysis data from the cache to a WebSocket client.
 *
 * Retrieves data using `dataCache.getCombinedData()` and sends it if the client
 * connection is open and there is data to send.
 * @function sendDataToClient
 * @param {WebSocket} ws - The WebSocket client instance.
 */
function sendDataToClient(ws) {
  try {
    if (ws.readyState === WebSocket.OPEN) {
      const combinedData = dataCache.getCombinedData();
      // Only send if there are speakers to avoid empty updates unless specifically designed otherwise
      if (combinedData && combinedData.speakers && combinedData.speakers.length > 0) {
        ws.send(JSON.stringify({
          type: "analysisData",
          data: combinedData,
          timestamp: Date.now(),
        }));
      } else if (combinedData && combinedData.speakers && combinedData.speakers.length === 0) {
        // Optionally send an empty speakers array if client expects periodic updates even if empty
        // ws.send(JSON.stringify({ type: "analysisData", data: { speakers: [] }, timestamp: Date.now() }));
      }
    }
  } catch (err) {
    logger.error(`WebSocket veri gönderme hatası: ${err.message}`);
  }
}

/**
 * @brief Handles errors that occur during frame processing or other operations.
 *
 * Logs the error and attempts to send an error message back to the WebSocket client
 * if the connection is still open.
 * @function handleError
 * @param {Error} error - The error object.
 * @param {WebSocket} ws - The WebSocket client instance.
 */
function handleError(error, ws) {
  logger.error(`Frame işleme hatası: ${error.message}`);
  if (error.stack) logger.error(error.stack);
  if (error.details) logger.error(`HATA DETAYI: ${error.details}`);
  if (error.code) logger.error(`HATA KODU: ${error.code}`);

  try {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: "error",
        error: `Frame işleme başarısız: ${error.message}`,
        timestamp: Date.now(),
      }));
    }
  } catch (sendError) {
    logger.error(`Hata mesajı gönderilemedi: ${sendError.message}`);
  }
}

module.exports = {
  createWebSocketServer,
};
