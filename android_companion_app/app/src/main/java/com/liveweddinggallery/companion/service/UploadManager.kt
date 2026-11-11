package com.liveweddinggallery.companion.service

import android.content.Context
import com.liveweddinggallery.companion.db.UploadQueueDatabase
import com.liveweddinggallery.companion.util.CompanionLogger
import com.liveweddinggallery.companion.util.FileIntegrityValidator
import com.liveweddinggallery.companion.util.ImageOptimizer
import com.liveweddinggallery.companion.util.StorageMonitor
import kotlinx.coroutines.*
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withPermit
import java.io.*
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID

object UploadManager {
    private const val PREFS_NAME = "WeddingCompanion"
    private const val KEY_API_URL = "django_api_url"
    private const val KEY_CURRENT_FOLDER = "current_folder"
    private const val KEY_DEVICE_ID = "device_id"

    const val DEFAULT_API_URL = "https://live-wedding-gallery.onrender.com/api/weddings/sandeep-prathyusha/photographer/phone"
    const val DEFAULT_DEVICE_ID = "phone_01"
    const val DEFAULT_FOLDER = "Wedding Day"

    private var job: Job? = null
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val uploadSemaphore = Semaphore(2) // Bounded concurrency: max 2 simultaneous uploads

    fun start(context: Context) {
        if (job != null && job?.isActive == true) return

        val appContext = context.applicationContext
        val db = UploadQueueDatabase.getInstance(appContext)

        // Reset any transfers that were interrupted by an app crash/kill
        val resetCount = db.resetStuckUploadingToPending()
        if (resetCount > 0) {
            CompanionLogger.i(
                event = "QUEUE_RECOVERY",
                status = "RECOVERED",
                details = "Reset $resetCount stuck uploads back to PENDING after restart"
            )
        }

        job = scope.launch {
            CompanionLogger.i(
                event = "SERVICE_START",
                status = "RUNNING",
                details = "UploadManager background forwarding engine active"
            )

            var lastCleanupTime = 0L

            while (isActive) {
                try {
                    // 1. Process files in incoming directory
                    scanAndEnqueueIncomingFiles(appContext)

                    // 2. Dispatch pending uploads with bounded concurrency
                    processPendingQueue(appContext)

                    // 3. Periodic safe cleanup (every 60 seconds)
                    val now = System.currentTimeMillis()
                    if (now - lastCleanupTime > 60 * 1000L) {
                        lastCleanupTime = now
                        StorageMonitor.performSafeCleanup(appContext, forceDueToLowStorage = false)
                    }

                } catch (e: CancellationException) {
                    break
                } catch (e: Exception) {
                    CompanionLogger.e(
                        event = "FORWARDER_LOOP_ERROR",
                        status = "ERROR",
                        details = "Error in background processing loop: ${e.message}",
                        throwable = e
                    )
                }

                delay(1500) // Poll loop every 1.5 seconds
            }
        }
    }

    fun stop() {
        job?.cancel()
        job = null
        CompanionLogger.i(
            event = "SERVICE_STOP",
            status = "STOPPED",
            details = "UploadManager background forwarding engine stopped"
        )
    }

    /**
     * Called directly by FtpTransferListener when Apache FtpServer finishes receiving a file.
     */
    fun onFileReceived(file: File, context: Context) {
        scope.launch {
            processIncomingFile(file, context.applicationContext)
        }
    }

    private fun getFtpIncomingDir(context: Context): File {
        val dir = File(context.filesDir, "ftp")
        if (!dir.exists()) dir.mkdirs()
        return dir
    }

    private fun getReadyDir(context: Context): File {
        val dir = File(context.filesDir, "ready_photos")
        if (!dir.exists()) dir.mkdirs()
        return dir
    }

