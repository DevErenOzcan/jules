/**
 * @file youtubeStream.js
 * @module YouTubeStreamManager
 * @brief Manages the streaming and processing of YouTube videos for analysis.
 *
 * This module defines the YouTubeStreamManager class, which is responsible for
 * fetching YouTube video streams using `ytdl-core`, extracting frames using `ffmpeg`,
 * and then passing these frames to a provided processor function (presumably for
 * further analysis by gRPC services). It handles concurrent stream limits,
 * stream lifecycle management (start, stop, cleanup), and error handling.
 */

const ytdl = require("@distube/ytdl-core"); // Use @distube/ytdl-core for better maintenance
const ffmpeg = require("fluent-ffmpeg");
const ffmpegInstaller = require("@ffmpeg-installer/ffmpeg");
const config = require("../config");
const logger = require("../utils/logger");

ffmpeg.setFfmpegPath(ffmpegInstaller.path);

/**
 * @class YouTubeStreamManager
 * @brief Manages fetching, processing, and lifecycle of YouTube video streams.
 */
class YouTubeStreamManager {
  /**
   * @constructor
   * @brief Initializes the YouTubeStreamManager.
   * Sets up a map for active streams and loads concurrent stream limit from config.
   */
  constructor() {
    this.activeStreams = new Map(); // Stores active ffmpeg processes, keyed by streamId
    this.maxConcurrentStreams = config.youtube.maxConcurrentStreams;
  }

  /**
   * @brief Starts the analysis of a YouTube video.
   *
   * Validates the URL, checks concurrent stream limits, generates a unique stream ID,
   * and initiates the video stream creation and processing.
   * @async
   * @param {string} youtubeUrl - The URL of the YouTube video to analyze.
   * @param {WebSocket} ws - The WebSocket client instance to send status updates to.
   * @param {function} frameProcessor - An async function that takes a frame buffer
   *                                    and processes it (e.g., sends to gRPC services).
   * @returns {Promise<Object>} A promise that resolves with an object containing stream data
   *                            (streamId, ffmpeg command, cleanup function, isActive check).
   * @throws {Error} If URL is invalid, stream limit is reached, video is already being processed,
   *                 or an error occurs during stream creation.
   */
  async startYouTubeAnalysis(youtubeUrl, ws, frameProcessor) {
    if (!ytdl.validateURL(youtubeUrl)) {
      throw new Error("Geçersiz YouTube linki");
    }

    if (this.activeStreams.size >= this.maxConcurrentStreams) {
      throw new Error(
        `Maksimum ${this.maxConcurrentStreams} eşzamanlı stream destekleniyor.`
      );
    }

    const streamId = this.generateStreamId(youtubeUrl);
    if (this.activeStreams.has(streamId)) {
      // To prevent re-processing the same video if identified by a consistent streamId generation.
      // However, generateStreamId currently includes Date.now(), making IDs unique per call.
      // If the intent is to prevent *identical* URLs at the same time regardless of call time,
      // a different check or streamId generation (e.g., based only on video ID) would be needed.
      logger.warn(`Bu video (${youtubeUrl}) için zaten bir analiz mevcut olabilir (ID: ${streamId}). Yeni stream başlatılıyor.`);
      // For now, we allow multiple analyses of the same URL if requested at different times due to unique streamId.
    }

    logger.info(`YouTube analizi başlatılıyor: ${youtubeUrl} (Stream ID: ${streamId})`);

    try {
      const streamData = await this.createVideoStream(
        youtubeUrl,
        streamId, // Pass streamId to createVideoStream
        ws,
        frameProcessor
      );
      this.activeStreams.set(streamId, streamData);

      // Augment streamData with a cleanup specific to this manager instance
      const originalCleanup = streamData.cleanup;
      streamData.cleanup = () => {
        originalCleanup(); // Call the cleanup from createVideoStream
        this.activeStreams.delete(streamId);
        logger.info(`YouTube stream manager'dan temizlendi: ${streamId}`);
      };

      return streamData;
    } catch (error) {
      logger.error(`YouTube stream oluşturma hatası (${youtubeUrl}): ${error.message}`);
      throw error; // Re-throw to be handled by the caller
    }
  }

