package com.liveweddinggallery.companion

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import android.content.Intent

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // In production, Jetpack Compose UI would be initialized here.
        // Start the FTP and Upload Service
        val serviceIntent = Intent(this, com.liveweddinggallery.companion.service.FtpServerService::class.java)
        startService(serviceIntent)
    }
}
