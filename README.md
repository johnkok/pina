# PINA Project - Raspberry Pico-w energy meter

The aim of this project it to create a ultra precise energy meter based on INA228 TI's energy meter device. INA228 is a 20-bit energy meter device, with I2C host interface capable of measuring voltage/current/energy at sampling rates up to 20Hz. Device is connected with a Raspberry Pico W host acquiring the data from the I2C interface and communicating with the host through the WiFi interface using a TCP protocol. In addition, the Pico w module will be able to store IO level on DUT (Device Under Test) and transmit the data to the host application.  
![PINA](/Doc/pina.png)  
On the host side, a basic driver implemented for libsigrok for communicating with the Pico W firmware and propagating the data to sigrok suite. Patched version of sigrok library located at the following location: https://github.com/johnkok/libsigrok  
