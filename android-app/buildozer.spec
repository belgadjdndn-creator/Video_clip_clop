[app]

# App identity
title = Smart Shorts
package.name = smartshorts
package.domain = org.smartshorts

# Source
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
source.include_patterns = assets/*,smart_shorts.py

# Version
version = 1.0.0

# Requirements — keep in sync with magic comments in main.py
requirements = python3,kivy,requests,certifi,urllib3,android,yt_dlp,websockets,mutagen,pycryptodomex

# Android build configuration
android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.archs = arm64-v8a

# Permissions
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,FOREGROUND_SERVICE,RECEIVE_BOOT_COMPLETED,WAKE_LOCK,REQUEST_INSTALL_PACKAGES

# Orientation — portrait only (matches on_start lock in main.py)
orientation = portrait

# Fullscreen (hides status bar)
fullscreen = 0

# App icon & presplash (place 512×512 PNG files in assets/)
icon.filename = assets/icon.png
presplash.filename = assets/presplash.png
presplash.color = #0f0f12

# Java / gradle
android.gradle_dependencies =
android.java_version = 17
android.add_jars =

# Enable AndroidX
android.enable_androidx = True

# p4a bootstrap — service (allows background threads + WebView access)
p4a.bootstrap = sdl2

# Private app files dir
android.private_storage = True

# Logcat filter (set to INFO to suppress DEBUG noise in production builds)
android.logcat_filters = *:S python:D

# Build output directory
bin.dir = ./bin

[buildozer]

# Log level: 0=error, 1=info, 2=debug
log_level = 1

# Warn on build warnings
warn_on_root = 1
