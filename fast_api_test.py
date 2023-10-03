import json
import asyncio
from wasabot_protocol import MessageDecoder
from fastapi import FastAPI
from fastapi import Request
from fastapi import WebSocket
from fastapi.templating import Jinja2Templates
import threading
import serial
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


async def read_serial_data():

    while True:
        md = MessageDecoder()
        frame = md.decode(ser.readline())
        if frame:
            print(frame.payload)
            await data_queue.put({reading.split("=")[0]:float(reading.split("=")[1]) for reading in frame.payload})

        #print(frame)

        #await data_queue.put(frame)


def serial_reader_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(read_serial_data())

# Create and start the separate thread
serial_thread = threading.Thread(target=serial_reader_thread)
serial_thread.daemon = True
serial_thread.start()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# with open('measurements.json', 'r') as file:
#     measurements = iter(json.loads(file.read()))

@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("index.htm", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await data_queue.get()  # Wait for data from the serial reader
        payload = data
        print(type(payload), payload)
        await websocket.send_json(data)