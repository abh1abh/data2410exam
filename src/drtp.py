from struct import pack, unpack
from datetime import datetime

# H = unsigned short (16 bits = 2 bytes)
# 4 fields, each 2 bytes = total 8 bytes
HEADER_FORMAT = '!HHHH'
HEADER_LEN = 8
DATA_LEN = 992
# Flags
FLAG_SYN = 0b0100
FLAG_ACK = 0b0010
FLAG_FIN = 0b1000
FLAG_RST = 0b0001  

# Pack the four 16-bit header fields into network byte order
def build_header(seq: int, ack: int, flags: int, window: int): 
    return pack(HEADER_FORMAT, seq, ack, flags, window)

# Unpack the header 
def parse_header(header_bytes: bytes):
    return unpack(HEADER_FORMAT, header_bytes)


"""
    Description
    -----------
    Construct a complete DRTP packet.

    Parameters
    ----------
    seq, ack : 16-bit sequence and acknowledgement numbers.
    flags : Bitwise OR of *FLAG_* constants.
    window : Advertised receive-window size (packets).
    data : Payload to append after the header.

    Returns
    -------
    bytes : Raw datagram.
"""
def make_packet(seq: int, ack: int, flags: int, window: int, data=b''):
    return build_header(seq, ack, flags, window) + data

# Return the current local time once
def timestamp():   
    return datetime.now()

# Print message with a wall-clock timestamp down to microseconds.
def log(message: str):
    print(f'{timestamp().strftime("%H:%M:%S.%f")} -- {message}')