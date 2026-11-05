package com.liveweddinggallery.companion.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.net.wifi.WifiManager
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import com.liveweddinggallery.companion.util.CompanionLogger
import org.apache.ftpserver.DataConnectionConfigurationFactory
import org.apache.ftpserver.FtpServer
import org.apache.ftpserver.FtpServerFactory
import org.apache.ftpserver.listener.ListenerFactory
import org.apache.ftpserver.usermanager.PropertiesUserManagerFactory
import org.apache.ftpserver.usermanager.impl.BaseUser
import org.apache.ftpserver.usermanager.impl.WritePermission
import java.io.File

class FtpServerService : Service() {
    private var server: FtpServer? = null
    private var wakeLock: PowerManager.WakeLock? = null
    private var wifiLock: WifiManager.WifiLock? = null

    companion object {
        const val FTP_PORT = 2121
        const val PASSIVE_PORTS = "50000-55000"
        const val CHANNEL_ID = "ftp_channel_id"
        const val NOTIFICATION_ID = 1

        fun getFtpCredentials(context: Context): Pair<String, String> {
            val prefs = context.getSharedPreferences("WeddingCompanion", Context.MODE_PRIVATE)
            val username = prefs.getString("ftp_username", "wedding") ?: "wedding"
            var password = prefs.getString("ftp_password", null)
            if (password.isNullOrEmpty()) {
                val chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
                val random = java.security.SecureRandom()
                password = (1..8).map { chars[random.nextInt(chars.length)] }.joinToString("")
                prefs.edit().putString("ftp_password", password).apply()
            }
            return Pair(username, password)
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        createNotificationChannel()
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Wedding Camera FTP Server Active")
            .setContentText("Listening for Sony / DSLR photos on port $FTP_PORT...")
            .setSmallIcon(android.R.drawable.ic_menu_camera)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }

        acquireLocks()
        startFtpServer()
        UploadManager.start(this)

        return START_STICKY
    }

    private fun acquireLocks() {
        try {
            // 1. Partial WakeLock: Keep CPU awake when phone screen is turned off
            if (wakeLock == null || wakeLock?.isHeld == false) {
                val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
                wakeLock = powerManager.newWakeLock(
                    PowerManager.PARTIAL_WAKE_LOCK,
                    "WeddingCompanion:FtpWakeLock"
                ).apply {
                    setReferenceCounted(false)
                    acquire(12 * 60 * 60 * 1000L) // 12 hours guard
                }
            }

            // 2. WifiLock: Maintain high-throughput Wi-Fi radio connection for camera transfer
            if (wifiLock == null || wifiLock?.isHeld == false) {
                val wifiManager = applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
                wifiLock = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    wifiManager.createWifiLock(
                        WifiManager.WIFI_MODE_FULL_LOW_LATENCY,
                        "WeddingCompanion:FtpWifiLock"
                    )
                } else {
                    @Suppress("DEPRECATION")
                    wifiManager.createWifiLock(
                        WifiManager.WIFI_MODE_FULL_HIGH_PERF,
                        "WeddingCompanion:FtpWifiLock"
                    )
                }.apply {
                    setReferenceCounted(false)
                    acquire()
                }
            }
            CompanionLogger.i("SYSTEM_LOCKS", status = "ACQUIRED", details = "WakeLock and WifiLock engaged")
        } catch (e: Exception) {
            CompanionLogger.e("SYSTEM_LOCKS", status = "FAILED", details = "Could not acquire system locks: ${e.message}", throwable = e)
        }
    }

    private fun releaseLocks() {
        try {
            wakeLock?.let {
                if (it.isHeld) it.release()
            }
            wakeLock = null

            wifiLock?.let {
                if (it.isHeld) it.release()
            }
            wifiLock = null
            CompanionLogger.i("SYSTEM_LOCKS", status = "RELEASED", details = "WakeLock and WifiLock released")
        } catch (_: Exception) {}
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val serviceChannel = NotificationChannel(
                CHANNEL_ID,
                "FTP Server Channel",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Keeps the embedded FTP server active for camera image ingestion"
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(serviceChannel)
        }
    }

    private fun startFtpServer() {
        if (server != null && server?.isStopped == false) {
            return
        }

        try {
            val serverFactory = FtpServerFactory()

            // 1. Configure Port and Passive Data Connections
            val factory = ListenerFactory().apply {
                port = FTP_PORT
                idleTimeout = 120 // 120s idle timeout
            }

            val dataConnFactory = DataConnectionConfigurationFactory().apply {
                passivePorts = PASSIVE_PORTS
                idleTime = 120
            }
            factory.dataConnectionConfiguration = dataConnFactory.createDataConnectionConfiguration()
            serverFactory.addListener("default", factory.createListener())

            // 2. Setup Base Home Directory
            val ftpDir = File(filesDir, "ftp")
            if (!ftpDir.exists()) ftpDir.mkdirs()

            // 3. Configure User with Dynamic Secure Credentials
            val (ftpUser, ftpPass) = getFtpCredentials(applicationContext)
            val user = BaseUser().apply {
                name = ftpUser
                password = ftpPass
                homeDirectory = ftpDir.absolutePath
                authorities = listOf(WritePermission())
            }

            // 4. Attach User to Server
            val userManagerFactory = PropertiesUserManagerFactory()
            val userManager = userManagerFactory.createUserManager()
            userManager.save(user)
            serverFactory.userManager = userManager

            // 5. Attach Ftplet Transfer Listener for Clean Transfer Detection
            val listener = FtpTransferListener(ftpDir) { file ->
                UploadManager.onFileReceived(file, applicationContext)
            }
            serverFactory.ftplets = mapOf("transferListener" to listener)

            // 6. Start Server
            server = serverFactory.createServer()
            server?.start()

            CompanionLogger.i(
                event = "FTP_SERVER_START",
                status = "RUNNING",
                details = "FTP server listening on port $FTP_PORT (passive: $PASSIVE_PORTS, user: wedding)"
            )

        } catch (e: Exception) {
            CompanionLogger.e(
                event = "FTP_SERVER_START_FAIL",
                status = "ERROR",
                details = "Failed to start Apache FtpServer: ${e.message}",
                throwable = e
            )
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        try {
            server?.stop()
            server = null
            UploadManager.stop()
            releaseLocks()
            CompanionLogger.i("FTP_SERVER_STOP", status = "STOPPED", details = "FtpServerService stopped and cleaned up")
        } catch (e: Exception) {
            CompanionLogger.e("FTP_SERVER_STOP_ERROR", details = e.message ?: "", throwable = e)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
