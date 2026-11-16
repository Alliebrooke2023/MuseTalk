# Binks Cam — native phone app (Android + iOS)

A real native app (Capacitor shell) with the Binks UI bundled inside it.
It connects over Wi-Fi to the Binks server running on your computer
(`python binks.py start`). In the app: Settings → Binks server → enter the
`http://<computer-ip>:8099` address the server prints → Connect.

## Get the Android APK without installing anything
The repo has a GitHub Actions build (`.github/workflows/binks-apk.yml`).
GitHub → Actions → "Binks apps" → latest run → Artifacts → `binks-debug-apk`.
Unzip it, copy `app-debug.apk` to the phone, open it, allow "install unknown apps".

## Build it yourself
Needs Node 20+, JDK 21 and Android Studio (Android) or a Mac with Xcode (iOS).

    cd mobile
    npm install
    npm run android     # copies ../web, syncs, opens Android Studio -> Run
    npm run ios         # Mac only: opens Xcode -> pick your iPhone -> Run

Command-line APK: `cd android` then `.\gradlew.bat assembleDebug` (Windows) or
`./gradlew assembleDebug`. Output: `android/app/build/outputs/apk/debug/app-debug.apk`.

## iPhone
Apple does not allow installing an app straight from a file the way Android
does. The cloud build produces an **unsigned** `Binks-unsigned.ipa`; you sign it
with your own free Apple ID while installing:

1. GitHub -> Actions -> "Binks apps" -> latest run -> Artifacts ->
   `binks-unsigned-ipa`. Download and unzip to get `Binks-unsigned.ipa`.
2. On a Windows PC or Mac, install **Sideloadly** (or AltStore) and iTunes/Apple
   Devices so the computer can see the phone.
3. Plug in the iPhone, drop the `.ipa` into Sideloadly, enter your Apple ID, Start.
4. iPhone: Settings -> General -> VPN & Device Management -> trust your Apple ID.
   iOS 16+: also Settings -> Privacy & Security -> Developer Mode -> On.
5. Open Binks, allow Local Network access, then Settings -> Binks server -> Connect.

A free Apple ID signature lasts 7 days, then re-run step 3 (your settings stay).
A paid developer account lasts a year. With a Mac you can skip all this:
`npm run ios`, pick your iPhone in Xcode, Run.

No computer at all: open the server address in Safari -> Share -> Add to Home
Screen. Same UI, no signing, never expires.

## What the native shell adds
- Installs as a real app with its own icon, no browser bar
- Camera permission for "use this phone as a camera"
- Snapshots go through the native share sheet (Save Image / Files)
- Plain-HTTP LAN access is enabled so it can reach `http://192.168.x.x`
