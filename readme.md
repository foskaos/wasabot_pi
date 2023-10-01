# Wasabot - "Server"


Building a raspberry pi based 'server' script/app to collect data over serial from various sensors.

## Phase 1
I will log sensor them in a database, and also provide a web ui to display them.

### So far I have:
* Designed a simple serial messaging protocol
* Implemented a testing environment
* Set up a raspberry pi pico to send data from a DHT-22 sensor

### Outstanding for Phase 1:
* Add light sensor
* Save data in persistent storage (db)
* Simple webserver to host sensor logs
* Simple UI to display logs and realtime data

## Phase 2
Will set up various thresholds and logic to detect if environmental conditions are suitable, and actuate things to get
things in order

### Outstanding for Phase 2
* Water pump
* Soil moisture sensor
* Fan
* Web notifications 
* Nicer web ui (graphs, responsive etc)
* Web API
