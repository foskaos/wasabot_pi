import serial

class DecodedMessage:
    def __init__(self, message_type: str, payload: [str]):
        self.message_type = message_type
        self.payload = payload

    def __str__(self):
        return f"Type: {self.message_type}, Payload: {self.payload}"

class MessageDecoder:
    def __init__(self):
        # Initialize any necessary state or settings for decoding
        ...
    def decode(self, serial_data):
        try:
            # Implement your decoding logic here, e.g., parsing JSON
            decoded_data = self._parse_serial_line(serial_data)
            return decoded_data
        except Exception as e:
            print("Error decoding data:", e)

            return None

    @staticmethod
    def calculate_checksum(data):
        checksum = 0
        for byte in data:
            checksum ^= byte
        return bytes([checksum])

    def _parse_serial_line(self,ln):
        line = ln.strip()
        if line:
            if (line[0] == 60) and line[-1] == 62:
                # we are in this block because the start and end chars were detected,
                # so we can extract the body from the line
                msg = line[1:-1]
                r_ck = msg[len(msg) - 1:]
                data = msg[:len(msg) - 1]

                # compare received checksum with calculated one
                if r_ck == self.calculate_checksum(data):
                    # convert data bytes to string
                    string_rep = data.decode('utf-8')
                    # data body is delimited with ":" character
                    msg_parts = string_rep.split(":")
                    # take the first value as which client sent the message, put the rest in
                    msg_type, *body = msg_parts
                    # print(f'from: {msg_from}, body: {body}')
                    message = DecodedMessage(msg_type,body)
                    return message
                else:
                    # checksum didn't work, so message bad

                    raise ValueError("Checksum Failed")
            else:
                print('invalid message: ', line)
                raise ValueError("Start/Stop Characters not found")

# /dev/ttyAMA3 is TX(green) on Gpio 8, RX(white) on Gpio 9
# /dev/ttyAMA0 is TX(green) on Gpio 14, RX(white) on GPIO 15


print('Creating Serial Connection')
ser = serial.Serial(
    '/dev/ttyAMA3',
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
