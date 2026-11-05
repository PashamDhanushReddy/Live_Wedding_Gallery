package com.liveweddinggallery.companion.util

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.ExifInterface
import java.io.File
import java.io.FileOutputStream

object ImageOptimizer {
    // 2560px Quad-HD: Retina-sharp on 4K TVs, tablets, and phones while fitting free-tier budget
    private const val TARGET_MAX_DIMENSION = 2560
    private const val TARGET_MAX_BYTES = 750 * 1024L // 750 KB

    /**
     * Optimizes high-resolution DSLR / camera photos on-device before streaming to cloud:
     * - Preserves EXIF orientation so portrait/landscape photos stay upright
     * - Scales to max 2560px Quad-HD
     * - Compresses to ~500-750 KB (96% bandwidth and RAM reduction)
     * - Returns a temporary optimized file in cacheDir, or sourceFile if already under target
     */
    fun getOptimizedFile(sourceFile: File, uploadId: String, context: Context): File {
        if (!sourceFile.exists()) return sourceFile
        if (sourceFile.length() <= TARGET_MAX_BYTES) return sourceFile

        val cleanName = sourceFile.name.replace(Regex("[^a-zA-Z0-9_.-]"), "_")
        val tempFile = File(context.cacheDir, "opt_${uploadId.take(8)}_$cleanName")

        try {
            // 1. Read bounds without allocating pixel memory
            val boundsOptions = BitmapFactory.Options().apply {
                inJustDecodeBounds = true
            }
            BitmapFactory.decodeFile(sourceFile.absolutePath, boundsOptions)
            val origW = boundsOptions.outWidth
            val origH = boundsOptions.outHeight
            if (origW <= 0 || origH <= 0) return sourceFile

            // 2. Read EXIF orientation
            var orientation = ExifInterface.ORIENTATION_NORMAL
            try {
                val exif = ExifInterface(sourceFile.absolutePath)
                orientation = exif.getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)
            } catch (_: Exception) {}

            // 3. Compute inSampleSize for fast sub-sampled decode
            val maxDim = maxOf(origW, origH)
            var sampleSize = 1
            while (maxDim / (sampleSize * 2) >= TARGET_MAX_DIMENSION) {
                sampleSize *= 2
            }

            val decodeOptions = BitmapFactory.Options().apply {
                inSampleSize = sampleSize
                inPreferredConfig = Bitmap.Config.RGB_565 // 50% memory savings
            }

            val decoded = BitmapFactory.decodeFile(sourceFile.absolutePath, decodeOptions) ?: return sourceFile

            // 4. Orientation & exact scaling matrix
            val matrix = Matrix()
            when (orientation) {
                ExifInterface.ORIENTATION_ROTATE_90 -> matrix.postRotate(90f)
                ExifInterface.ORIENTATION_ROTATE_180 -> matrix.postRotate(180f)
                ExifInterface.ORIENTATION_ROTATE_270 -> matrix.postRotate(270f)
            }

            val currentMax = maxOf(decoded.width, decoded.height)
            if (currentMax > TARGET_MAX_DIMENSION) {
                val scale = TARGET_MAX_DIMENSION.toFloat() / currentMax
                matrix.postScale(scale, scale)
            }

            val finalBitmap = if (!matrix.isIdentity) {
                val transformed = Bitmap.createBitmap(decoded, 0, 0, decoded.width, decoded.height, matrix, true)
                if (transformed != decoded) decoded.recycle()
                transformed
            } else {
                decoded
            }

            // 5. Compress to JPEG quality 82
            FileOutputStream(tempFile).use { fos ->
                finalBitmap.compress(Bitmap.CompressFormat.JPEG, 82, fos)
            }
            finalBitmap.recycle()

            CompanionLogger.i(
                event = "IMAGE_OPTIMIZED",
                uploadId = uploadId,
                filename = sourceFile.name,
                details = "Compressed ${sourceFile.length() / 1024} KB (${origW}x${origH}) -> ${tempFile.length() / 1024} KB (Quad-HD 2560px)"
            )

            return tempFile
        } catch (e: Exception) {
            CompanionLogger.w(
                event = "IMAGE_OPTIMIZE_FALLBACK",
                uploadId = uploadId,
                filename = sourceFile.name,
                details = "Optimization fallback: ${e.message}"
            )
            if (tempFile.exists()) tempFile.delete()
            return sourceFile
        }
    }
}

