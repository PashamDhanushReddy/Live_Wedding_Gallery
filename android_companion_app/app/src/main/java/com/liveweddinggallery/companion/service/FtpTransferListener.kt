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
        UploadManager.clearActiveSessionTransfers(session?.sessionId?.toString())
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
        resolveFtpFile(session, request?.argument)?.let { targetFile ->
            UploadManager.markFtpTransferStarted(session?.sessionId?.toString(), targetFile)
        }
        CompanionLogger.i(
            event = "FTP_TRANSFER_START",
            filename = filename,
            status = "RECEIVING",
            details = "Camera started pushing photo"
        )
        return FtpletResult.DEFAULT
    }

    private fun resolveFtpFile(session: FtpSession?, rawArg: String?): File? {
        if (rawArg.isNullOrEmpty()) return null
        return try {
            val baseCanonical = baseFtpDir.canonicalFile
            val virtualPath = try {
                session?.fileSystemView?.getFile(rawArg)?.absolutePath
            } catch (_: Exception) {
                null
            } ?: run {
                val cwd = session?.fileSystemView?.workingDirectory?.absolutePath ?: "/"
                val cleanedArg = rawArg.replace('\\', '/')
                if (cleanedArg.startsWith("/")) cleanedArg else "${cwd.trimEnd('/')}/$cleanedArg"
            }

            val relativePath = virtualPath.replace('\\', '/').trimStart('/')
            val candidate = File(baseCanonical, relativePath).canonicalFile
            if (candidate.path.startsWith(baseCanonical.path + File.separator) || candidate == baseCanonical) {
                candidate
            } else {
                File(baseCanonical, File(rawArg).name)
            }
        } catch (_: Exception) {
            File(baseFtpDir, File(rawArg).name)
        }
    }

    override fun onUploadUniqueStart(session: FtpSession?, request: FtpRequest?): FtpletResult {
        resolveFtpFile(session, request?.argument)?.let { targetFile ->
            UploadManager.markFtpTransferStarted(session?.sessionId?.toString(), targetFile)
        }
        return FtpletResult.DEFAULT
    }

    override fun onUploadUniqueEnd(session: FtpSession?, request: FtpRequest?): FtpletResult {
        return onUploadEnd(session, request)
    }

    override fun onUploadEnd(session: FtpSession?, request: FtpRequest?): FtpletResult {
        val filename = request?.argument
        if (!filename.isNullOrEmpty()) {
            val uploadedFile = resolveFtpFile(session, filename) ?: File(baseFtpDir, File(filename).name)
            val cleanName = uploadedFile.name
            UploadManager.markFtpTransferFinished(session?.sessionId?.toString(), uploadedFile)

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

