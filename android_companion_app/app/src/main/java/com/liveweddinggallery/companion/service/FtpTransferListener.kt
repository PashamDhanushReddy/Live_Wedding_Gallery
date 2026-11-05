package com.liveweddinggallery.companion.service

import com.liveweddinggallery.companion.util.CompanionLogger
import org.apache.ftpserver.ftplet.DefaultFtplet
import org.apache.ftpserver.ftplet.FtpRequest
import org.apache.ftpserver.ftplet.FtpSession
import org.apache.ftpserver.ftplet.FtpletResult
import java.io.File

class FtpTransferListener(
    private val baseFtpDir: File,
    private val onFileUploaded: (File) -> Unit
) : DefaultFtplet() {

    override fun onConnect(session: FtpSession?): FtpletResult {
        val clientIp = session?.clientAddress?.address?.hostAddress ?: "Unknown"
        CompanionLogger.i(
            event = "FTP_CLIENT_CONNECT",
            status = "CONNECTED",
            details = "Camera connected from $clientIp"
        )
        return FtpletResult.DEFAULT
    }

    override fun onDisconnect(session: FtpSession?): FtpletResult {
        val clientIp = session?.clientAddress?.address?.hostAddress ?: "Unknown"
        CompanionLogger.i(
            event = "FTP_CLIENT_DISCONNECT",
            status = "DISCONNECTED",
            details = "Camera disconnected from $clientIp"
        )
        return FtpletResult.DEFAULT
    }

    override fun onUploadStart(session: FtpSession?, request: FtpRequest?): FtpletResult {
        val filename = request?.argument ?: "Unknown"
        CompanionLogger.i(
            event = "FTP_TRANSFER_START",
            filename = filename,
            status = "RECEIVING",
            details = "Camera started pushing photo"
        )
        return FtpletResult.DEFAULT
    }

    override fun onUploadEnd(session: FtpSession?, request: FtpRequest?): FtpletResult {
        val filename = request?.argument
        if (!filename.isNullOrEmpty()) {
            val cleanName = File(filename).name
            val uploadedFile = File(baseFtpDir, cleanName)

            CompanionLogger.i(
                event = "FTP_TRANSFER_COMPLETE",
                filename = cleanName,
                status = "RECEIVED",
                details = "Transfer completed cleanly. Size: ${if (uploadedFile.exists()) uploadedFile.length() else -1} bytes"
            )

            if (uploadedFile.exists()) {
                try {
                    onFileUploaded(uploadedFile)
                } catch (e: Exception) {
                    CompanionLogger.e(
                        event = "FTP_CALLBACK_ERROR",
                        filename = cleanName,
                        details = "Error notifying onFileUploaded: ${e.message}",
                        throwable = e
                    )
                }
            }
        }
        return FtpletResult.DEFAULT
    }
}

