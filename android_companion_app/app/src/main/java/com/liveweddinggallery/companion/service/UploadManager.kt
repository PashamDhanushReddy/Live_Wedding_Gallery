package com.liveweddinggallery.companion.service

import android.content.Context
import android.util.Log
import kotlinx.coroutines.*
import java.io.*
import java.net.HttpURLConnection
import java.net.URL

object UploadManager {
    private var job: Job? = null
    // You'd ideally store this config somewhere
    private const val DJANGO_API_URL = "https://live-wedding-gallery.onrender.com/api/weddings/sandeep-prathyusha/photographer/phone"
    private const val DEVICE_ID = "phone_01"
    
    fun start(context: Context) {
        if (job != null) return
        job = CoroutineScope(Dispatchers.IO).launch {
            while (isActive) {
                try {
                    syncWithDjango(context)
                    processQueue(context)
                } catch (e: Exception) {
                    Log.e("UploadManager", "Error in background loop: ${e.message}")
                }
                delay(1000) // Poll every 1 second for faster uploads
            }
        }
    }
    
    fun stop() {
        job?.cancel()
        job = null
    }
    
    private suspend fun syncWithDjango(context: Context) {
        // We'll skip complex stats syncing for now and focus on photo uploading.
    }
    
    private suspend fun processQueue(context: Context) {
        val ftpDir = File(context.filesDir, "ftp")
        if (!ftpDir.exists()) return

        val validExtensions = listOf(".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif")
        val files = ftpDir.listFiles()?.filter { file -> 
            file.isFile && validExtensions.any { ext -> file.name.endsWith(ext, true) }
        } ?: return

        for (file in files) {
            Log.d("UploadManager", "Found file ${file.name}, uploading to Django...")
            val success = uploadFile(file)
            if (success) {
                Log.d("UploadManager", "Upload success! Deleting local file ${file.name}")
                file.delete()
            } else {
                Log.d("UploadManager", "Upload failed for ${file.name}")
            }
        }
    }

    private fun uploadFile(file: File): Boolean {
        val boundary = "*****"
        val lineEnd = "\r\n"
        val twoHyphens = "--"
        
        try {
            val url = URL("$DJANGO_API_URL/upload/")
            val connection = url.openConnection() as HttpURLConnection
            connection.connectTimeout = 5000 // 5 seconds timeout
            connection.readTimeout = 5000
            connection.doInput = true
            connection.doOutput = true
            connection.useCaches = false
            connection.requestMethod = "POST"
            connection.setRequestProperty("Connection", "Keep-Alive")
            connection.setRequestProperty("Content-Type", "multipart/form-data;boundary=$boundary")

            val outputStream = DataOutputStream(connection.outputStream)

            // 1. Add device_id
            outputStream.writeBytes(twoHyphens + boundary + lineEnd)
            outputStream.writeBytes("Content-Disposition: form-data; name=\"device_id\"$lineEnd$lineEnd")
            outputStream.writeBytes("$DEVICE_ID$lineEnd")

            // 2. Add file
            outputStream.writeBytes(twoHyphens + boundary + lineEnd)
            outputStream.writeBytes("Content-Disposition: form-data; name=\"photo\"; filename=\"${file.name}\"$lineEnd")
            outputStream.writeBytes("Content-Type: image/jpeg$lineEnd$lineEnd")

            val fileInputStream = FileInputStream(file)
            var bytesAvailable = fileInputStream.available()
            var bufferSize = Math.min(bytesAvailable, 1024 * 1024)
            val buffer = ByteArray(bufferSize)

            var bytesRead = fileInputStream.read(buffer, 0, bufferSize)
            while (bytesRead > 0) {
                outputStream.write(buffer, 0, bytesRead)
                bytesAvailable = fileInputStream.available()
                bufferSize = Math.min(bytesAvailable, 1024 * 1024)
                bytesRead = fileInputStream.read(buffer, 0, bufferSize)
            }
            outputStream.writeBytes(lineEnd)
            outputStream.writeBytes(twoHyphens + boundary + twoHyphens + lineEnd)
            
            fileInputStream.close()
            outputStream.flush()
            outputStream.close()

            val responseCode = connection.responseCode
            val isSuccess = responseCode in 200..299
            
            if (!isSuccess) {
                val errorMsg = connection.errorStream?.bufferedReader()?.use { it.readText() } ?: "No error stream"
                Log.e("UploadManager", "Upload failed with HTTP $responseCode: $errorMsg")
            }
            
            return isSuccess
            
        } catch (e: Exception) {
            Log.e("UploadManager", "Exception during upload: ${e.message}", e)
            return false
        }
    }
}
