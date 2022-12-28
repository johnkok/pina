import network
import time
import socket
import _thread
import struct
from time import sleep
from machine import Pin
from machine import Timer

# WiFi Access Point data
SSID = "SSID"
PASSWORD = "PSW"

# INA I2C Registers
INA_ADDRESS    = 0x40
INA_CONFIG     = 0x00
INA_ADC_CONFIG = 0x01
INA_SHUNT_CAL  = 0x02
INA_VBUS       = 0x05
INA_CURRENT    = 0x07
INA_CHARGE     = 0x0A

# PIO Register
GPIOA = const(0x48000000)
GPIO_BSRR = const(0x18)
GPIO_IDR = const(0x10)

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
def tcpserver(ip):
    global tx_enable
    global connected
    global connection

    # Create a TCP/IP socket and bind it
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #tcp socket
    server_address = (ip, 5555)
    print ('Server starting up on %s port %s' % server_address)
    sock.bind(server_address)
    # Listen for incoming connections
    sock.listen(5)
    while True:
        # Wait for a connection
        print ('Server waiting for a connection...')
        connection, client_address = sock.accept()
        print('Connected')
        connected = True
        try:
            led.value(1)
            print ('Server connection from', client_address)
            # Receive the data in small chunks and process it
            while True:
                data = connection.recv(16)
                if data:
                    string = data.decode('ascii')
                    if string == 'version':
                        connection.write('PINA')
                    elif string == 'get':
                        tx_enable = True
                    elif string == 'close':
                        tx_enable = False
                    elif string == 'samplerate':
                        connection.write(rate)
                    elif string == 'sampleunit':
                        connection.write(unit)
                    elif string == 'memalloc':
                        connection.write(malloc)
                    elif string == 'exit':
                        tx_enable = False
                        connection.close()
                        break; # Disconnect
                    else:
                        print('Unknown data {}'.format(data))
                elif data < 0:
                    print ('no more data from', client_address)
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
    
    i2c = machine.I2C(0, scl=machine.Pin(17), sda=machine.Pin(16))
    devices = i2c.scan()
    if devices:
        for d in devices:
            if d == INA_ADDRESS:
                print("INA228 found!")
            else:
                print("No INA228 found!")
                return
    #setup ina 228
    i2c.writeto_mem(INA_ADDRESS, INA_CONFIG, bytearray([0x00,0x00]))
    i2c.writeto_mem(INA_ADDRESS, INA_ADC_CONFIG, bytearray([0xFB, 0x6A]))
    # R = 0.2 Ohm -> 163.84 mV = 819.2mA MAX -> 1,5625uA MIN
    # SHUNT_CAL = 13107.2 x 106 x CURRENT_LSB x RSHUNT
    # CURRENT_LSB = Maximum Expected Current / 2^19
    i2c.writeto_mem(INA_ADDRESS, INA_SHUNT_CAL, bytearray([0x10, 0x00]))
    
    while 1:
        if new_data == False:
            data = i2c.readfrom_mem(0x40, INA_CURRENT, 3)
            value = ((data[0] & 0x7F) << 12) + (data[1] << 4) + data[2] >> 4
            if (data[0] & 0x80):
                value = -value
            print('Current: {} mA'.format(value * 1.5625 / 1000.0))
        
            data = i2c.readfrom_mem(0x40, INA_VBUS, 3)
            value = (data[0] << 12) + (data[1] << 4) + (data[2] >> 4)
            print('Voltage: {} V'.format((value * 195.3125) / 1000000.0))
        
            data = i2c.readfrom_mem(0x40, INA_VBUS, 3)
            print('Voltage2: {} V'.format((value * 195.3125) / 1000000.0))
        
        
            data = i2c.readfrom_mem(0x40, INA_CHARGE, 5)
            value = ((data[0] & 0x80) << 24) + (data[1] << 20) + (data[2] << 16) + (data[3] << 8) + (data[4])
            print('Charge: {} V'.format((value * 195.3125) / 1000000.0))
        
        sleep(0.01)

# Timer callback
def timerCallback(t):
    global vbus
    global isense
    global new_data
    global ch_id
    global connected
    global connection
    
    if connected:
        print("ok")
        #ina228()
        new_data = True
        if new_data:     
            gpio =  0x11111 #(machine.mem32[GPIOA + GPIO_IDR] >> 8) & 0x000000FF
            packet = bytearray(struct.pack("iffi", ch_id, isense, vbus, gpio))
            new_data = False
            connection.send(packet)

############
#   main   #
############
try:
    # Try to connect to WiFi AP
    ip = connect()  # Prepare WiFi connection
    # Should be connected now
    x =  _thread.start_new_thread(tcpserver, (ip,))  # TCP Server thread
    tim.init(mode=Timer.PERIODIC, period=1000, callback=timerCallback)

except KeyboardInterrupt:
    machine.reset()
    print("Reset done!")

print("Init done!")

while 1:
   sleep(5)
