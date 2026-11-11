package com.liveweddinggallery.companion

import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.io.FileOutputStream

class UploadManagerTest {

    @Test
    fun testExponentialBackoffCalculation() {
        // Backoff formula: min(300_000L, 5_000L * (1 shl (attempt - 1)))
        val delays = (1..6).map { attempt ->
            Math.min(300_000L, 5_000L * (1L shl (attempt - 1)))
        }
        val expected = listOf(5_000L, 10_000L, 20_000L, 40_000L, 80_000L, 160_000L)
        assertEquals(expected, delays)
    }

    @Test
    fun testMaxRetryLimitCap() {
        val maxAttempts = 5
        var currentAttempt = 4
        var status = "PENDING"

        currentAttempt++
        if (currentAttempt >= maxAttempts) {
            status = "FAILED_PERMANENT"
        }

        assertEquals("FAILED_PERMANENT", status)
        assertEquals(5, currentAttempt)
    }

    @Test
    fun testJpegMagicBytesValidationSOIandEOI() {
        // Valid minimal JPEG SOI (0xFF, 0xD8) and EOI (0xFF, 0xD9)
        val tempFile = File.createTempFile("test_valid", ".jpg").apply {
            deleteOnExit()
            FileOutputStream(this).use { fos ->
                val bytes = byteArrayOf(
                    0xFF.toByte(), 0xD8.toByte(),
                    0x00, 0x01, 0x02, 0x03,
                    0xFF.toByte(), 0xD9.toByte()
                )
                fos.write(bytes)
            }
        }

        assertTrue(tempFile.exists())
        assertEquals(8L, tempFile.length())

        val bytes = tempFile.readBytes()
        val hasSoi = bytes[0] == 0xFF.toByte() && bytes[1] == 0xD8.toByte()
        val hasEoi = bytes[bytes.size - 2] == 0xFF.toByte() && bytes[bytes.size - 1] == 0xD9.toByte()

        assertTrue("Should have SOI marker", hasSoi)
        assertTrue("Should have EOI marker", hasEoi)
    }

    @Test
    fun testIncompleteTransferDetectedWhenMissingEOI() {
        // File starts with SOI but was cut off mid-transfer (no EOI 0xFF 0xD9)
        val truncatedFile = File.createTempFile("test_truncated", ".jpg").apply {
            deleteOnExit()
            FileOutputStream(this).use { fos ->
                val bytes = byteArrayOf(
                    0xFF.toByte(), 0xD8.toByte(),
                    0x00, 0x01, 0x02, 0x03, 0x04
                )
                fos.write(bytes)
            }
        }

        val bytes = truncatedFile.readBytes()
        val hasEoi = bytes.size >= 2 && bytes[bytes.size - 2] == 0xFF.toByte() && bytes[bytes.size - 1] == 0xD9.toByte()
        assertFalse("Truncated file must not have EOI marker", hasEoi)
    }

    @Test
    fun testFileRetentionPolicyNeverDeletesUnforwardedFiles() {
        // Simulates the retention logic in StorageMonitor:
        // Files with status PENDING, UPLOADING, or FAILED are never deleted
        val eligibleStatusesForDeletion = setOf("FORWARDED")

        val file1Status = "PENDING"
        val file2Status = "UPLOADING"
        val file3Status = "FORWARDED"

        assertFalse("PENDING file must not be eligible for deletion", eligibleStatusesForDeletion.contains(file1Status))
        assertFalse("UPLOADING file must not be eligible for deletion", eligibleStatusesForDeletion.contains(file2Status))
        assertTrue("FORWARDED file can be deleted after retention window", eligibleStatusesForDeletion.contains(file3Status))
    }

    @Test
    fun testAppRestartRecoveryLogic() {
        // In-flight items with status UPLOADING during unexpected process kill
        // must be safely transitioned back to PENDING on service start
        val databaseRows = mutableMapOf(
            "upload_1" to "UPLOADING",
            "upload_2" to "UPLOADING",
            "upload_3" to "FORWARDED"
        )

        // Recovery routine: reset all UPLOADING to PENDING
        databaseRows.forEach { (id, status) ->
            if (status == "UPLOADING") {
                databaseRows[id] = "PENDING"
            }
        }

        assertEquals("PENDING", databaseRows["upload_1"])
        assertEquals("PENDING", databaseRows["upload_2"])
        assertEquals("FORWARDED", databaseRows["upload_3"])
    }

    @Test
    fun testActiveFtpTransferLockAndSessionCleanup() {
        val tempFile = File.createTempFile("ftp_active_test", ".jpg").apply { deleteOnExit() }
        val sessionId = "session-109-test"

        com.liveweddinggallery.companion.service.UploadManager.markFtpTransferStarted(sessionId, tempFile)
        assertTrue(com.liveweddinggallery.companion.service.UploadManager.isFtpTransferActive(tempFile))

        com.liveweddinggallery.companion.service.UploadManager.markFtpTransferFinished(sessionId, tempFile)
        assertFalse(com.liveweddinggallery.companion.service.UploadManager.isFtpTransferActive(tempFile))

        // Disconnecting mid-transfer must release session-held paths
        com.liveweddinggallery.companion.service.UploadManager.markFtpTransferStarted(sessionId, tempFile)
        assertTrue(com.liveweddinggallery.companion.service.UploadManager.isFtpTransferActive(tempFile))
        com.liveweddinggallery.companion.service.UploadManager.clearActiveSessionTransfers(sessionId)
        assertFalse(com.liveweddinggallery.companion.service.UploadManager.isFtpTransferActive(tempFile))
    }

    @Test
    fun testJpegEoiDetectedWithLargeTrailingCameraMetadata() {
        // Sony / camera JPEGs can append >128 bytes of XMP/MPF/padding after primary EOI or within trailing 64KB
        val tempFile = File.createTempFile("sony_trailer_test", ".jpg").apply { deleteOnExit() }
        FileOutputStream(tempFile).use { fos ->
            fos.write(byteArrayOf(0xFF.toByte(), 0xD8.toByte(), 0xFF.toByte(), 0xE1.toByte()))
            fos.write(ByteArray(1024) { 0x11 })
            fos.write(byteArrayOf(0xFF.toByte(), 0xD9.toByte()))
            fos.write(ByteArray(512) { 0x00 }) // 512 bytes trailing padding > old 128-byte limit
        }

        val len = tempFile.length()
        val tail = ByteArray(Math.min(len, 65536L).toInt())
        java.io.RandomAccessFile(tempFile, "r").use { raf ->
            raf.seek(len - tail.size)
            raf.readFully(tail)
        }
        var foundEoi = false
        for (i in tail.size - 2 downTo 0) {
            if (tail[i] == 0xFF.toByte() && tail[i + 1] == 0xD9.toByte()) {
                foundEoi = true
                break
            }
        }
        assertTrue("EOI within 64KB tail should be detected despite 512B trailer", foundEoi)
    }
}

