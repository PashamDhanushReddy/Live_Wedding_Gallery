package com.liveweddinggallery.companion.util

import android.content.Context
import android.os.StatFs
import com.liveweddinggallery.companion.db.UploadQueueDatabase
import java.io.File

object StorageMonitor {
    const val LOW_STORAGE_THRESHOLD_BYTES = 1024L * 1024L * 1024L // 1 GB
    const val CRITICAL_STORAGE_THRESHOLD_BYTES = 500L * 1024L * 1024L // 500 MB
    const val DEFAULT_RETENTION_MS = 24L * 60L * 60L * 1000L // 24 Hours

    data class StorageStatus(
        val availableBytes: Long,
        val totalBytes: Long,
        val isLow: Boolean,
        val isCritical: Boolean
    ) {
        val availableMb: Long get() = availableBytes / (1024 * 1024)
        val totalMb: Long get() = totalBytes / (1024 * 1024)
        val availableGb: Double get() = availableBytes.toDouble() / (1024 * 1024 * 1024)
    }

    fun getStorageStatus(context: Context): StorageStatus {
        return try {
            val stat = StatFs(context.filesDir.path)
            val available = stat.availableBlocksLong * stat.blockSizeLong
            val total = stat.blockCountLong * stat.blockSizeLong
            StorageStatus(
                availableBytes = available,
                totalBytes = total,
                isLow = available < LOW_STORAGE_THRESHOLD_BYTES,
                isCritical = available < CRITICAL_STORAGE_THRESHOLD_BYTES
            )
        } catch (_: Exception) {
            StorageStatus(
                availableBytes = Long.MAX_VALUE,
                totalBytes = Long.MAX_VALUE,
                isLow = false,
                isCritical = false
            )
        }
    }

    /**
     * Safely prunes ONLY files that have been successfully FORWARDED to the Django backend.
     * Never deletes PENDING, UPLOADING, or unverified files.
     */
    fun performSafeCleanup(context: Context, forceDueToLowStorage: Boolean = false): Int {
        val db = UploadQueueDatabase.getInstance(context)
        val status = getStorageStatus(context)
        val retention = if (forceDueToLowStorage || status.isLow) 0L else DEFAULT_RETENTION_MS
        val cutoffTime = System.currentTimeMillis() - retention

        val candidates = db.getForwardedForCleanup(cutoffTime = cutoffTime, limit = 50)
        var cleanedCount = 0

        for (item in candidates) {
            try {
                val file = File(item.filePath)
                if (file.exists()) {
                    val deleted = file.delete()
                    if (deleted) {
                        db.markPurged(item.uploadId)
                        cleanedCount++
                        CompanionLogger.i(
                            event = "STORAGE_PURGE",
                            uploadId = item.uploadId,
                            filename = item.originalName,
                            status = "PURGED",
                            details = "Safely deleted forwarded file. Freed ${item.fileSize / 1024} KB"
                        )
                    }
                } else {
                    db.markPurged(item.uploadId)
                }
            } catch (e: Exception) {
                CompanionLogger.e(
                    event = "STORAGE_PURGE_ERROR",
                    uploadId = item.uploadId,
                    filename = item.originalName,
                    details = "Error purging file: ${e.message}",
                    throwable = e
                )
            }
        }

        return cleanedCount
    }
}

