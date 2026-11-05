# Android Companion App & Camera Setup Guide
**Live Wedding Gallery — Edge Ingestion Architecture**

This guide provides instructions for configuring the Android Companion App and pairing professional cameras (Sony, Canon, Nikon, Fujifilm) for automatic, real-time wireless photo transmission during live weddings.

---

## 1. Edge Ingestion Architecture Overview

The Android Companion App acts as an autonomous wireless ingestion bridge between professional cameras and the cloud backend.

```
+-------------------+                   +-----------------------------+                   +-----------------------+
|  Camera (WiFi)    |                   | Android Companion Device    |                   | Django Backend        |
|  - Sony Alpha     |  FTP over Wi-Fi   | - Local Hotspot or Venue AP |   HTTPS POST /    | - Render Web Service  |
|  - Canon EOS R    | ----------------> | - Embedded FTP Server (2121)| ----------------> | - Ephemeral Staging   |
|  - Nikon Z        |                   | - SQLite Ingestion Queue    |  HTTP 202 Ingest  | - Immediate ACK <200ms|
+-------------------+                   | - File Validator & Retain   |                   +-----------------------+
                                        +-----------------------------+
```

### Key Principles
1. **Zero Camera Tethering**: Camera connects wirelessly over standard FTP/FTPS.
2. **Local Queue Durability**: Photos written to internal Android storage (`ready_photos/`) are tracked in SQLite and **retained** until the cloud backend confirms `STATUS_COMPLETED`.
3. **Resilient Forwarding**: Network drops on cellular/Wi-Fi trigger exponential backoff retry without dropping photos.
4. **Instant Ingestion ACK**: The backend receives the chunked upload, validates file magic bytes, enqueues an `IngestionJob`, and acknowledges in $<200$ms.

---

## 2. Android Device Preparation

### 2.1 Hardware Requirements
- **OS**: Android 10+ (API level 29 or higher).
- **RAM**: Minimum 4 GB RAM (6 GB+ recommended).
- **Storage**: Minimum 32 GB free flash storage (high-speed UFS recommended for burst events).
- **Networking**: Dual-band Wi-Fi (5 GHz preferred for camera transmission) + 4G/5G LTE cellular connection.

### 2.2 Device System Settings
1. **Disable Battery Optimization**:
   - Go to `Settings -> Apps -> Live Wedding Companion -> Battery`.
   - Set to **Unrestricted** (prevents Android OS from killing the FTP server or HTTP upload background worker during long idle periods).
2. **Grant Permissions**:
   - Storage / All Files Access (`MANAGE_EXTERNAL_STORAGE` or Media permissions).
   - Location Permission (required by Android for Wi-Fi SSID discovery).
   - Notifications (required for ongoing Foreground Service status banner).
3. **Keep Wi-Fi Active During Sleep**:
   - Go to `Settings -> Wi-Fi -> Advanced -> Keep Wi-Fi on during sleep -> Always`.

---

## 3. Network Topologies

Choose one of two network topologies based on the venue:

### Topology A: Android Wi-Fi Hotspot (Recommended)
* **Configuration**: Android device enables portable Wi-Fi Hotspot (5 GHz, WPA2/WPA3). Camera connects directly to Android hotspot.
* **Advantages**: Fully self-contained, independent of venue infrastructure, mobile across ceremony and banquet areas.
* **Internet**: Android forwards uploads to Django over 4G/5G cellular data.

### Topology B: Venue / Production Router AP
* **Configuration**: Both Android device and Camera connect to a dedicated production 5 GHz Wi-Fi router.
* **Advantages**: Extended range, no hotspot throttling.
* **Internet**: Router WAN connection or Android mobile data.

---

## 4. Android Companion App Configuration

1. Launch the **Live Wedding Companion** app.
2. Navigate to **Settings**:
   - **Backend URL**: `https://live-wedding-gallery.onrender.com` (or your production domain).
   - **Wedding Slug**: e.g., `sandeep-prathyusha`.
   - **Photographer Token / Key**: Enter the authentication token generated from the Django Admin or photographer login.
   - **FTP Server Port**: `2121` (default non-root port).
   - **FTP Username**: `photographer`
   - **FTP Password**: `secure_wedding_pass_2026`
   - **Active Category / Folder**: Select active segment (`Ceremony`, `Reception`, `Guests`, `Decor`).
3. Tap **"Start Server"**:
   - The app launches a Foreground Service with a persistent status notification showing the active IP address (e.g., `192.168.43.1:2121`).

---

## 5. Camera FTP Setup Guides

