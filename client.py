from socket import socket, AF_INET, SOCK_DGRAM, timeout as sock_timeout
from drtp import *

def handshake_client(sock, server_addr, rcv_window, timeout=0.4, max_retry=5):
    print('Connection Establishment Phase:\n')
    seq = 0
    ack = 0

    syn_pkt = make_packet(seq, 0, FLAG_SYN, 0)

    sock.settimeout(timeout)

    retries = 0
    while retries < max_retry:
        sock.sendto(syn_pkt, server_addr)
        print(f'SYN packet is sent seq={seq}, ack={ack}')

        try:
            data, _ = sock.recvfrom(HEADER_LEN)   # blocks ≤ timeout
        except sock_timeout:                      # ★ replaces select()
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
                window = min(rcv_window, s_window)

                ack_pkt = make_packet(seq+1, ack, FLAG_ACK, window)
                sock.sendto(ack_pkt, server_addr)
                print(f'ACK packet is sent (seq={seq+1}, ack={ack})')
                
                print('Connection established')

                return seq+1, window                 # next usable seq number
        else:
            print('HEADER unexpected packet during handshake, ignoring…')
    raise RuntimeError('Three-way handshake failed')

def send_data(sock, server_addr, start_seq, rcv_window, filename, timeout=0.4, max_retry=5):
    
    seq = start_seq

    print('\nData Transfer:\n')
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

    sock.settimeout(timeout)

    def window_output(): 
        return "{" + ", ".join(map(str, sorted(outstanding))) + "}"
    
    while base - start_seq < len(payloads):

        while next_pkt < base + rcv_window and next_pkt - start_seq < len(payloads):
            pkt_bytes = make_packet(next_pkt, 0, 0, rcv_window, payloads[next_pkt-start_seq])
            sock.sendto(pkt_bytes, server_addr)
            outstanding[next_pkt] = pkt_bytes
            log(f"packet with seq = {next_pkt} is sent, sliding window = {window_output()}")
            next_pkt += 1

        try:
            header, _ = sock.recvfrom(HEADER_LEN)
        except sock_timeout:
            log('RTO occured')
            for pkt_id, pkt in outstanding.items():
                sock.sendto(pkt, server_addr)
                log(f'retransmitting packet with seq={pkt_id} is resent, sliding window = {window_output()}')
            continue

        _, ack, flags, _ = parse_header(header)
        if not (flags & FLAG_ACK):
            continue

        if ack in outstanding:
            log(f'ACK for packet = {ack} is recieved')
            while base <= ack:
                outstanding.pop(base, None)
                base +=1
    print("DATA Finished\n\n")

    total_pkts   = next_pkt - start_seq          # how many DATA packets
    final_seq_no = start_seq + total_pkts        # first unused seq number
    return final_seq_no  

def teardown_client(sock, server_addr, seq, timeout=0.4, max_retry=5):

    print('\nConnection Teardown:\n')

    fin_pkt = make_packet(seq, 0, FLAG_FIN, 0)
    retries = 0

    sock.settimeout(timeout)

    while retries < max_retry:
        sock.sendto(fin_pkt, server_addr)
        print(f'FIN packet packet is sent {seq}')
        try:
            header, _ = sock.recvfrom(HEADER_LEN)
        except sock_timeout:
            retries += 1
            print('Timeout - resend FIN')
            continue
        
        s_seq, s_ack, s_flags, _ = parse_header(header)
        wanted = FLAG_ACK | FLAG_FIN

        if(s_flags & wanted) == wanted and s_ack == seq:
            print(f'FIN-ACK packet is received seq={s_seq} ack={s_ack}')
            print('Connection closes')
            return
    raise RuntimeError('Teardown failed: FIN not acknowledged')

def client(ip, port, filename, window):

    sock = socket(AF_INET, SOCK_DGRAM)

    server_addr = ((ip, port))
    sock.bind(('', 0))
    sock.settimeout(0.4)  
    try:
        next_seq, agreed_window = handshake_client(sock, server_addr, window)
        final_seq = send_data(sock, server_addr, next_seq, agreed_window, filename)
        teardown_client(sock, server_addr, final_seq)
    except RuntimeError as e:
        print(e)

    return 

if __name__=="__main__":
    client()