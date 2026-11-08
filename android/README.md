# Android pilot

Native Kotlin/Compose, minAndroid8(API26), target36. Meshtastic protobuf inputs pinned85f3f4357946a52daa5310285476d2dffb137c7b, included generated Java-lite; no altered firmware. Android SQLite payloads/contacts protected with AES-GCM using Android Keystore; routing/times/states remain metadata. Losing the key may make history unreadable.

## Build

SDKplatform36/buildtools36, Gradle9.8, Java17+ (verified with Java25). Initial dependencies need internet; messaging does not. From this directory:

```
ANDROID_HOME=/path/to/sdk ./gradlew --no-daemon --max-workers=1 testDebugUnitTest assembleDebug
```

Use local nonsynced build/cache directories and adequate free space. Output app/build/outputs/apk/debug/app-debug.apk uses a test certificate. A production release needs separate signing/distribution setup; no credentials or private signing keys included here. Supplied APK signature was verified.

## Use

Configure a locally lawful candidateEU_868 profile, dutycycleoverrideoff, private channel, MQTT/uplink/downlinkoff using official Meshtastic client. Disconnect it, install this APK, allow Bluetooth and select radio. Explicit local RF-review checkbox permits queue attempts; it is not regulator clearance. App reads config and blocks sends unless candidate/private settings are reported. Bluetooth foreground service runs only after explicit connection. Force-stop ends it; there is no silent boot-autostart or cloud push.

Outgoing texts including ID are200UTF8bytes; incoming accepts233. Persist reservation before BLE write; uncertain writes/restarts pause. Radio ACK is never human receipt. HelpTTL1h does not close incident. Openhelp and personally verified receipts/closures have separate controls. GPS is opt-in insertion into reviewed draft, last-known GPS must be fresh within5min. Notification previews exclude message content.

Karta starts empty. Prepare a licensed MapLibre style/region while online, include attribution and verify full offline rendering before reliance. No paid default tiles/APIkeys, map data or shelter points are bundled. Priprema contains dated source-attributed guide drafts. Baza exports a separate user-consented public radiogramJSON to a selected document; this does not transmitHF or import private conversations automatically. Station operator independently reviews exact text and evidence.

## Evidence

7JVMtests passed; debugAPK compiled and signature verified. No Android device/emulator/BLE radio was available. Tests under src/androidTest require actual hardware/emulator (`./gradlew connectedDebugAndroidTest`) and were not executed. BLE reliability, background behavior, missed-message replay, maps offline and battery targets require the field/device matrix; compilation does not prove them. iPhone uses the official free client plus documents, no customiOS app.
