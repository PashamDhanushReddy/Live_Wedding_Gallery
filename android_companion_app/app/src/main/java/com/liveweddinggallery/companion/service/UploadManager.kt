package com.liveweddinggallery.companion.service

import android.content.Context
import com.liveweddinggallery.companion.db.UploadQueueDatabase
import com.liveweddinggallery.companion.util.CompanionLogger
import com.liveweddinggallery.companion.util.FileIntegrityValidator
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

                    // 3. Periodic safe cleanup (every 10 minutes)
                    val now = System.currentTimeMillis()
                    if (now - lastCleanupTime > 10 * 60 * 1000L) {
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

    private fun scanAndEnqueueIncomingFiles(context: Context) {
        val ftpDir = getFtpIncomingDir(context)
        val validExtensions = setOf("jpg", "jpeg", "png", "webp")
        val db = UploadQueueDatabase.getInstance(context)

        val files = ftpDir.listFiles()?.filter { f ->
            f.isFile && validExtensions.contains(f.extension.lowercase()) && !f.name.endsWith(".part")
        } ?: return

        val now = System.currentTimeMillis()
        for (file in files) {
            val ageMs = now - file.lastModified()
            val validation = FileIntegrityValidator.validateFile(file)
            if (validation is FileIntegrityValidator.ValidationResult.Valid && db.isDuplicateChecksum(validation.checksumSha256)) {
                // Windows File Explorer grace period: delete from ftp folder only after 30 seconds
                if (ageMs > 30000) {
                    file.delete()
                }
                continue
            }
            processIncomingFile(file, context)
        }
    }

    private fun processIncomingFile(file: File, context: Context) {
        if (!file.exists() || file.length() == 0L) return

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
                // Deduplication check
                if (db.isDuplicateChecksum(validation.checksumSha256)) {
                    CompanionLogger.i(
                        event = "DEDUPLICATION",
                        filename = file.name,
                        status = "SKIPPED",
                        details = "Identical photo already in queue or uploaded (SHA: ${validation.checksumSha256.take(8)})"
                    )
                    if (ageMs > 30000) {
                        file.delete()
                    }
                    return
                }

                val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                val currentFolder = prefs.getString(KEY_CURRENT_FOLDER, DEFAULT_FOLDER) ?: DEFAULT_FOLDER
                val uploadId = UUID.randomUUID().toString()

                // Copy to persistent ready directory with collision-free unique name
                // Leaving original in ftp/ so Windows File Explorer can verify SIZE/MDTM without 550 errors
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
                    CompanionLogger.i(
                        event = "FILE_ENQUEUED",
                        uploadId = uploadId,
                        filename = file.name,
                        status = "QUEUED",
                        details = "Dimensions: ${validation.width}x${validation.height}, Size: ${targetFile.length() / 1024} KB, Folder: $currentFolder"
                    )
                }
            }
            is FileIntegrityValidator.ValidationResult.Invalid -> {
                // If the file is simply still being written, let the next loop handle it.
                // But if it's genuinely corrupted and hasn't changed for over 10 seconds, quarantine it.
                val age = System.currentTimeMillis() - file.lastModified()
                if (age > 15000) {
                    CompanionLogger.w(
                        event = "CORRUPT_QUARANTINE",
                        filename = file.name,
                        status = "CORRUPTED",
                        details = "File failed integrity after 15s: ${validation.reason}"
                    )
                    val corruptDir = File(context.filesDir, "corrupted_photos")
                    if (!corruptDir.exists()) corruptDir.mkdirs()
                    file.renameTo(File(corruptDir, "${System.currentTimeMillis()}_${file.name}"))
                }
            }
        }
    }

    private suspend fun processPendingQueue(context: Context) = coroutineScope {
        val db = UploadQueueDatabase.getInstance(context)
        val pendingItems = db.getPendingBatch(limit = 6)

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

        db.markUploading(item.uploadId)
        CompanionLogger.i(
            event = "HTTP_FORWARD_START",
            uploadId = item.uploadId,
            filename = item.originalName,
            status = "UPLOADING",
            details = "Attempt ${item.attempts + 1}/5, Streaming ${file.length() / 1024} KB to backend"
        )

        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val baseUrl = prefs.getString(KEY_API_URL, DEFAULT_API_URL) ?: DEFAULT_API_URL
        val deviceId = prefs.getString(KEY_DEVICE_ID, DEFAULT_DEVICE_ID) ?: DEFAULT_DEVICE_ID
        val authToken = prefs.getString("photographer_token", null)
        val uploadUrl = if (baseUrl.endsWith("/")) "${baseUrl}upload/" else "$baseUrl/upload/"

        val boundary = "==Boundary-${UUID.randomUUID()}=="
        val lineEnd = "\r\n"
        val twoHyphens = "--"

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
                // Disable internal HTTP chunking/buffering in Android memory for large streams
                setChunkedStreamingMode(64 * 1024)
            }

            DataOutputStream(connection.outputStream).use { outputStream ->
                // 1. device_id
                outputStream.writeBytes(twoHyphens + boundary + lineEnd)
                outputStream.writeBytes("Content-Disposition: form-data; name=\"device_id\"$lineEnd$lineEnd")
                outputStream.writeBytes("$deviceId$lineEnd")

                // 2. folder
                outputStream.writeBytes(twoHyphens + boundary + lineEnd)
                outputStream.writeBytes("Content-Disposition: form-data; name=\"folder\"$lineEnd$lineEnd")
                outputStream.writeBytes("${item.folder}$lineEnd")

                // 3. upload_id
                outputStream.writeBytes(twoHyphens + boundary + lineEnd)
                outputStream.writeBytes("Content-Disposition: form-data; name=\"upload_id\"$lineEnd$lineEnd")
                outputStream.writeBytes("${item.uploadId}$lineEnd")

                // 4. checksum
                outputStream.writeBytes(twoHyphens + boundary + lineEnd)
                outputStream.writeBytes("Content-Disposition: form-data; name=\"checksum\"$lineEnd$lineEnd")
                outputStream.writeBytes("${item.checksumSha256}$lineEnd")

                // 5. photo file (STREAMED DIRECTLY FROM DISK - Zero Bitmap Allocation)
                outputStream.writeBytes(twoHyphens + boundary + lineEnd)
                outputStream.writeBytes("Content-Disposition: form-data; name=\"photo\"; filename=\"${item.originalName}\"$lineEnd")
                outputStream.writeBytes("Content-Type: image/jpeg$lineEnd$lineEnd")

                FileInputStream(file).use { fis ->
                    val buffer = ByteArray(64 * 1024)
                    var bytesRead = fis.read(buffer)
                    while (bytesRead != -1) {
                        outputStream.write(buffer, 0, bytesRead)
                        bytesRead = fis.read(buffer)
                    }
                }

                outputStream.writeBytes(lineEnd)
                outputStream.writeBytes(twoHyphens + boundary + twoHyphens + lineEnd)
                outputStream.flush()
            }

            val responseCode = connection.responseCode
            if (responseCode in 200..299) {
                // Mark FORWARDED in SQLite database.
                // DO NOT DELETE FILE IMMEDIATELY! It remains safe in ready_photos until safe retention purge.
                db.markForwarded(item.uploadId)
                CompanionLogger.i(
                    event = "HTTP_FORWARD_SUCCESS",
                    uploadId = item.uploadId,
                    filename = item.originalName,
                    status = "FORWARDED",
                    details = "HTTP $responseCode: Photo safely forwarded to Django"
                )
            } else {
                val errorStreamText = connection.errorStream?.bufferedReader()?.use { it.readText() } ?: "No response body"
                val errorMsg = "HTTP $responseCode: $errorStreamText"
                handleUploadFailure(db, item, errorMsg)
            }

        } catch (e: Exception) {
            val errorMsg = "Network exception: ${e.javaClass.simpleName}: ${e.message}"
            handleUploadFailure(db, item, errorMsg, e)
        } finally {
            connection?.disconnect()
        }
    }

    private fun handleUploadFailure(
        db: UploadQueueDatabase,
        item: UploadQueueDatabase.QueueItem,
        errorMsg: String,
        throwable: Throwable? = null
    ) {
        val attempts = item.attempts + 1
        // Exponential backoff: 2s, 4s, 8s, 16s, 32s, 60s
        val backoffDelayMs = Math.min(2000L * (1L shl Math.min(attempts, 6)), 60000L)
        val nextRetryAt = System.currentTimeMillis() + backoffDelayMs

        db.markFailed(item.uploadId, errorMsg, nextRetryAt)
        CompanionLogger.e(
            event = "HTTP_FORWARD_FAILURE",
            uploadId = item.uploadId,
            filename = item.originalName,
            status = "RETRY_SCHEDULED",
            details = "Attempt $attempts/5 failed. Next retry in ${backoffDelayMs / 1000}s. Error: $errorMsg",
            throwable = throwable
        )
    }
}
