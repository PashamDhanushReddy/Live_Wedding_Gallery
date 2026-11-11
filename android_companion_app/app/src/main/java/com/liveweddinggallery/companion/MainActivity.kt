package com.liveweddinggallery.companion

import android.content.Context
import android.content.Intent
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.os.Build
import android.os.Bundle
import android.view.View
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.liveweddinggallery.companion.db.UploadQueueDatabase
import com.liveweddinggallery.companion.service.FtpServerService
import com.liveweddinggallery.companion.util.CompanionLogger
import com.liveweddinggallery.companion.util.NetworkUtils
import com.liveweddinggallery.companion.util.StorageMonitor
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.net.Inet4Address
import java.net.NetworkInterface

class MainActivity : AppCompatActivity() {

    private lateinit var tvIpAddress: TextView
    private lateinit var tvPendingCount: TextView
    private lateinit var tvForwardedCount: TextView
    private lateinit var tvFailedCount: TextView
    private lateinit var tvStorageInfo: TextView
    private lateinit var btnRetryFailed: Button
    private lateinit var spinnerFolder: Spinner

    private var connectivityManager: ConnectivityManager? = null
    private var networkCallback: ConnectivityManager.NetworkCallback? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        initViews()
        setupFolderSpinner()
        setupRetryButton()
        startFtpService()
        registerNetworkObserver()
        startPeriodicUiUpdater()
    }

    private fun initViews() {
        tvIpAddress = findViewById(R.id.tvIpAddress)
        tvPendingCount = findViewById(R.id.tvPendingCount)
        tvForwardedCount = findViewById(R.id.tvForwardedCount)
        tvFailedCount = findViewById(R.id.tvFailedCount)
        tvStorageInfo = findViewById(R.id.tvStorageInfo)
        btnRetryFailed = findViewById(R.id.btnRetryFailed)
        spinnerFolder = findViewById(R.id.spinnerFolder)

        val (ftpUser, ftpPass) = FtpServerService.getFtpCredentials(this)
        findViewById<TextView>(R.id.tvFtpCredentials)?.text = 
            "Port: ${FtpServerService.FTP_PORT}  |  User: $ftpUser  |  Pass: $ftpPass"

        tvIpAddress.setOnClickListener {
            val address = tvIpAddress.text.toString()
            if (address.startsWith("ftp://")) {
                val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as? android.content.ClipboardManager
                val clip = android.content.ClipData.newPlainText("FTP Address", address)
                clipboard?.setPrimaryClip(clip)
                Toast.makeText(this, "Copied to clipboard: $address", Toast.LENGTH_SHORT).show()
            }
        }

        tvStorageInfo.setOnClickListener {
            val freed = StorageMonitor.performSafeCleanup(this, forceDueToLowStorage = true)
            updateQueueStats()
            Toast.makeText(this, "Storage Auto-Cleaned! Cleaned $freed items.", Toast.LENGTH_SHORT).show()
        }

        refreshIpAddress()
    }

    private fun startFtpService() {
        val serviceIntent = Intent(this, FtpServerService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent)
        } else {
            startService(serviceIntent)
        }
    }

    private fun setupFolderSpinner() {
        val folders = arrayOf(
            "Engagement",
            "Pre-wedding Shoot",
            "Haldi",
            "Before Wedding Rituals",
            "Wedding Day",
            "Bride and Groom",
            "Bride",
            "Groom",
            "Uncategorized"
        )

        val adapter = ArrayAdapter(this, R.layout.spinner_item, folders)
        adapter.setDropDownViewResource(R.layout.spinner_dropdown_item)
        spinnerFolder.adapter = adapter

        val prefs = getSharedPreferences("WeddingCompanion", Context.MODE_PRIVATE)
        val rawSaved = prefs.getString("current_folder", "Wedding Day")
        val savedFolder = if (rawSaved == "Bride & Groom") {
            prefs.edit().putString("current_folder", "Bride and Groom").apply()
            "Bride and Groom"
        } else {
            rawSaved
        }
        val position = folders.indexOf(savedFolder)
        if (position >= 0) {
            spinnerFolder.setSelection(position)
        }

        spinnerFolder.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, pos: Int, id: Long) {
                val selected = folders[pos]
                prefs.edit().putString("current_folder", selected).apply()
                CompanionLogger.i("FOLDER_CHANGE", status = "UPDATED", details = "Active event folder set to: $selected")
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }
    }

    private fun setupRetryButton() {
        btnRetryFailed.setOnClickListener {
            val db = UploadQueueDatabase.getInstance(this)
            val count = db.retryAllFailed()
            Toast.makeText(this, "Retrying $count failed uploads...", Toast.LENGTH_SHORT).show()
            updateQueueStats()
        }
    }

    private fun registerNetworkObserver() {
        connectivityManager = getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
        val request = NetworkRequest.Builder()
            .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
            .build()

        networkCallback = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                runOnUiThread { refreshIpAddress() }
            }

            override fun onLost(network: Network) {
                runOnUiThread { refreshIpAddress() }
            }

            override fun onCapabilitiesChanged(network: Network, networkCapabilities: NetworkCapabilities) {
                runOnUiThread { refreshIpAddress() }
            }
        }

        try {
            connectivityManager?.registerNetworkCallback(request, networkCallback!!)
        } catch (_: Exception) {}
    }

    private fun refreshIpAddress() {
        val ip = NetworkUtils.getActiveWifiOrHotspotIp()
        if (ip.isNotEmpty()) {
            tvIpAddress.text = "ftp://$ip:${FtpServerService.FTP_PORT}"
        } else {
            tvIpAddress.text = "Connect Wi-Fi / Hotspot"
        }
    }

    private fun startPeriodicUiUpdater() {
        lifecycleScope.launch {
            while (isActive) {
                refreshIpAddress()
                updateQueueStats()
                delay(2000)
            }
        }
    }

    private fun updateQueueStats() {
        try {
            val db = UploadQueueDatabase.getInstance(this)
            val stats = db.getQueueStats()

            tvPendingCount.text = stats.pendingCount.toString()
            tvForwardedCount.text = stats.forwardedCount.toString()
            tvFailedCount.text = stats.failedCount.toString()

            btnRetryFailed.visibility = if (stats.failedCount > 0) View.VISIBLE else View.GONE

            val storage = StorageMonitor.getStorageStatus(this)
            tvStorageInfo.text = String.format(java.util.Locale.US, "%.1f GB Free", storage.availableGb)

            if (storage.isCritical) {
                tvStorageInfo.setTextColor(android.graphics.Color.RED)
            } else if (storage.isLow) {
                tvStorageInfo.setTextColor(android.graphics.Color.YELLOW)
            } else {
                tvStorageInfo.setTextColor(android.graphics.Color.WHITE)
            }
        } catch (_: Exception) {}
    }

    override fun onDestroy() {
        super.onDestroy()
        networkCallback?.let {
            try {
                connectivityManager?.unregisterNetworkCallback(it)
            } catch (_: Exception) {}
        }
    }
}