  /**
   * @brief Creates and manages an ffmpeg process to extract frames from a YouTube stream.
   * @async
   * @param {string} youtubeUrl - The URL of the YouTube video.
   * @param {string} streamId - The unique ID for this stream instance.
   * @param {WebSocket} ws - The WebSocket client to send updates to.
   * @param {function} frameProcessor - Async function to process extracted frames.
   * @returns {Promise<Object>} A promise resolving to an object with stream details
   *                            (streamId, ffmpeg command, cleanup function, isActive check).
   * @throws {Error} If ffmpeg processing fails or stream times out.
   */
  async createVideoStream(youtubeUrl, streamId, ws, frameProcessor) {
    return new Promise((resolve, reject) => {
      const videoStream = ytdl(youtubeUrl, {
        quality: config.youtube.quality,
        filter: "videoonly",
      });

      videoStream.on('error', (err) => {
        logger.error(`ytdl stream hatası (${youtubeUrl}): ${err.message}`);
        reject(new Error(`ytdl stream hatası: ${err.message}`));
      });

      const ffmpegCommand = ffmpeg(videoStream)
        .format("image2pipe") // Output frames as a pipe
        .fps(config.youtube.frameRate)
        .outputOptions([
            "-vcodec", "mjpeg", // Output MJPEG frames
            "-f", "image2pipe",
            "-vf", `scale=${config.youtube.videoWidth || 640}:${config.youtube.videoHeight || 480}` // Configurable scale
        ]);
        // .outputOptions(["-vcodec mjpeg", "-f image2pipe", "-vf scale=640:480"]); // Original

      let bufferAccumulator = Buffer.alloc(0);
      let isActive = true;
      let frameCount = 0;
      let commandInstance = null; // To store the command instance for killing

      const streamTimeout = setTimeout(() => {
        if (isActive) {
          logger.warn(`YouTube stream timeout (${streamId}): ${youtubeUrl}`);
          cleanupLocal();
          reject(new Error("YouTube stream timeout"));
        }
      }, config.youtube.timeout);

      const cleanupLocal = () => {
        if (!isActive) return; // Already cleaned up
        isActive = false;
        clearTimeout(streamTimeout);
        videoStream.destroy(); // Ensure ytdl stream is destroyed
        if (commandInstance) {
          try {
            commandInstance.kill("SIGKILL"); // Force kill ffmpeg
            logger.debug(`FFmpeg işlemi sonlandırıldı (${streamId})`);
          } catch (err) {
            logger.warn(`FFmpeg temizleme hatası (${streamId}): ${err.message}`);
          }
        }
      };

      commandInstance = ffmpegCommand // Store the command instance
        .on("start", (commandLine) => {
          logger.info(`FFmpeg başlatıldı (${streamId}): ${commandLine}`);
          ws.send(JSON.stringify({ event: "analysisStarted", youtubeUrl, streamId, message: "Video analizi başlatıldı" }));
        })
        .on("end", () => {
          logger.info(`FFmpeg normal şekilde tamamlandı (${streamId})`);
          cleanupLocal();
          ws.send(JSON.stringify({ event: "analysisComplete", youtubeUrl, streamId, framesProcessed: frameCount, message: "Video analizi tamamlandı" }));
        })
        .on("error", (err, stdout, stderr) => {
          // Only reject if stream is still considered active, to avoid multiple rejections
          if(isActive) {
            logger.error(`FFmpeg hatası (${streamId}): ${err.message}. Stdout: ${stdout}. Stderr: ${stderr}`);
            cleanupLocal();
            reject(err); // Reject the main promise from createVideoStream
          } else {
            logger.warn(`FFmpeg hatası (stream zaten aktif değil) (${streamId}): ${err.message}`);
          }
        })
        .pipe(); // Returns a PassThrough stream for the output

      // Handle data from ffmpeg's output stream
      ffmpegCommand.on("data", async (chunk) => {
        if (!isActive) return;
        bufferAccumulator = Buffer.concat([bufferAccumulator, chunk]);
        let jpegStartIdx, jpegEndIdx;

        while (
          isActive && // Check isActive in loop condition
          (jpegStartIdx = bufferAccumulator.indexOf(Buffer.from([0xff, 0xd8]))) !== -1 &&
          (jpegEndIdx = bufferAccumulator.indexOf(Buffer.from([0xff, 0xd9]), jpegStartIdx + 2)) !== -1
        ) {
          const completeFrame = bufferAccumulator.slice(jpegStartIdx, jpegEndIdx + 2);
          bufferAccumulator = bufferAccumulator.slice(jpegEndIdx + 2);
          frameCount++;

          try {
            await frameProcessor(completeFrame); // Process the extracted frame
            if (frameCount % 10 === 0) { // Send progress update every 10 frames
              ws.send(JSON.stringify({ event: "analysisProgress", youtubeUrl, streamId, framesProcessed: frameCount }));
            }
          } catch (err) {
            logger.error(`Frame işleme hatası (${streamId}, frame ${frameCount}): ${err.message}`);
            // Decide if this error should stop the stream
          }
        }
      });

      // Resolve the promise with stream data
      resolve({
        streamId,
        command: ffmpegCommand, // The fluent-ffmpeg command object
        cleanup: cleanupLocal,    // Function to stop this specific stream
        isActive: () => isActive, // Function to check if stream is still active
      });
    });
  }

