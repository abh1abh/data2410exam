from socket import * 
from struct import *
from drtp import *

def handshake(sock, server_addr, c_window, timeout_window=0.4, max_retry=5):
    seq = 0
    ack = 0

    syn_pkt = make_packet(seq, 0, FLAG_SYN, 0)

    sock.settimeout(timeout_window)

    retries = 0
    while retries < max_retry:
        sock.sendto(syn_pkt, server_addr)
        print(f'SYN packet is sent seq={seq}, ack={ack}')

        try:
            data, _ = sock.recvfrom(HEADER_LEN)   # blocks ≤ timeout
        except timeout:                      # ★ replaces select()
            retries += 1
            print('Timeout -> retransmit SYN')
            continue                              # go back and resend

        if len(data) != HEADER_LEN:
            print('HEADER has incorrect lenght, skipping')
            continue   

        s_seq, s_ack, s_flags, s_window = parse_header(data)
        
        
        wanted_flags = FLAG_SYN | FLAG_ACK
        if (s_flags & wanted_flags) == wanted_flags and s_ack == (seq+1):
                print(f'SYN-ACK packet is received (seq={s_seq}, ack={s_ack}, wnd={s_window})')

                ack = s_seq + 1

                # adjust our send window to min(cleint_window, r_window)
                window = min(c_window, s_window)

                ack_pkt = make_packet(seq+1, ack, FLAG_ACK, window)
                sock.sendto(ack_pkt, server_addr)
                print(f'ACK packet is sent (seq={seq+1}, ack={ack})')
                
                print('Connection established')

                return seq+1, window                 # next usable seq number
        else:
            print('HEADER unexpected packet during handshake, ignoring…')
    raise RuntimeError('Three-way handshake failed')

def send_data(sock, server_addr, start_seq, window, filename, timeout_window=0.4, max_retry=5):
    
    seq = start_seq

    payloads = []

    with open(filename, 'rb') as f:
        while True:
            chunk = f.read(DATA_LEN)
            if not chunk:
                break
            payloads.append(chunk)

    base = start_seq
    next_pkt = start_seq
    outstanding = {}

    sock.settimeout(timeout_window)

    def window_output(): 
        return "{" + ", ".join(map(str, sorted(outstanding))) + "}"
    
    while base - start_seq < len(payloads):

        while next_pkt < base + window and next_pkt - start_seq < len(payloads):
            pkt_bytes = make_packet(next_pkt, 0, 0, window, payloads[next_pkt-start_seq])
            sock.sendto(pkt_bytes, server_addr)
            outstanding[next_pkt] = pkt_bytes
            log(f"packet with seq = {next_pkt} is sent, sliding window = {window_output()}")




def client(ip, port, filename, window):

    sock = socket(AF_INET, SOCK_DGRAM)

    server_addr = ((ip, port))
    sock.bind(('', 0))
    sock.settimeout(0.4) 
    print("Client running")
 
    try:
        next_seq, agreed_window = handshake(sock, server_addr, window)
    except RuntimeError as e:
        print(e)

    return 

if __name__=="__main__":
    client()