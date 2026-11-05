package com.liveweddinggallery.companion.db

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

class UploadQueueDatabase private constructor(context: Context) :
    SQLiteOpenHelper(context.applicationContext, DATABASE_NAME, null, DATABASE_VERSION) {

    data class QueueItem(
        val id: Long,
        val uploadId: String,
        val originalName: String,
        val filePath: String,
        val fileSize: Long,
        val checksumSha256: String,
        val folder: String,
        val status: String,
        val attempts: Int,
        val lastError: String?,
        val nextRetryAt: Long,
        val createdAt: Long,
        val forwardedAt: Long?
    )

    data class QueueStats(
        val pendingCount: Int,
        val uploadingCount: Int,
        val forwardedCount: Int,
        val failedCount: Int,
        val totalCount: Int
    )

    companion object {
        private const val DATABASE_NAME = "wedding_upload_queue.db"
        private const val DATABASE_VERSION = 1
        private const val TABLE_NAME = "upload_queue"

        const val STATUS_PENDING = "PENDING"
        const val STATUS_UPLOADING = "UPLOADING"
        const val STATUS_FORWARDED = "FORWARDED"
        const val STATUS_FAILED = "FAILED"
        const val STATUS_CORRUPTED = "CORRUPTED"
        const val STATUS_PURGED = "PURGED"

        @Volatile
        private var INSTANCE: UploadQueueDatabase? = null

        fun getInstance(context: Context): UploadQueueDatabase {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: UploadQueueDatabase(context).also { INSTANCE = it }
            }
        }
    }

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL(
            """
            CREATE TABLE $TABLE_NAME (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_id TEXT UNIQUE NOT NULL,
                original_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                checksum_sha256 TEXT NOT NULL,
                folder TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT '$STATUS_PENDING',
                attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                next_retry_at INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL,
                forwarded_at INTEGER
            )
            """.trimIndent()
        )

        db.execSQL("CREATE INDEX idx_queue_status_retry ON $TABLE_NAME (status, next_retry_at)")
        db.execSQL("CREATE INDEX idx_queue_checksum ON $TABLE_NAME (checksum_sha256)")
        db.execSQL("CREATE INDEX idx_queue_upload_id ON $TABLE_NAME (upload_id)")
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        // Future schema migrations
    }

    @Synchronized
    fun enqueue(
        uploadId: String,
        originalName: String,
        filePath: String,
        fileSize: Long,
        checksumSha256: String,
        folder: String
    ): Boolean {
        val db = writableDatabase
        val values = ContentValues().apply {
            put("upload_id", uploadId)
            put("original_name", originalName)
            put("file_path", filePath)
            put("file_size", fileSize)
            put("checksum_sha256", checksumSha256)
            put("folder", folder)
            put("status", STATUS_PENDING)
            put("attempts", 0)
            put("next_retry_at", 0L)
            put("created_at", System.currentTimeMillis())
        }
        val result = db.insertWithOnConflict(TABLE_NAME, null, values, SQLiteDatabase.CONFLICT_IGNORE)
        return result != -1L
    }

    @Synchronized
    fun isDuplicateChecksum(checksumSha256: String): Boolean {
        if (checksumSha256.isEmpty()) return false
        val db = readableDatabase
        val cursor = db.rawQuery(
            "SELECT 1 FROM $TABLE_NAME WHERE checksum_sha256 = ? AND status IN ('$STATUS_PENDING', '$STATUS_UPLOADING', '$STATUS_FORWARDED', '$STATUS_PURGED') LIMIT 1",
            arrayOf(checksumSha256)
        )
        val exists = cursor.moveToFirst()
        cursor.close()
        return exists
    }

    @Synchronized
    fun getPendingBatch(limit: Int = 10): List<QueueItem> {
        val db = readableDatabase
        val now = System.currentTimeMillis()
        val items = mutableListOf<QueueItem>()
        val cursor = db.rawQuery(
            """
            SELECT id, upload_id, original_name, file_path, file_size, checksum_sha256, folder, status, attempts, last_error, next_retry_at, created_at, forwarded_at
            FROM $TABLE_NAME
            WHERE status IN ('$STATUS_PENDING', '$STATUS_FAILED') AND next_retry_at <= ? AND attempts < 5
            ORDER BY created_at ASC
            LIMIT ?
            """.trimIndent(),
            arrayOf(now.toString(), limit.toString())
        )

        while (cursor.moveToNext()) {
            items.add(cursorToQueueItem(cursor))
        }
        cursor.close()
        return items
    }

    @Synchronized
    fun markUploading(uploadId: String) {
        val db = writableDatabase
        val values = ContentValues().apply {
            put("status", STATUS_UPLOADING)
        }
        db.update(TABLE_NAME, values, "upload_id = ?", arrayOf(uploadId))
    }

    @Synchronized
    fun markForwarded(uploadId: String) {
        val db = writableDatabase
        val values = ContentValues().apply {
            put("status", STATUS_FORWARDED)
            put("forwarded_at", System.currentTimeMillis())
            putNull("last_error")
        }
        db.update(TABLE_NAME, values, "upload_id = ?", arrayOf(uploadId))
    }

    @Synchronized
    fun markFailed(uploadId: String, error: String, nextRetryAt: Long) {
        val db = writableDatabase
        db.execSQL(
            """
            UPDATE $TABLE_NAME
            SET status = '$STATUS_FAILED',
                attempts = attempts + 1,
                last_error = ?,
                next_retry_at = ?
            WHERE upload_id = ?
            """.trimIndent(),
            arrayOf(error, nextRetryAt, uploadId)
        )
    }

    @Synchronized
    fun markCorrupted(uploadId: String, error: String) {
        val db = writableDatabase
        val values = ContentValues().apply {
            put("status", STATUS_CORRUPTED)
            put("last_error", error)
        }
        db.update(TABLE_NAME, values, "upload_id = ?", arrayOf(uploadId))
    }

    @Synchronized
    fun markPurged(uploadId: String) {
        val db = writableDatabase
        val values = ContentValues().apply {
            put("status", STATUS_PURGED)
        }
        db.update(TABLE_NAME, values, "upload_id = ?", arrayOf(uploadId))
    }

    @Synchronized
    fun resetStuckUploadingToPending(): Int {
        val db = writableDatabase
        val values = ContentValues().apply {
            put("status", STATUS_PENDING)
            put("next_retry_at", 0L)
        }
        return db.update(TABLE_NAME, values, "status = ?", arrayOf(STATUS_UPLOADING))
    }

    @Synchronized
    fun retryAllFailed(): Int {
        val db = writableDatabase
        val values = ContentValues().apply {
            put("status", STATUS_PENDING)
            put("next_retry_at", 0L)
            put("attempts", 0)
        }
        return db.update(TABLE_NAME, values, "status = ?", arrayOf(STATUS_FAILED))
    }

    @Synchronized
    fun getForwardedForCleanup(cutoffTime: Long, limit: Int = 50): List<QueueItem> {
        val db = readableDatabase
        val items = mutableListOf<QueueItem>()
        val cursor = db.rawQuery(
            """
            SELECT id, upload_id, original_name, file_path, file_size, checksum_sha256, folder, status, attempts, last_error, next_retry_at, created_at, forwarded_at
            FROM $TABLE_NAME
            WHERE status = '$STATUS_FORWARDED' AND forwarded_at <= ?
            ORDER BY forwarded_at ASC
            LIMIT ?
            """.trimIndent(),
            arrayOf(cutoffTime.toString(), limit.toString())
        )
        while (cursor.moveToNext()) {
            items.add(cursorToQueueItem(cursor))
        }
        cursor.close()
        return items
    }

    @Synchronized
    fun getQueueStats(): QueueStats {
        val db = readableDatabase
        var pending = 0
        var uploading = 0
        var forwarded = 0
        var failed = 0
        var total = 0

        val cursor = db.rawQuery(
            """
            SELECT status, COUNT(*)
            FROM $TABLE_NAME
            WHERE status != '$STATUS_PURGED'
            GROUP BY status
            """.trimIndent(),
            null
        )

        while (cursor.moveToNext()) {
            val status = cursor.getString(0)
            val count = cursor.getInt(1)
            total += count
            when (status) {
                STATUS_PENDING -> pending = count
                STATUS_UPLOADING -> uploading = count
                STATUS_FORWARDED -> forwarded = count
                STATUS_FAILED -> failed = count
            }
        }
        cursor.close()

        return QueueStats(
            pendingCount = pending,
            uploadingCount = uploading,
            forwardedCount = forwarded,
            failedCount = failed,
            totalCount = total
        )
    }

    private fun cursorToQueueItem(cursor: android.database.Cursor): QueueItem {
        val forwardedAtCol = cursor.getColumnIndex("forwarded_at")
        val forwardedAt = if (cursor.isNull(forwardedAtCol)) null else cursor.getLong(forwardedAtCol)

        return QueueItem(
            id = cursor.getLong(cursor.getColumnIndexOrThrow("id")),
            uploadId = cursor.getString(cursor.getColumnIndexOrThrow("upload_id")),
            originalName = cursor.getString(cursor.getColumnIndexOrThrow("original_name")),
            filePath = cursor.getString(cursor.getColumnIndexOrThrow("file_path")),
            fileSize = cursor.getLong(cursor.getColumnIndexOrThrow("file_size")),
            checksumSha256 = cursor.getString(cursor.getColumnIndexOrThrow("checksum_sha256")),
            folder = cursor.getString(cursor.getColumnIndexOrThrow("folder")),
            status = cursor.getString(cursor.getColumnIndexOrThrow("status")),
            attempts = cursor.getInt(cursor.getColumnIndexOrThrow("attempts")),
            lastError = cursor.getString(cursor.getColumnIndexOrThrow("last_error")),
            nextRetryAt = cursor.getLong(cursor.getColumnIndexOrThrow("next_retry_at")),
            createdAt = cursor.getLong(cursor.getColumnIndexOrThrow("created_at")),
            forwardedAt = forwardedAt
        )
    }
}

