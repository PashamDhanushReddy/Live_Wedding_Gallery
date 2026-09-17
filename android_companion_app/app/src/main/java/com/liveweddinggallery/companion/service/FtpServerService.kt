package com.liveweddinggallery.companion.service

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log
import org.apache.ftpserver.FtpServer
import org.apache.ftpserver.FtpServerFactory
import org.apache.ftpserver.listener.ListenerFactory
import org.apache.ftpserver.usermanager.impl.BaseUser
import org.apache.ftpserver.usermanager.impl.WritePermission
import org.apache.ftpserver.usermanager.impl.WritePermission
import org.apache.ftpserver.usermanager.PropertiesUserManagerFactory
import org.apache.ftpserver.DataConnectionConfigurationFactory
import java.io.File
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import android.content.pm.ServiceInfo
import androidx.core.app.NotificationCompat

class FtpServerService : Service() {
    private var server: FtpServer? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        createNotificationChannel()
        val notification = NotificationCompat.Builder(this, "ftp_channel_id")
            .setContentTitle("FTP Server Running")
            .setContentText("Listening for camera photos...")
            .setSmallIcon(android.R.drawable.ic_menu_camera)
            .build()
            
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(1, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
        } else {
            startForeground(1, notification)
        }
        
        startFtpServer()
        UploadManager.start(this)
        return START_STICKY
    }
    
    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val serviceChannel = NotificationChannel(
                "ftp_channel_id",
                "FTP Server Channel",
                NotificationManager.IMPORTANCE_LOW
            )
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(serviceChannel)
        }
    }

    private fun startFtpServer() {
        try {
            val serverFactory = FtpServerFactory()
            
            // 1. Configure Port and Passive Data Connections
            val factory = ListenerFactory()
            factory.port = 2121
            
            val dataConnFactory = DataConnectionConfigurationFactory()
            dataConnFactory.passivePorts = "50000-55000"
            factory.dataConnectionConfiguration = dataConnFactory.createDataConnectionConfiguration()
            
            serverFactory.addListener("default", factory.createListener())

            // 2. Setup the Home Directory
            val ftpDir = File(filesDir, "ftp")
            if (!ftpDir.exists()) ftpDir.mkdirs()

            // 3. Configure User
            val user = BaseUser()
            user.name = "wedding"
            user.password = "password123"
            user.homeDirectory = ftpDir.absolutePath
            // Grant permission so the camera can actually upload/write files
            user.authorities = listOf(WritePermission())
            
            // 4. Attach User to Server
            val userManagerFactory = PropertiesUserManagerFactory()
            val userManager = userManagerFactory.createUserManager()
            userManager.save(user)
            serverFactory.userManager = userManager

            // 5. Start Server
            server = serverFactory.createServer()
            server?.start()
            Log.d("FTP", "FTP Server fully started and authenticated on port 2121")
            
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        server?.stop()
        UploadManager.stop()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