    private val activeFtpPaths = java.util.concurrent.ConcurrentHashMap<String, String>()
    private val sessionActivePaths = java.util.concurrent.ConcurrentHashMap<String, MutableSet<String>>()
    private val observedIncomingFiles = java.util.concurrent.ConcurrentHashMap<String, Pair<Long, Long>>()
    private val recentlyQueuedFtpFiles = java.util.concurrent.ConcurrentHashMap<String, Pair<Long, Long>>()
    private val pathEnqueueLocks = java.util.concurrent.ConcurrentHashMap<String, Any>()

    fun markFtpTransferStarted(sessionId: String?, file: File) {
        val path = try { file.canonicalPath } catch (_: Exception) { file.absolutePath }
        val sid = sessionId ?: "default"
        activeFtpPaths[path] = sid
        sessionActivePaths.computeIfAbsent(sid) {
            java.util.Collections.newSetFromMap(java.util.concurrent.ConcurrentHashMap())
        }.add(path)
        recentlyQueuedFtpFiles.remove(path)
    }

    fun markFtpTransferFinished(sessionId: String?, file: File) {
        val path = try { file.canonicalPath } catch (_: Exception) { file.absolutePath }
        activeFtpPaths.remove(path)
        if (sessionId != null) {
            sessionActivePaths[sessionId]?.remove(path)
        }
        observedIncomingFiles.remove(path)
    }

    fun clearActiveSessionTransfers(sessionId: String?) {
        val sid = sessionId ?: return
        val paths = sessionActivePaths.remove(sid) ?: return
        for (p in paths) {
            activeFtpPaths.remove(p, sid)
        }
    }

    internal fun isFtpTransferActive(file: File): Boolean {
        val path = try { file.canonicalPath } catch (_: Exception) { file.absolutePath }
        return activeFtpPaths.containsKey(path)
    }

    internal fun isFileSettledForPoll(file: File): Boolean {
        val path = try { file.canonicalPath } catch (_: Exception) { file.absolutePath }
        if (activeFtpPaths.containsKey(path)) return false
        val len = file.length()
        val mtime = file.lastModified()
        val now = System.currentTimeMillis()
        if (len <= 0L || (now - mtime) < 3500L) {
            observedIncomingFiles[path] = Pair(len, mtime)
            return false
        }
        val prev = observedIncomingFiles[path]
        observedIncomingFiles[path] = Pair(len, mtime)
        // Require at least two consecutive unchanged poll observations (>= 3.5s quiet after last write)
        if (prev == null || prev.first != len || prev.second != mtime) {
            return false
        }
        return true
    }

    private fun scanAndEnqueueIncomingFiles(context: Context) {
        val ftpDir = getFtpIncomingDir(context)
        val validExtensions = setOf("jpg", "jpeg", "png", "webp")

        val files = ftpDir.walkTopDown().filter { f ->
            f.isFile && validExtensions.contains(f.extension.lowercase()) && !f.name.endsWith(".part")
        }.filter { f ->
            isFileSettledForPoll(f)
        }.toList()

        val now = System.currentTimeMillis()
        for (file in files) {
            val path = try { file.canonicalPath } catch (_: Exception) { file.absolutePath }
            val sig = Pair(file.length(), file.lastModified())
            val queuedSig = recentlyQueuedFtpFiles[path]
            val ageMs = now - file.lastModified()
            if (queuedSig != null && queuedSig == sig) {
                if (ageMs > 30000L) {
                    file.delete()
                    recentlyQueuedFtpFiles.remove(path)
                    observedIncomingFiles.remove(path)
                }
                continue
            }
            processIncomingFile(file, context)
        }
    }

