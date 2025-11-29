import network
import socket
import json
import time

SSID = "SUPERONLINE_Wi-Fi_3252"
PASSWORD = "3HcTsZPUXYx5"

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(SSID, PASSWORD)
        while not wlan.isconnected():
            time.sleep(0.5)
    print("ifconfig:", wlan.ifconfig())
    return wlan

def start_server():
    addr = socket.getaddrinfo("0.0.0.0", 8266)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print("Waiting for client...")
    client, remote_addr = s.accept()
    print("Client connected from:", remote_addr)
    return client

wlan = connect_wifi()
client = start_server()

# Sonsuz döngü: sahte ama Flutter ile uyumlu data paketi gönder
while True:
    data_packet = {
        "red": [],
        "ir": [],
        "acq_freq": 100,
        "hr": {
            "value": 72,
            "peaks_index": []
        },
        "spo2": 98.5,
        "body_temp": 36.7
    }

    payload = json.dumps(data_packet) + "\n"
    try:
        client.send(payload.encode("utf-8"))
        print("Sent packet")
    except OSError as e:
        print("Send error:", e)
        client = start_server()
        continue

    time.sleep(1)
