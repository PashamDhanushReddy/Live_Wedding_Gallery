package com.liveweddinggallery.companion.util

import android.util.Log
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.CopyOnWriteArrayList

object CompanionLogger {
    private const val TAG = "WeddingCompanion"
    private const val MAX_RING_BUFFER = 100
    private val dateFormat = SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS", Locale.US)
    
    data class LogEntry(
        val timestamp: Long,
        val formattedTime: String,
        val event: String,
        val uploadId: String?,
        val filename: String?,
        val status: String,
        val details: String,
        val isError: Boolean = false
    )

    private val ringBuffer = ArrayDeque<LogEntry>()
    private val listeners = CopyOnWriteArrayList<(LogEntry) -> Unit>()

    fun addListener(listener: (LogEntry) -> Unit) {
        listeners.add(listener)
    }

    fun removeListener(listener: (LogEntry) -> Unit) {
        listeners.remove(listener)
    }

    @Synchronized
    fun getRecentLogs(): List<LogEntry> {
        return ringBuffer.toList()
    }

    fun i(event: String, uploadId: String? = null, filename: String? = null, status: String = "INFO", details: String = "") {
        record(event, uploadId, filename, status, details, isError = false)
    }

    fun w(event: String, uploadId: String? = null, filename: String? = null, status: String = "WARN", details: String = "") {
        record(event, uploadId, filename, status, details, isError = false)
    }

    fun e(event: String, uploadId: String? = null, filename: String? = null, status: String = "ERROR", details: String = "", throwable: Throwable? = null) {
        val fullDetails = if (throwable != null) {
            if (details.isNotEmpty()) "$details | ${throwable.message}" else throwable.message ?: "Unknown error"
        } else {
            details
        }
        record(event, uploadId, filename, status, fullDetails, isError = true)
        if (throwable != null) {
            Log.e(TAG, "[$event] uploadId=$uploadId filename=$filename status=$status: $fullDetails", throwable)
        }
    }

    @Synchronized
    private fun record(
        event: String,
        uploadId: String?,
        filename: String?,
        status: String,
        details: String,
        isError: Boolean
    ) {
        val now = System.currentTimeMillis()
        val entry = LogEntry(
            timestamp = now,
            formattedTime = dateFormat.format(Date(now)),
            event = event,
            uploadId = uploadId,
            filename = filename,
            status = status,
            details = details,
            isError = isError
        )

        if (ringBuffer.size >= MAX_RING_BUFFER) {
            ringBuffer.removeFirst()
        }
        ringBuffer.addLast(entry)

        val logMessage = "[FTP_INGEST] [${entry.formattedTime}] [${uploadId ?: "-"}] [${filename ?: "-"}] [$event:$status] $details"
        if (isError) {
            Log.e(TAG, logMessage)
        } else {
            Log.i(TAG, logMessage)
        }

        for (listener in listeners) {
            try {
                listener(entry)
            } catch (_: Exception) {}
        }
    }
}

