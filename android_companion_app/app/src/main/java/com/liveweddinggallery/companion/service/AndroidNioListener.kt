package com.liveweddinggallery.companion.service

import org.apache.ftpserver.DataConnectionConfiguration
import org.apache.ftpserver.FtpServerConfigurationException
import org.apache.ftpserver.impl.DefaultFtpHandler
import org.apache.ftpserver.impl.FtpHandler
import org.apache.ftpserver.impl.FtpIoSession
import org.apache.ftpserver.impl.FtpServerContext
import org.apache.ftpserver.ipfilter.MinaSessionFilter
import org.apache.ftpserver.ipfilter.SessionFilter
import org.apache.ftpserver.listener.nio.AbstractListener
import org.apache.ftpserver.listener.nio.FtpHandlerAdapter
import org.apache.ftpserver.listener.nio.FtpLoggingFilter
import org.apache.ftpserver.ssl.ClientAuth
import org.apache.ftpserver.ssl.SslConfiguration
import org.apache.mina.core.session.IdleStatus
import org.apache.mina.filter.codec.ProtocolCodecFilter
import org.apache.mina.filter.executor.ExecutorFilter
import org.apache.mina.filter.logging.MdcInjectionFilter
import org.apache.mina.filter.ssl.SslFilter
import org.apache.mina.transport.socket.SocketAcceptor
import org.apache.mina.transport.socket.nio.NioSocketAcceptor
import org.slf4j.LoggerFactory
import java.io.IOException
import java.net.InetSocketAddress
import java.security.GeneralSecurityException

/**
 * Custom NIO Listener for Android that replaces Apache FtpServer's crash-prone codec
 * with AndroidFtpServerProtocolCodecFactory to ensure multi-client and multi-photo
 * transfers never throw BufferUnderflowException.
 */
class AndroidNioListener(
    serverAddress: String?,
    port: Int,
    implicitSsl: Boolean,
    sslConfiguration: SslConfiguration?,
    dataConnectionConfig: DataConnectionConfiguration?,
    idleTimeout: Int,
    sessionFilter: SessionFilter?
) : AbstractListener(
    serverAddress,
    port,
    implicitSsl,
    sslConfiguration,
    dataConnectionConfig,
    idleTimeout,
    sessionFilter
) {
    private val log = LoggerFactory.getLogger(AndroidNioListener::class.java)
    private var acceptor: SocketAcceptor? = null
    private var address: InetSocketAddress? = null
    private var isSuspendedState: Boolean = false
    private val handler: FtpHandler = DefaultFtpHandler()
    private var serverContext: FtpServerContext? = null

    @Synchronized
    override fun start(context: FtpServerContext) {
        if (!isStopped) {
            throw IllegalStateException("Listener already started")
        }
        this.serverContext = context
        try {
            val nioAcceptor = NioSocketAcceptor(Runtime.getRuntime().availableProcessors())
            acceptor = nioAcceptor

            address = if (serverAddress != null) {
                InetSocketAddress(serverAddress, port)
            } else {
                InetSocketAddress(port)
            }

            nioAcceptor.isReuseAddress = true
            nioAcceptor.sessionConfig.readBufferSize = 8192
            nioAcceptor.sessionConfig.setIdleTime(IdleStatus.BOTH_IDLE, idleTimeout)
            nioAcceptor.sessionConfig.receiveBufferSize = 8192

            val mdcFilter = MdcInjectionFilter()
            nioAcceptor.filterChain.addLast("mdcFilter", mdcFilter)

            val filter = sessionFilter
            if (filter != null) {
                nioAcceptor.filterChain.addLast("sessionFilter", MinaSessionFilter(filter))
            }

            nioAcceptor.filterChain.addLast(
                "threadPool",
                ExecutorFilter(context.threadPoolExecutor)
            )

            // CRITICAL: Crash-proof thread-safe codec for Android
            nioAcceptor.filterChain.addLast(
                "codec",
                ProtocolCodecFilter(AndroidFtpServerProtocolCodecFactory())
            )

            nioAcceptor.filterChain.addLast("mdcFilter2", mdcFilter)
            nioAcceptor.filterChain.addLast("logger", FtpLoggingFilter())

            if (isImplicitSsl) {
                val ssl = sslConfiguration
                val sslFilter = try {
                    SslFilter(ssl?.sslContext)
                } catch (e: GeneralSecurityException) {
                    throw FtpServerConfigurationException("SSL could not be initialized, check configuration", e)
                }
                if (ssl != null) {
                    if (ssl.clientAuth == ClientAuth.NEED) {
                        sslFilter.setNeedClientAuth(true)
                    } else if (ssl.clientAuth == ClientAuth.WANT) {
                        sslFilter.setWantClientAuth(true)
                    }
                    if (ssl.enabledCipherSuites != null) {
                        sslFilter.setEnabledCipherSuites(ssl.enabledCipherSuites)
                    }
                }
                nioAcceptor.filterChain.addFirst("sslFilter", sslFilter)
            }

            handler.init(context, this)
            nioAcceptor.handler = FtpHandlerAdapter(context, handler)

            try {
                nioAcceptor.bind(address)
            } catch (e: IOException) {
                val msg = "Failed to bind to address $address, check configuration"
                throw FtpServerConfigurationException(msg, e)
            }

            updatePort()
        } catch (e: RuntimeException) {
            stop()
            throw e
        }
    }

    private fun updatePort() {
        val localAddr = acceptor?.localAddress as? InetSocketAddress
        if (localAddr != null) {
            setPort(localAddr.port)
        }
    }

    @Synchronized
    override fun stop() {
        try {
            acceptor?.unbind()
            acceptor?.dispose()
            acceptor = null
            serverContext = null
        } catch (e: Exception) {
            log.error("Failed to stop AndroidNioListener", e)
        }
    }

    override fun isStopped(): Boolean = acceptor == null

    override fun isSuspended(): Boolean = isSuspendedState

    @Synchronized
    override fun resume() {
        val a = acceptor
        val addr = address
        if (a != null && isSuspendedState && addr != null) {
            try {
                log.debug("Resuming listener")
                a.bind(addr)
                log.debug("Listener resumed")
                updatePort()
                isSuspendedState = false
            } catch (e: IOException) {
                log.error("Failed to resume listener", e)
            }
        }
    }

    @Synchronized
    override fun suspend() {
        val a = acceptor
        if (a != null && !isSuspendedState) {
            log.debug("Suspending listener")
            a.unbind()
            isSuspendedState = true
            log.debug("Listener suspended")
        }
    }

    @Synchronized
    override fun getActiveSessions(): Set<FtpIoSession> {
        val a = acceptor ?: return emptySet()
        val sessions = a.managedSessions
        val result = HashSet<FtpIoSession>()
        val ctx = serverContext
        for (session in sessions.values) {
            result.add(FtpIoSession(session, ctx))
        }
        return result
    }
}

