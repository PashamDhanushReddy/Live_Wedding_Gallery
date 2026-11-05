package com.liveweddinggallery.companion.util

import java.net.Inet4Address
import java.net.NetworkInterface

object NetworkUtils {
    /**
     * Resolves the active IPv4 address from network interfaces.
     * Works seamlessly for both Wi-Fi Station mode and Mobile Hotspot (AP) mode.
     */
    fun getActiveWifiOrHotspotIp(): String {
        try {
            val interfaces = NetworkInterface.getNetworkInterfaces()
            val candidateIps = mutableListOf<String>()

            while (interfaces.hasMoreElements()) {
                val iface = interfaces.nextElement()
                if (iface.isLoopback || !iface.isUp) continue

                val name = iface.name.lowercase()
                val isWireless = name.contains("wlan") || name.contains("ap") || name.contains("rndis") || name.contains("swlan")

                val addresses = iface.inetAddresses
                while (addresses.hasMoreElements()) {
                    val addr = addresses.nextElement()
                    if (!addr.isLoopbackAddress && addr is Inet4Address) {
                        val host = addr.hostAddress ?: ""
                        if (host.isNotEmpty() && !host.startsWith("127.")) {
                            if (isWireless) {
                                return host // Highest priority: Wi-Fi or Hotspot interface
                            }
                            candidateIps.add(host)
                        }
                    }
                }
            }
            if (candidateIps.isNotEmpty()) {
                return candidateIps.first()
            }
        } catch (_: Exception) {}
        return ""
    }
}

