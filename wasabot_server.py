import json
import asyncio
import sqlite3
from wasabot_protocol import MessageDecoder
from fastapi import FastAPI
from fastapi import Request,HTTPException
from fastapi import WebSocket
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import requests
import threading
import serial
import datetime
import random




data_queue = asyncio.Queue()

print('Creating Serial Connection')
ser = serial.Serial(
    '/dev/ttyAMA0',
    9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1,
    write_timeout=1,
)


async def read_serial_data(con):
    cur = con.cursor()
    print('reading serial data')
    while True:


        md = MessageDecoder()
        frame = md.decode(ser.readline())
        if frame:
            print(frame.payload)
            if frame.message_type == 'sensor':
                reading = {reading.split("=")[0]:float(reading.split("=")[1]) for reading in frame.payload}
                cur.execute(f"""
                    INSERT INTO readings VALUES
                        ({reading['light']},{reading['temp']},{reading['humidity']},{reading['moisture_1']},{reading['moisture_2']},CURRENT_TIMESTAMP)
                """)
                con.commit()
                await data_queue.put(reading)


def serial_reader_thread():
    print('run serial reader')
    con = sqlite3.connect("wasabot_v1.db")
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS readings(light, temp, humidity,moisture_1,moisture_2,timestamp)")
    cur.execute("CREATE TABLE IF NOT EXISTS moisture_readings(sensor_id, value, timestamp)")
    cur.execute("CREATE TABLE IF NOT EXISTS watering_log(amount, timestamp)")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(read_serial_data(con))

# Create and start the separate thread
serial_thread = threading.Thread(target=serial_reader_thread)
serial_thread.daemon = True
serial_thread.start()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

origins = [
    "http://localhost:3000",  # React app origin
    # Add any other origins if needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.htm", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await data_queue.get()  # Wait for data from the serial reader
        payload = data
        print(type(payload), payload)
        await websocket.send_json(data)

@app.get("/items/")
async def list_items(request: Request):
    con = sqlite3.connect("wasabot_v1.db")
    try:
        cur = con.cursor()
        res = cur.execute("select * from readings order by timestamp desc limit 10")
        data = res.fetchall()
        print(data)
        items = [{'timestamp':item[5],"light": item[0], "temp": item[1], "humidity": item[2],"moisture_1": item[3],"moisture_2":item[4]} for item in data]
        return templates.TemplateResponse("sensor_data.html", {"request": request, "items": items})
    finally:
        con.close()


@app.get("/json-sensor-data/")
async def list_items():
    con = sqlite3.connect("wasabot_v1.db")
    try:
        cur = con.cursor()
        res = cur.execute("select * from readings order by timestamp desc limit 1")
        data = res.fetchall()
        items = [{"light": item[0], "temp": item[1], "humidity": item[2],"moisture_1": item[3],"moisture_2":item[4]} for item in data]
        return items  # This will be automatically converted to JSON
    finally:
        con.close()


@app.get("/send_command")
def send_water(request: Request):

    print('sending command by serial')


    ser.write(b'bb')

@app.get("/water_command")
def water_command(request: Request):

    print('sending command by api')
    # URL of the external API you want to call
    external_api_url = "http://192.168.1.134/light/on"

    try:
        # Make a GET request to the external API
        response = requests.get(external_api_url)

        # Check if the request was successful
        if response.status_code == 200:
            # Process and return the response data
            return response.status_code
        else:
            return {"error": "External API request failed"}

    except requests.RequestException as e:
        # Handle any exceptions that occur during the request
        return {"error": str(e)}


@app.get("/water_command/{param}")
def water_command(param: int):
    # Use the param in your logic, for example, as part of the external API URL
    external_api_url = f"http://192.168.1.134/light/amt/{param}"

    try:
        response = requests.get(external_api_url)

        if response.status_code == 200:
            if response.content:
                try:
                    return response.status_code
                except ValueError:
                    return {"error": "Invalid JSON received"}
            else:
                return {"error": "Empty response received"}
        else:
            return {"error": f"External API request failed with status code {response.status_code}"}

    except requests.RequestException as e:
        return {"error": str(e)}



# Function to insert a batch of readings into the database
def insert_readings(readings: list):
    try:
        with sqlite3.connect('wasabot_v1.db') as conn:
            cursor = conn.cursor()
            cursor.executemany(
                "INSERT INTO moisture_readings (sensor_id, value, timestamp) VALUES (?, ?, ?)",
                readings
            )
            conn.commit()
    except sqlite3.Error as e:
        raise e

@app.post("/batch_readings/")
async def add_batch_readings(request: Request):
    try:
        # Parse JSON body of the request
        data = await request.json()

        # Validate data and prepare for batch insertion
        readings_to_insert = []
        for reading in data:
            sensor_id = reading.get("sensor_id")
            value = reading.get("value")
            timestamp = reading.get("timestamp")

            if sensor_id is None or value is None or timestamp is None:
                raise ValueError("Missing data in one or more readings")

            readings_to_insert.append((sensor_id, value, timestamp))

        insert_readings(readings_to_insert)
        return {"message": "Batch readings added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/watering_log")
async def add_watering_log(request: Request):
    try:
        with sqlite3.connect('wasabot_v1.db') as conn:
            cursor = conn.cursor()
            reading = await request.json()
            cursor.execute(f"""
                                INSERT INTO watering_log VALUES
                                    ({reading['amount']},CURRENT_TIMESTAMP)
                            """)
            conn.commit()
    except sqlite3.Error as e:
        raise e