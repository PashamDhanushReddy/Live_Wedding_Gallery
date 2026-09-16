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
import org.apache.ftpserver.usermanager.PropertiesUserManagerFactory
import java.io.File

class FtpServerService : Service() {
    private var server: FtpServer? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startFtpServer()
        UploadManager.start(this)
        return START_STICKY
    }

    private fun startFtpServer() {
        try {
            val serverFactory = FtpServerFactory()
            
            // 1. Configure Port
            val factory = ListenerFactory()
            factory.port = 2121
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