    private fun processIncomingFile(file: File, context: Context) {
        val canonicalKey = try { file.canonicalPath } catch (_: Exception) { file.absolutePath }
        val fileLock = pathEnqueueLocks.computeIfAbsent(canonicalKey) { Any() }
        synchronized(fileLock) {
            if (!file.exists() || file.length() == 0L || isFtpTransferActive(file)) return

            // Check storage before admitting file
            val storage = StorageMonitor.getStorageStatus(context)
            if (storage.isCritical) {
                CompanionLogger.e(
                    event = "STORAGE_CRITICAL",
                    filename = file.name,
                    details = "Storage critical (${storage.availableMb} MB free). Forcing emergency purge."
                )
                StorageMonitor.performSafeCleanup(context, forceDueToLowStorage = true)
            }

            // Validate complete container and boundaries
            val validation = FileIntegrityValidator.validateFile(file)
            val db = UploadQueueDatabase.getInstance(context)

            when (validation) {
                is FileIntegrityValidator.ValidationResult.Valid -> {
                    val ageMs = System.currentTimeMillis() - file.lastModified()
                    val sig = Pair(file.length(), file.lastModified())
                    // Deduplication check
                    if (db.isDuplicateChecksum(validation.checksumSha256)) {
                        recentlyQueuedFtpFiles[canonicalKey] = sig
                        CompanionLogger.i(
                            event = "DEDUPLICATION",
                            filename = file.name,
                            status = "SKIPPED",
                            details = "Identical photo already in queue or uploaded (SHA: ${validation.checksumSha256.take(8)})"
                        )
                        if (ageMs > 30000) {
                            file.delete()
                            recentlyQueuedFtpFiles.remove(canonicalKey)
                            observedIncomingFiles.remove(canonicalKey)
                        }
                        return
                    }

                    val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                    val currentFolder = prefs.getString(KEY_CURRENT_FOLDER, DEFAULT_FOLDER) ?: DEFAULT_FOLDER
                    val uploadId = UUID.randomUUID().toString()

                    // Copy to persistent ready directory with collision-free unique name
                    // Leaving original in ftp/ briefly so FTP clients can verify SIZE/MDTM cleanly
                    val readyDir = getReadyDir(context)
                    val uniqueSafeName = "${System.currentTimeMillis()}_${uploadId.take(8)}_${file.name}"
                    val targetFile = File(readyDir, uniqueSafeName)

                    try {
                        file.copyTo(targetFile, overwrite = true)
                    } catch (e: Exception) {
                        CompanionLogger.e("FILE_COPY_FAIL", uploadId = uploadId, filename = file.name, details = e.message ?: "", throwable = e)
                        return
                    }
                    val storedPath = targetFile.absolutePath

                    val enqueued = db.enqueue(
                        uploadId = uploadId,
                        originalName = file.name,
                        filePath = storedPath,
                        fileSize = targetFile.length(),
                        checksumSha256 = validation.checksumSha256,
                        folder = currentFolder
                    )

                    if (enqueued) {
                        recentlyQueuedFtpFiles[canonicalKey] = sig
                        CompanionLogger.i(
                            event = "FILE_ENQUEUED",
                            uploadId = uploadId,
                            filename = file.name,
                            status = "QUEUED",
                            details = "Dimensions: ${validation.width}x${validation.height}, Size: ${targetFile.length() / 1024} KB, Folder: $currentFolder"
                        )
                    } else {
                        targetFile.delete()
                    }
                }
                is FileIntegrityValidator.ValidationResult.Invalid -> {
                    // Only quarantine files that have been completely idle for >20s and are not in an active FTP session.
                    val age = System.currentTimeMillis() - file.lastModified()
                    if (age > 20000 && !isFtpTransferActive(file)) {
                        CompanionLogger.w(
                            event = "CORRUPT_QUARANTINE",
                            filename = file.name,
                            status = "CORRUPTED",
                            details = "File failed integrity after 20s: ${validation.reason}"
                        )
                        val corruptDir = File(context.filesDir, "corrupted_photos")
                        if (!corruptDir.exists()) corruptDir.mkdirs()
                        file.renameTo(File(corruptDir, "${System.currentTimeMillis()}_${file.name}"))
                        observedIncomingFiles.remove(canonicalKey)
                    }
                }
            }
        }
    }

