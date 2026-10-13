"""Pico -> Mac through libusb instead of Apple's /dev/cu.usbserial node.
    .venv/bin/python libusb_rx_test.py MEGABYTES SCLK_MHZ H L"""
import sys
from sustained4_test import run_tx_libusb

print(run_tx_libusb(float(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])))
