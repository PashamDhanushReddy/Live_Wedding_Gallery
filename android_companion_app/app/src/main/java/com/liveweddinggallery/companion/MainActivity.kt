package com.liveweddinggallery.companion

import android.content.Context
import android.content.Intent
import android.net.wifi.WifiManager
import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Show IP Address
        val wifiManager = applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
        val ipAddress = wifiManager.connectionInfo.ipAddress
        val ipString = String.format(
            "%d.%d.%d.%d",
            ipAddress and 0xff,
            ipAddress shr 8 and 0xff,
            ipAddress shr 16 and 0xff,
            ipAddress shr 24 and 0xff
        )
        
        val tvIp = findViewById<TextView>(R.id.tvIpAddress)
        if (ipAddress == 0) {
            tvIp.text = "Connect to Wi-Fi/Hotspot"
        } else {
            tvIp.text = ipString
        }

        // Start the FTP and Upload Service
        val serviceIntent = Intent(this, com.liveweddinggallery.companion.service.FtpServerService::class.java)
        startService(serviceIntent)
    }
}