    private suspend fun processPendingQueue(context: Context) = coroutineScope {
        val db = UploadQueueDatabase.getInstance(context)
        val pendingItems = db.getPendingBatch(limit = 10)

        if (pendingItems.isEmpty()) return@coroutineScope

        for (item in pendingItems) {
            launch {
                uploadSemaphore.withPermit {
                    forwardItemToDjango(context, item)
                }
            }
        }
    }

    private fun forwardItemToDjango(context: Context, item: UploadQueueDatabase.QueueItem) {
        val db = UploadQueueDatabase.getInstance(context)
        val file = File(item.filePath)

        if (!file.exists()) {
            db.markFailed(item.uploadId, "File missing on disk: ${item.filePath}", System.currentTimeMillis() + 60000)
            CompanionLogger.e(
                event = "FILE_NOT_FOUND",
                uploadId = item.uploadId,
                filename = item.originalName,
                details = "Target file not found at ${item.filePath}"
            )
            return
        }

        // Optimize photo on-device (Quad-HD 2560px, ~600KB) to save 96% bandwidth and prevent cloud OOM
        val uploadFile = ImageOptimizer.getOptimizedFile(file, item.uploadId, context)
        val isTempOptimized = uploadFile.absolutePath != file.absolutePath
        val uploadChecksum = if (isTempOptimized) FileIntegrityValidator.calculateSha256(uploadFile) else item.checksumSha256

        db.markUploading(item.uploadId)
        CompanionLogger.i(
            event = "HTTP_FORWARD_START",
            uploadId = item.uploadId,
            filename = item.originalName,
            status = "UPLOADING",
            details = "Attempt ${item.attempts + 1}/10, Sending ${uploadFile.length() / 1024} KB to backend"
        )

        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val baseUrl = prefs.getString(KEY_API_URL, DEFAULT_API_URL) ?: DEFAULT_API_URL
        val deviceId = prefs.getString(KEY_DEVICE_ID, DEFAULT_DEVICE_ID) ?: DEFAULT_DEVICE_ID
        val authToken = prefs.getString("photographer_token", null)
        val uploadUrl = if (baseUrl.endsWith("/")) "${baseUrl}upload/" else "$baseUrl/upload/"

        val boundary = "==Boundary-${UUID.randomUUID()}=="
        val lineEnd = "\r\n"
        val twoHyphens = "--"

        val headerBytes = buildString {
            append(twoHyphens).append(boundary).append(lineEnd)
            append("Content-Disposition: form-data; name=\"device_id\"").append(lineEnd).append(lineEnd)
            append(deviceId).append(lineEnd)

            append(twoHyphens).append(boundary).append(lineEnd)
            append("Content-Disposition: form-data; name=\"folder\"").append(lineEnd).append(lineEnd)
            append(item.folder).append(lineEnd)

            append(twoHyphens).append(boundary).append(lineEnd)
            append("Content-Disposition: form-data; name=\"upload_id\"").append(lineEnd).append(lineEnd)
            append(item.uploadId).append(lineEnd)

            append(twoHyphens).append(boundary).append(lineEnd)
            append("Content-Disposition: form-data; name=\"checksum\"").append(lineEnd).append(lineEnd)
            append(uploadChecksum).append(lineEnd)

            append(twoHyphens).append(boundary).append(lineEnd)
            append("Content-Disposition: form-data; name=\"photo\"; filename=\"").append(item.originalName).append("\"").append(lineEnd)
            append("Content-Type: image/jpeg").append(lineEnd).append(lineEnd)
        }.toByteArray(Charsets.UTF_8)
        val footerBytes = (lineEnd + twoHyphens + boundary + twoHyphens + lineEnd).toByteArray(Charsets.UTF_8)
        val totalContentLength = headerBytes.size.toLong() + uploadFile.length() + footerBytes.size.toLong()

        var connection: HttpURLConnection? = null
        try {
            val url = URL(uploadUrl)
            connection = (url.openConnection() as HttpURLConnection).apply {
                connectTimeout = 15000 // 15 seconds
                readTimeout = 60000    // 60 seconds (allow backend to queue large RAW/JPEG)
                doInput = true
                doOutput = true
                useCaches = false
                requestMethod = "POST"
                setRequestProperty("Connection", "Keep-Alive")
                setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
                setRequestProperty("X-Device-Id", deviceId)
                setRequestProperty("X-Correlation-ID", item.uploadId)
                setRequestProperty("X-Upload-ID", item.uploadId)
                if (!authToken.isNullOrEmpty()) {
                    setRequestProperty("Authorization", "Token $authToken")
                    setRequestProperty("X-Photographer-Token", authToken)
                }
                setFixedLengthStreamingMode(totalContentLength)
            }

            DataOutputStream(connection.outputStream).use { outputStream ->
                outputStream.write(headerBytes)

                FileInputStream(uploadFile).use { fis ->
                    val buffer = ByteArray(64 * 1024)
                    var bytesRead = fis.read(buffer)
                    while (bytesRead != -1) {
                        outputStream.write(buffer, 0, bytesRead)
                        bytesRead = fis.read(buffer)
                    }
                }

                outputStream.write(footerBytes)
                outputStream.flush()
            }

            val responseCode = connection.responseCode
            if (responseCode in 200..299) {
                db.markForwarded(item.uploadId)
                // Automatically delete local file upon verified upload to keep tablet storage permanently clean
                try {
                    if (file.exists()) {
                        file.delete()
                    }
                    db.markPurged(item.uploadId)
                } catch (_: Exception) {}

                CompanionLogger.i(
                    event = "HTTP_FORWARD_SUCCESS",
                    uploadId = item.uploadId,
                    filename = item.originalName,
                    status = "FORWARDED",
                    details = "HTTP $responseCode: Photo safely forwarded & local file auto-purged"
                )
            } else {
                val errorStreamText = connection.errorStream?.bufferedReader()?.use { it.readText() } ?: "No response body"
                val errorMsg = "HTTP $responseCode: $errorStreamText"
                val retryAfterSec = connection.getHeaderField("Retry-After")?.toLongOrNull()
                handleUploadFailure(db, item, errorMsg, retryAfterSeconds = retryAfterSec)
            }

        } catch (e: Exception) {
            val errorMsg = "Network exception: ${e.javaClass.simpleName}: ${e.message}"
            handleUploadFailure(db, item, errorMsg, e)
        } finally {
            connection?.disconnect()
            if (isTempOptimized && uploadFile.exists()) {
                uploadFile.delete()
            }
        }
    }

    private fun handleUploadFailure(
        db: UploadQueueDatabase,
        item: UploadQueueDatabase.QueueItem,
        errorMsg: String,
        throwable: Throwable? = null,
        retryAfterSeconds: Long? = null
    ) {
        val attempts = item.attempts + 1
        // Exponential backoff: 2s, 4s, 8s, 16s, 32s, 60s (honoring Retry-After if server throttles)
        val defaultDelayMs = Math.min(2000L * (1L shl Math.min(attempts, 6)), 60000L)
        val backoffDelayMs = if (retryAfterSeconds != null && retryAfterSeconds > 0L) {
            Math.max(defaultDelayMs, Math.min(retryAfterSeconds * 1000L, 120000L))
        } else {
            defaultDelayMs
        }
        val nextRetryAt = System.currentTimeMillis() + backoffDelayMs

        db.markFailed(item.uploadId, errorMsg, nextRetryAt)
        CompanionLogger.e(
            event = "HTTP_FORWARD_FAILURE",
            uploadId = item.uploadId,
            filename = item.originalName,
            status = "RETRY_SCHEDULED",
            details = "Attempt $attempts/10 failed. Next retry in ${backoffDelayMs / 1000}s. Error: $errorMsg",
            throwable = throwable
        )
    }
}
