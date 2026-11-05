package com.liveweddinggallery.companion.service

import org.apache.mina.core.buffer.IoBuffer
import org.apache.mina.core.session.IoSession
import org.apache.mina.filter.codec.ProtocolCodecFactory
import org.apache.mina.filter.codec.ProtocolDecoder
import org.apache.mina.filter.codec.ProtocolEncoder
import org.apache.mina.filter.codec.ProtocolEncoderAdapter
import org.apache.mina.filter.codec.ProtocolEncoderOutput
import org.apache.mina.filter.codec.textline.TextLineDecoder
import java.nio.charset.StandardCharsets

/**
 * Thread-safe FTP response encoder for Android.
 *
 * Apache FtpServer's default FtpResponseEncoder uses a single static java.nio.charset.CharsetEncoder
 * which is NOT thread-safe. When multiple FTP transfers or commands occur concurrently,
 * Android's CharsetEncoderICU throws java.nio.BufferUnderflowException and crashes the process.
 *
 * This implementation encodes directly via UTF-8 byte arrays without stateful shared encoders,
 * guaranteeing 100% thread safety for batch and parallel transfers.
 */
class AndroidFtpResponseEncoder : ProtocolEncoderAdapter() {
    override fun encode(session: IoSession, message: Any, out: ProtocolEncoderOutput) {
        val value = message.toString()
        val bytes = value.toByteArray(StandardCharsets.UTF_8)
        val buf = IoBuffer.allocate(bytes.size, false)
        buf.put(bytes)
        buf.flip()
        out.write(buf)
    }
}

/**
 * Custom ProtocolCodecFactory utilizing the crash-proof AndroidFtpResponseEncoder.
 */
class AndroidFtpServerProtocolCodecFactory : ProtocolCodecFactory {
    private val decoder = TextLineDecoder(StandardCharsets.UTF_8)
    private val encoder = AndroidFtpResponseEncoder()

    override fun getDecoder(session: IoSession?): ProtocolDecoder = decoder
    override fun getEncoder(session: IoSession?): ProtocolEncoder = encoder
}

