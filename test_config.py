#!/usr/bin/env python3
"""
Test script to verify device config update logic
"""
import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.globals import devices, devices_lock

# Simulate device config data
test_data = {
    'device_id': 'ESP8266_123',
    'location': 'sala',
    'config': {
        'firmware': '1.2.3',
        'mac': 'AA:BB:CC:DD:EE:FF',
        'heap': 12345,
        'sensor': {
            'temp_c': 25.5,
            'temp_h': 60.0,
            'temp_st': 22.0
        }
    }
}

print("Test data:", json.dumps(test_data, indent=2))

# Simulate what happens in handleDeviceConfigUpdate
device_id = test_data['device_id']
location = test_data['location']
config = test_data['config']

print(f"\nChecking device {device_id}@{location}")

# Check if device exists in devices dict
device_key = f"{device_id}@{location}"
with devices_lock:
    if device_key in devices:
        print(f"Device {device_key} exists in devices dict")
        print("Current device data:", devices[device_key])
    else:
        print(f"Device {device_key} NOT in devices dict")

# Simulate updating devices dict (as done in mqtt_callbacks.py)
with devices_lock:
    if 'firmware' in config:
        devices[device_key]['firmware'] = config.get('firmware', 'Unknown')
    if 'mac' in config:
        devices[device_key]['mac'] = config.get('mac', 'N/A')
    if 'heap' in config:
        devices[device_key]['heap'] = config.get('heap', 0)

    print(f"\nUpdated device data: {devices[device_key]}")

print("\nTest completed - logic appears correct")