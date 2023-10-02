import serial
from wasabot_protocol import MessageDecoder

# /dev/ttyAMA3 is TX(green) on Gpio 8, RX(white) on Gpio 9
# /dev/ttyAMA0 is TX(green) on Gpio 14, RX(white) on GPIO 15


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

while True:
    while ser.in_waiting:
        md = MessageDecoder()
        frame = md.decode(ser.readline())
        if frame:
            print(frame)
