package com.liveweddinggallery.companion.service

import android.content.Context
import kotlinx.coroutines.*
import java.io.File
import com.liveweddinggallery.companion.network.DjangoApi

object UploadManager {
    private var job: Job? = null
    
    fun start(context: Context) {
        if (job != null) return
        job = CoroutineScope(Dispatchers.IO).launch {
            while (isActive) {
                syncWithDjango(context)
                processQueue(context)
                delay(5000) // Poll every 5 seconds
            }
        }
    }
    
    fun stop() {
        job?.cancel()
        job = null
    }
    
    private suspend fun syncWithDjango(context: Context) {
        // Send local IP, storage usage (3GB limit logic) to Django
    }
    
    private suspend fun processQueue(context: Context) {
        // 1. Check local Room DB for QUEUED photos
        // 2. Upload to Django API
        // 3. If 200 OK -> Delete local file and DB row
        // 4. If Failure -> Mark FAILED and retry later
    }
}
