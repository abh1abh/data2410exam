from drtp import *
from socket import *

def handshake(sock, rcv_window, timeout_window=0.4, max_retry=5):
    print('Waiting')
    while True:
        data, client_addr = sock.recvfrom(HEADER_LEN)
        if len(data) != HEADER_LEN:
            continue

        c_seq, c_ack, c_flags, _ = parse_header(data)

        # Ignore anything that is *not* a bare SYN
        if not (c_flags & FLAG_SYN) or (c_flags & FLAG_ACK):
            continue          # stay in the loop and wait for a real SYN

        print(f'SYN packet is received seq={c_seq}, ack={c_ack}, wnd={_}')
                    
        server_isn  = 1                      
        synack_pkt  = make_packet(server_isn, c_seq + 1, FLAG_SYN | FLAG_ACK, rcv_window)

        sock.settimeout(timeout_window)             
        retries = 0
        while retries < max_retry:
            sock.sendto(synack_pkt, client_addr)
            print(f'SYN-ACK packet is sent seq={server_isn}, ack={c_ack +1}')

            try:
                data, addr = sock.recvfrom(HEADER_LEN)
            except:
                retries += 1
                print('Server timeout -> resend SYN-ACK')
                continue

            if addr != client_addr or len(data) != HEADER_LEN:
                continue

            c_seq2, c_ack2, c_flags2, c_wnd = parse_header(data)
            wanted_flags = FLAG_ACK
            if(c_flags2 & wanted_flags) == wanted_flags and c_ack2 == server_isn + 1:
                print(f'ACK packet is received seq={c_seq2} ack={c_ack2} wnd={c_wnd}')
                sock.settimeout(None)          # restore blocking mode
                agreed_wnd = min(rcv_window, c_wnd)   # flow-control safety
                print('Connection established')
                return client_addr, c_seq2, agreed_wnd
        raise RuntimeError('client did not finish handshake')



def server(ip, port, window):
    with socket(AF_INET, SOCK_DGRAM) as sock:
        sock.bind((ip, port))
        print("Server running")

        while True:
            try:
                c_addr, c_seq, window = handshake(sock, window)
            except RuntimeError as e:
                print('Server', e)
                continue

if __name__=="__main__":
    server()