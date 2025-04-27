from struct import pack, unpack
from datetime import datetime


# H = unsigned short (16 bits = 2 bytes)
# 4 fields, each 2 bytes = total 8 bytes
HEADER_FORMAT = '!HHHH'
HEADER_LEN = 8
DATA_LEN = 992
FLAG_SYN = 0b0100
FLAG_ACK = 0b0010
FLAG_FIN = 0b1000
FLAG_RST = 0b0001  



def build_header(seq_num, ack_num, flags, window):
    return pack(HEADER_FORMAT, seq_num, ack_num, flags, window)

def parse_header(header_bytes):
    return unpack(HEADER_FORMAT, header_bytes)

def make_packet(seq, ack, flags, window, data=b''):
    return build_header(seq, ack, flags, window) + data

def timestamp():
    return datetime.now().strftime("%H:%M:%S.%f")

def log(message):
    print(f'{timestamp()} -- {message}')