  /**
   * @brief Stops a specific YouTube stream by its ID.
   * @param {string} streamId - The ID of the stream to stop.
   * @returns {boolean} True if the stream was found and cleanup was initiated, false otherwise.
   */
  stopStream(streamId) {
    const streamData = this.activeStreams.get(streamId);
    if (streamData && typeof streamData.cleanup === 'function') {
      streamData.cleanup(); // This will also remove it from activeStreams via the augmented cleanup
      return true;
    }
    logger.warn(`Durdurulacak stream bulunamadı: ${streamId}`);
    return false;
  }

  /**
   * @brief Stops all active YouTube streams.
   */
  stopAllStreams() {
    logger.info(`${this.activeStreams.size} aktif YouTube stream durduruluyor.`);
    for (const streamData of this.activeStreams.values()) {
      if (typeof streamData.cleanup === 'function') {
        streamData.cleanup();
      }
    }
    // The augmented cleanup in startYouTubeAnalysis should handle removal from the map.
    // If not, or for safety: this.activeStreams.clear();
  }

  /**
   * @brief Gets the current count of active YouTube streams.
   * @returns {number} The number of active streams.
   */
  getActiveStreamsCount() {
    return this.activeStreams.size;
  }

  /**
   * @brief Generates a unique stream ID for a YouTube URL.
   * Incorporates the YouTube video ID and the current timestamp.
   * @param {string} youtubeUrl - The URL of the YouTube video.
   * @returns {string} A unique stream identifier.
   * @throws {Error} if ytdl.getVideoID fails (e.g. invalid URL).
   */
  generateStreamId(youtubeUrl) {
    const videoId = ytdl.getVideoID(youtubeUrl); // Can throw if URL is invalid
    return `youtube_${videoId}_${Date.now()}`;
  }

  /**
   * @brief Fetches basic information about a YouTube video.
   * @async
   * @param {string} youtubeUrl - The URL of the YouTube video.
   * @returns {Promise<Object|null>} A promise that resolves with an object containing
   *                                 video title, duration, author, and view count,
   *                                 or null if fetching info fails.
   */
  async getVideoInfo(youtubeUrl) {
    try {
      const info = await ytdl.getInfo(youtubeUrl);
      return {
        title: info.videoDetails.title,
        duration: info.videoDetails.lengthSeconds,
        author: info.videoDetails.author.name, // Corrected path
        viewCount: info.videoDetails.viewCount,
      };
    } catch (error) {
      logger.error(`Video bilgisi alınamadı (${youtubeUrl}): ${error.message}`);
      return null;
    }
  }
}

/**
 * Exports a singleton instance of the YouTubeStreamManager.
 * @type {YouTubeStreamManager}
 */
module.exports = new YouTubeStreamManager();
