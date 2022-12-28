import network
import time
import socket
import select
import _thread
import struct
from time import sleep
from machine import Pin
from machine import Timer

# WiFi Access Point data
SSID = ""
PASSWORD = ""

# INA I2C Registers
INA_ADDRESS    = 0x40
INA_CONFIG     = 0x00
INA_ADC_CONFIG = 0x01
INA_SHUNT_CAL  = 0x02
INA_VBUS       = 0x05
INA_CURRENT    = 0x07
INA_CHARGE     = 0x0A

# Init hardware
led = machine.Pin("LED", machine.Pin.OUT)
tim = machine.Timer()

led.value(0)

# Global varibles
tx_enable = False
connected = False
new_data = False

rate = 10
unit = 1
malloc = 16

ch_id: int
gpio: int
vbus: float
isense: float

ch_id = 1
isense = 0.0
vbus = 0.0

# WiFi connection handling
def connect(): #WIFI connection
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    while wlan.isconnected() == False:
        print('Waiting for connection...')
        sleep(1)
    ip = wlan.ifconfig()[0]
    print(f'Connected on {ip}')
    return ip

# TCP Server handler
def tcpserver():
    global tx_enable
    global connected
    global connection

    try:
        led.value(1)

        # Receive the data in small chunks and process it
        while True:
            data = connection.readline()
            if data:
                string = data.decode('ascii')
                print('Rx data: ', string)
                if string.startswith('version'):
                    connection.send('PINA')
                elif string.startswith('get'):
                    tx_enable = True
                elif string.startswith('close'):
                    tx_enable = False
                elif string.startswith('samplerate'):
                    connection.send(chr(rate))
                elif string.startswith('sampleunit'):
                    connection.send(chr(unit))
                elif string.startswith('memalloc'):
                    connection.send(chr(malloc))
                elif string.startswith('exit'):
                    tx_enable = False
                    connection.close()
                    break # Disconnect
                else:
                    print('Unknown data {}'.format(data))
            else:
                print ('no data')
                break
    finally:
        # Clean up the connection
        connection.close()
        connected = False
        led.value(0)
        print("Connection closed!")

# INA228 Driver
def ina228():
    global vbus
    global isense
    global new_data
    global i2c

    if new_data == False:
        data = i2c.readfrom_mem(0x40, INA_CURRENT, 3)
        value = ((data[0] & 0x7F) << 12) + (data[1] << 4) + data[2] >> 4
        if (data[0] & 0x80):
            value = -value
        isense = value * 1.5625 / 1000.0 / 1000.0
        #print('Current: {} mA'.format(isense))

        data = i2c.readfrom_mem(0x40, INA_VBUS, 3)
        value = (data[0] << 12) + (data[1] << 4) + (data[2] >> 4)
        vbus = (value * 195.3125) / 1000000.0
        #print('Voltage: {} V'.format(vbus))

        data = i2c.readfrom_mem(0x40, INA_CHARGE, 5)
        value = ((data[0] & 0x80) << 24) + (data[1] << 20) + (data[2] << 16) + (data[3] << 8) + (data[4])
        #print('Charge: {} V'.format((value * 195.3125) / 1000000.0))

        new_data = True

# Timer callback
def timerCallback(t):
    global vbus
    global isense
    global new_data
    global ch_id
    global connected
    global connection
    global gpio
    global IO0
    global IO1
    global IO2
    global IO3
    global IO4
    global IO5
    global IO6
    global IO7

    if connected and tx_enable:
        ina228()
        if new_data:
            gpio = IO0.value() + IO1.value()*2 + IO2.value()*4 + IO3.value()*8 + IO4.value()*16 + IO5.value()*32 + IO6.value()*64 + IO7.value()*128
            packet = bytearray(struct.pack("iffi", ch_id, isense, vbus, gpio))
            connection.write(packet)
            print(gpio)
            print(IO0.value())
            new_data = False

############
#   main   #
############
try:
    # Try to connect to WiFi AP
    ip = connect()  # Prepare WiFi connection
    # Should be connected to WiFi now

    # Connect to INA228
    i2c = machine.I2C(0, scl=machine.Pin(17), sda=machine.Pin(16))
    devices = i2c.scan()
    if devices:
        for d in devices:
            if d == INA_ADDRESS:
                print("INA228 found!")

                #setup ina 228
                i2c.writeto_mem(INA_ADDRESS, INA_CONFIG, bytearray([0x00,0x00]))
                i2c.writeto_mem(INA_ADDRESS, INA_ADC_CONFIG, bytearray([0xFB, 0x6A]))
                # R = 0.2 Ohm -> 163.84 mV = 819.2mA MAX -> 1,5625uA MIN
                # SHUNT_CAL = 13107.2 x 106 x CURRENT_LSB x RSHUNT
                # CURRENT_LSB = Maximum Expected Current / 2^19
                i2c.writeto_mem(INA_ADDRESS, INA_SHUNT_CAL, bytearray([0x10, 0x00]))

            else:
                print("No INA228 found!")
                exit

    # Setup GPIOs
    IO0 = Pin(8, Pin.IN)
    IO1 = Pin(9, Pin.IN)
    IO2 = Pin(10, Pin.IN)
    IO3 = Pin(11, Pin.IN)
    IO4 = Pin(12, Pin.IN)
    IO5 = Pin(13, Pin.IN)
    IO6 = Pin(14, Pin.IN)
    IO7 = Pin(15, Pin.IN)

    # Create data acq timer
    tim.init(mode=Timer.PERIODIC, period=200, callback=timerCallback)

    # Create a TCP/IP socket and bind it
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #tcp socket
    server_address = socket.getaddrinfo('0.0.0.0', 5555)[0][-1]
    print ('Server starting up on %s port %s' % server_address)
    sock.bind(server_address)

    # Listen for incoming connections
    sock.listen(5)
    while True:
        # Wait for a connection
        print ('Server waiting for a connection...')
        connection, client_address = sock.accept()
        connected = True
        print ('Server connection from', client_address)

        #_thread.start_new_thread(tcpserver, ())  # TCP Server thread
        tcpserver()


except KeyboardInterrupt:
    machine.reset()
    print("Reset done!")

print("Exit!")
