import json
import asyncio
import sqlite3
from wasabot_protocol import MessageDecoder
from fastapi import FastAPI
from fastapi import Request,HTTPException
from fastapi import WebSocket
from fastapi.templating import Jinja2Templates
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
                        ({reading['light']},{reading['temp']},{reading['humidity']},CURRENT_TIMESTAMP)
                """)
                con.commit()
                await data_queue.put(reading)


def serial_reader_thread():
    print('run serial reader')
    con = sqlite3.connect("tutorial.db")
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS readings(light, temp, humidity,timestamp)")
    cur.execute("CREATE TABLE IF NOT EXISTS moisture_readings(sensor_id, value, timestamp)")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(read_serial_data(con))

# Create and start the separate thread
serial_thread = threading.Thread(target=serial_reader_thread)
serial_thread.daemon = True
serial_thread.start()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

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
    con = sqlite3.connect("tutorial.db")
    try:
        cur = con.cursor()
        res = cur.execute("select * from readings order by timestamp desc limit 10")
        data = res.fetchall()
        items = [{'timestamp':item[3],"light": item[0], "temp": item[1], "humidity": item[2]} for item in data]
        return templates.TemplateResponse("sensor_data.html", {"request": request, "items": items})
    finally:
        con.close()


@app.get("/send_command")
def send_water(request: Request):

    print('sending command by serial')


    ser.write(b'bb')


# Function to insert a batch of readings into the database
def insert_readings(readings: list):
    try:
        with sqlite3.connect('tutorial.db') as conn:
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