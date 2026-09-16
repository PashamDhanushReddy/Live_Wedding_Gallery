package com.liveweddinggallery.companion.service

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log
import org.apache.ftpserver.FtpServer
import org.apache.ftpserver.FtpServerFactory
import org.apache.ftpserver.listener.ListenerFactory
import org.apache.ftpserver.usermanager.impl.BaseUser

class FtpServerService : Service() {
    private var server: FtpServer? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startFtpServer()
        // Also start the UploadManager coroutine here
        UploadManager.start(this)
        return START_STICKY
    }

    private fun startFtpServer() {
        try {
            val serverFactory = FtpServerFactory()
            val factory = ListenerFactory()
            factory.port = 2121
            serverFactory.addListener("default", factory.createListener())

            val user = BaseUser()
            user.name = "wedding"
            user.password = "password123"
            user.homeDirectory = filesDir.absolutePath + "/ftp"
            
            // FtpServer config...
            server = serverFactory.createServer()
            server?.start()
            Log.d("FTP", "FTP Server started on port 2121")
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
