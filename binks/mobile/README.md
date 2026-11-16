# Binks Cam — native phone app (Android + iOS)

A real native app (Capacitor shell) with the Binks UI bundled inside it.
It connects over Wi-Fi to the Binks server running on your computer
(`python binks.py start`). In the app: Settings → Binks server → enter the
`http://<computer-ip>:8099` address the server prints → Connect.

## Get the Android APK without installing anything
The repo has a GitHub Actions build (`.github/workflows/binks-apk.yml`).
GitHub → Actions → "Binks APK" → latest run → Artifacts → `binks-debug-apk`.
Unzip it, copy `app-debug.apk` to the phone, open it, allow "install unknown apps".

## Build it yourself
Needs Node 20+, JDK 21 and Android Studio (Android) or a Mac with Xcode (iOS).

    cd mobile
    npm install
    npm run android     # copies ../web, syncs, opens Android Studio -> Run
    npm run ios         # Mac only: opens Xcode -> pick your iPhone -> Run

Command-line APK: `cd android` then `.\gradlew.bat assembleDebug` (Windows) or
`./gradlew assembleDebug`. Output: `android/app/build/outputs/apk/debug/app-debug.apk`.

## iPhone notes
Apple only allows iOS builds from a Mac. A free Apple ID in Xcode installs the
app on your own iPhone for 7 days at a time; a paid developer account removes
that limit. No Mac: use the home-screen (PWA) install from MANUAL.md instead.

## What the native shell adds
- Installs as a real app with its own icon, no browser bar
- Camera permission for "use this phone as a camera"
- Snapshots go through the native share sheet (Save Image / Files)
- Plain-HTTP LAN access is enabled so it can reach `http://192.168.x.x`
