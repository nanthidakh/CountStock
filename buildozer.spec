[app]

title = HWKCountStock

package.name = CountStockV1

package.domain = org.example

icon.filename = %(source.dir)s/barcode.png

version = 1.2

source.dir = .

source.include_exts = py,png,jpg,kv,atlas,ttf,json

requirements = python3,kivy,kivymd,requests,pyjnius

p4a.branch = release-2024.01.21

android.api = 28

android.minapi = 23

android.ndk = 25b

android.accept_sdk_license = True

#android.archs = armeabi-v7a,arm64-v8a
android.archs = armeabi-v7a

#android.enable_androidx = False
android.orientation = portrait

android.permissions = INTERNET, ACCESS_NETWORK_STATE, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE