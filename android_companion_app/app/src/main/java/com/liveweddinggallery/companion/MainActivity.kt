package com.liveweddinggallery.companion

import android.content.Context
import android.content.Intent
import android.net.wifi.WifiManager
import android.os.Bundle
import android.widget.TextView
import android.widget.ArrayAdapter
import android.widget.Spinner
import android.widget.AdapterView
import android.view.View
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
        
        setupFolderSpinner()
    }
    
    private fun setupFolderSpinner() {
        val spinner = findViewById<Spinner>(R.id.spinnerFolder)
        val folders = arrayOf(
            "Engagement",
            "Bride & Groom",
            "Pre-wedding Shoot",
            "Haldi",
            "Before Wedding Rituals",
            "Wedding Day"
        )
        
        val adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, folders)
        spinner.adapter = adapter
        
        // Restore previous selection if any
        val prefs = getSharedPreferences("WeddingCompanion", Context.MODE_PRIVATE)
        val savedFolder = prefs.getString("current_folder", "wedding day")
        val position = folders.indexOf(savedFolder)
        if (position >= 0) {
            spinner.setSelection(position)
        }
        
        spinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                val selected = folders[position]
                prefs.edit().putString("current_folder", selected).apply()
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }
    }
}
