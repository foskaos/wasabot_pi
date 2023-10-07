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


# async def read_serial_data():
#
#     while True:
#         md = MessageDecoder()
#         frame = md.decode(ser.readline())
#         if frame:
#             #print(frame.payload)
#             if frame.message_type == 'sensor':
#                 await data_queue.put({reading.split("=")[0]:float(reading.split("=")[1]) for reading in frame.payload})


async def mock_read_data():
    print('started mock read')
    counter = 0
    while True:
        await asyncio.sleep(2)
        data = {'light':counter}#f"{counter}"
        await data_queue.put(data)
        counter += 1
        print('put_data', counter)


app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("index.htm", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print('ws')
    while True:
        data = await data_queue.get()  # Wait for data from the serial reader
        payload = data
        print(type(payload), payload)
        await websocket.send_json(data)


loop = asyncio.get_event_loop()
task = loop.create_task(mock_read_data())