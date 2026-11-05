package com.liveweddinggallery.companion.util

import android.graphics.BitmapFactory
import java.io.File
import java.io.FileInputStream
import java.io.RandomAccessFile
import java.security.MessageDigest

object FileIntegrityValidator {

    sealed class ValidationResult {
        data class Valid(val checksumSha256: String, val width: Int, val height: Int) : ValidationResult()
        data class Invalid(val reason: String) : ValidationResult()
    }

    fun validateFile(file: File): ValidationResult {
        if (!file.exists()) {
            return ValidationResult.Invalid("File does not exist: ${file.name}")
        }

        val length = file.length()
        if (length < 1024) { // Suspiciously small (<1KB) for a DSLR photo
            return ValidationResult.Invalid("File size too small (${length} bytes) for a valid photo")
        }

        // 1. Check Magic Bytes & EOF markers for JPEG
        val lowerName = file.name.lowercase()
        if (lowerName.endsWith(".jpg") || lowerName.endsWith(".jpeg")) {
            val isJpegValid = checkJpegHeaderAndTrailer(file)
            if (!isJpegValid) {
                return ValidationResult.Invalid("Incomplete JPEG: Missing SOI (0xFFD8) or EOI (0xFFD9) markers")
            }
        } else if (lowerName.endsWith(".png")) {
            val isPngValid = checkPngHeader(file)
            if (!isPngValid) {
                return ValidationResult.Invalid("Invalid PNG: Missing PNG header bytes")
            }
        }

        // 2. Bounds Probe via BitmapFactory (0 memory allocation)
        val boundsOptions = BitmapFactory.Options().apply {
            inJustDecodeBounds = true
        }
        BitmapFactory.decodeFile(file.absolutePath, boundsOptions)

        if (boundsOptions.outWidth <= 0 || boundsOptions.outHeight <= 0) {
            return ValidationResult.Invalid("Corrupted image header: Dimensions are invalid (${boundsOptions.outWidth}x${boundsOptions.outHeight})")
        }

        // 3. Compute SHA-256 Checksum
        val checksum = calculateSha256(file)
        if (checksum.isEmpty()) {
            return ValidationResult.Invalid("Failed to compute SHA-256 checksum")
        }

        return ValidationResult.Valid(
            checksumSha256 = checksum,
            width = boundsOptions.outWidth,
            height = boundsOptions.outHeight
        )
    }

    private fun checkJpegHeaderAndTrailer(file: File): Boolean {
        try {
            RandomAccessFile(file, "r").use { raf ->
                val length = raf.length()
                if (length < 4) return false

                // Check SOI (Start of Image): 0xFF, 0xD8
                val header = ByteArray(2)
                raf.seek(0)
                raf.readFully(header)
                if (header[0] != 0xFF.toByte() || header[1] != 0xD8.toByte()) {
                    return false
                }

                // Check EOI (End of Image): 0xFF, 0xD9
                // Note: Some cameras have up to a few trailing null/padding bytes after EOI
                val searchBytes = Math.min(length, 128L).toInt()
                val tail = ByteArray(searchBytes)
                raf.seek(length - searchBytes)
                raf.readFully(tail)

                var foundEoi = false
                for (i in tail.size - 2 downTo 0) {
                    if (tail[i] == 0xFF.toByte() && tail[i + 1] == 0xD9.toByte()) {
                        foundEoi = true
                        break
                    }
                }
                return foundEoi
            }
        } catch (_: Exception) {
            return false
        }
    }

    private fun checkPngHeader(file: File): Boolean {
        try {
            FileInputStream(file).use { fis ->
                val header = ByteArray(8)
                val read = fis.read(header)
                if (read < 8) return false
                // PNG signature: 137 80 78 71 13 10 26 10
                return (header[0] == 0x89.toByte() &&
                        header[1] == 0x50.toByte() &&
                        header[2] == 0x4E.toByte() &&
                        header[3] == 0x47.toByte() &&
                        header[4] == 0x0D.toByte() &&
                        header[5] == 0x0A.toByte() &&
                        header[6] == 0x1A.toByte() &&
                        header[7] == 0x0A.toByte())
            }
        } catch (_: Exception) {
            return false
        }
    }

    fun calculateSha256(file: File): String {
        return try {
            val digest = MessageDigest.getInstance("SHA-256")
            FileInputStream(file).use { fis ->
                val buffer = ByteArray(64 * 1024)
                var bytesRead = fis.read(buffer)
                while (bytesRead != -1) {
                    digest.update(buffer, 0, bytesRead)
                    bytesRead = fis.read(buffer)
                }
            }
            digest.digest().joinToString("") { "%02x".format(it) }
        } catch (_: Exception) {
            ""
        }
    }
}

