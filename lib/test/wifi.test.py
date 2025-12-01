import network
import time

SSID = ""
PASSWORD = ""

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
print("Wi-Fi active:", wlan.active())

if not wlan.isconnected():
    print("Connecting to", SSID, "...")
    wlan.connect(SSID, PASSWORD)
    while not wlan.isconnected():
        print("Waiting for connection...")
        time.sleep(0.5)

print("Connected!")
print("ifconfig:", wlan.ifconfig())