### 5.1 Sony Alpha Series (A7 IV, A7R V, A1, A9 II)
1. Turn on Wi-Fi on the camera:
   - `Menu -> Network -> Wi-Fi -> Wi-Fi Connect -> On`.
   - Connect to the Android Hotspot SSID.
2. Configure FTP Transfer Function:
   - `Menu -> Network -> FTP Transfer Func. -> Server Setting -> Server 1`.
   - **Display Name**: `Android Companion`
   - **Destination**: Enter the Android IP displayed in the app (e.g., `192.168.43.1`).
   - **Port**: `2121`
   - **Secure Protocol**: `Off` (Plain FTP) or `On` (if FTPS certificate loaded).
   - **User**: `photographer`
   - **Password**: `secure_wedding_pass_2026`
   - **Directory**: `/`
3. Auto Transfer Setup:
   - `FTP Transfer Func. -> FTP Function -> On`.
   - `FTP Transfer Func. -> Target Group -> All Photos` or `Protected Only`.
   - `FTP Transfer Func. -> Auto Transfer -> On` (transfers each photo immediately as shot).
   - **Format**: Select `JPEG / HEIF only` (do NOT transfer RAW over live 5GHz FTP to minimize bandwidth and battery drain; keep RAW on SD card 1, write medium JPEG to SD card 2 for live transfer).

### 5.2 Canon EOS R Series (R5, R6 II, R3)
1. Network Settings:
   - `Menu -> Network -> Connection Settings -> Create new connection`.
   - Select **FTP transfer**.
   - Connect to Android Hotspot.
2. TCP/IP Configuration:
   - Set IP address to **Auto / DHCP**.
3. FTP Server Details:
   - **Target Server**: `192.168.43.1` (Android IP).
   - **Port**: `2121`
   - **Passive Mode**: `Enable`
   - **Login**: `photographer` / `secure_wedding_pass_2026`
   - **Target Directory**: Root (`/`)
4. Transfer Settings:
   - `Image Transfer -> Automatic Transfer -> Enable`.
   - Set **Transfer Size**: `Reduced JPEG` or `Standard JPEG`.

### 5.3 Nikon Z Series (Z6 II, Z8, Z9)
1. Network Menu:
   - Select **Connect to FTP server -> Create profile**.
   - Connection type: **Wi-Fi**. Select Android Hotspot.
2. Server Configuration:
   - **Server Type**: FTP.
   - **Host**: `192.168.43.1`
   - **Port**: `2121`
   - **Username / Password**: `photographer` / `secure_wedding_pass_2026`
   - **PASV Mode**: `On`
3. Options:
   - **Auto Send**: `ON`.
   - **Send File**: `JPEG only`.

---

## 6. Verification & Operating Protocol

### 6.1 Pre-Wedding Checklist
- [ ] Android device battery at 100% or connected to external battery pack (10,000mAh+).
- [ ] Dual SD cards configured in camera: **Slot 1 = RAW (backup), Slot 2 = JPEG (live transfer)**.
- [ ] Android companion app started; FTP service shows green active status.
- [ ] Take 2 test shots; confirm FTP icon flashes on camera display.
- [ ] Verify Android Companion App increments "Received" count.
- [ ] Verify backend `/admin/live` displays incoming upload and transitions to `COMPLETED`.
- [ ] Verify photo appears in real-time on guest gallery within 3–5 seconds.

### 6.2 Switching Folders / Events
- Before ceremony begins: Open Android app, switch dropdown from `Guests` to `Ceremony`.
- All subsequent camera uploads automatically carry the folder tag `Ceremony`.
- Frontend gallery tabs and real-time updates instantly filter accordingly.

---

## 7. Android Troubleshooting & Disaster Recovery

| Symptom | Cause | Resolution |
| :--- | :--- | :--- |
| **Camera shows "FTP Connection Error (Error 41 / 42)"** | IP address mismatch or FTP service stopped. | Check Android notification for current IP. Verify phone hotspot didn't reassign IP. Restart FTP service. |
| **Uploads queued on Android but not uploading to cloud** | Weak cellular data connection or invalid auth token. | Check signal. App automatically queues files in SQLite. Once LTE/5G restores, queue drains automatically. |
| **Android OS closes app after 20 minutes** | Battery optimization active. | Verify battery optimization is set to **Unrestricted** for the app. |
| **Storage full alert on Android** | Retained photos reached limit. | Go to app Settings -> Storage -> Verify safe threshold. Photos verified by backend as `COMPLETED` can be safely pruned. |
| **Need to recover missed photos** | Camera Wi-Fi was off during a burst. | On camera, select un-transferred photos -> tap `Protect` or `Transfer to FTP now`. Or tap **"Rescan & Re-queue"** in Android app. |

