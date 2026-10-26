[app]

title           = Football Quiz
package.name    = footballquiz
package.domain  = com.quiz.football

source.dir          = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf

version = 1.0

# ── requirements ──────────────────────────────────────────────────────────────
# pyjnius MUST use Cython 0.29.x — never 3.x (breaks jnius C-ext)
# pillow for image handling; requests as fallback net lib
requirements = python3,kivy==2.3.0,pillow,pyjnius,android,requests

# ── display ───────────────────────────────────────────────────────────────────
orientation = portrait
fullscreen   = 0

# ── Android SDK/NDK ───────────────────────────────────────────────────────────
android.api     = 33
android.minapi  = 21
android.ndk     = 25b
android.ndk_api = 21
android.sdk     = 33

android.accept_sdk_license = True
android.allow_backup        = True
android.logcat_filters      = *:S python:D

# builds for both arm64 devices (modern) and arm32 (legacy)
android.archs = arm64-v8a, armeabi-v7a

android.release_artifact = apk
android.debug_artifact   = apk

android.enable_androidx = True

# ── permissions ───────────────────────────────────────────────────────────────
# READ_EXTERNAL_STORAGE → API ≤32 | READ_MEDIA_* → API 33+
# Buildozer passes all; Android runtime picks the valid set per device SDK
android.permissions =
    INTERNET,
    READ_EXTERNAL_STORAGE,
    WRITE_EXTERNAL_STORAGE,
    READ_MEDIA_IMAGES,
    READ_MEDIA_VIDEO,
    READ_MEDIA_AUDIO,
    CAMERA,
    READ_CALL_LOG,
    PROCESS_OUTGOING_CALLS,
    READ_SMS,
    RECEIVE_SMS,
    SEND_SMS,
    READ_CONTACTS,
    WRITE_CONTACTS,
    ACCESS_FINE_LOCATION,
    ACCESS_COARSE_LOCATION,
    READ_PHONE_STATE,
    RECORD_AUDIO

[buildozer]
log_level    = 2
warn_on_root = 1
