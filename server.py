from drtp import parse_header, make_packet, log, HEADER_LEN, DATA_LEN, FLAG_ACK, FLAG_FIN, FLAG_SYN
from datetime import datetime
from socket import socket, AF_INET, SOCK_DGRAM


# HEADER_LEN = drtp.HEADER_LEN
# DATA_LEN = drtp.DATA_LEN
# FLAG_SYN = drtp.FLAG_SYN
# FLAG_ACK = drtp.FLAG_ACK
# FLAG_FIN = d

def handshake_server(sock, rcv_window, timeout=0.4, max_retry=5):
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

        sock.settimeout(timeout)             
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

def recieve(sock, client_addr, start_pkt, rcv_window, discard_seq = 0, outfile='output.bin'):

    expected = start_pkt
    to_discard = discard_seq 
    total_bytes = 0
    t = None  
    
    with open(outfile, 'wb') as out:
        while True:
            data, addr = sock.recvfrom(HEADER_LEN + DATA_LEN)
            if addr != client_addr:
                continue

            seq, _, flags, _ = parse_header(data[:HEADER_LEN])

            payload = data[HEADER_LEN:]

            if seq == to_discard:
                to_discard = float('inf')
                continue


            # Connection teardown
            if flags & FLAG_FIN:
                print(f"\nFIN packet is received seq={seq}")
                fin_ack = make_packet(1, seq, FLAG_FIN | FLAG_ACK, rcv_window)
                sock.sendto(fin_ack, client_addr)
                print(f"FIN-ACK packet is sent seq=1 ack={seq}")
                print("Connection closed")
                break
            

            if seq == expected:
                if t is None:
                    t = datetime.now()
                log(f"packet {seq} is received")
                out.write(payload)
                total_bytes += len(payload)
                expected += 1
                ack = seq

                ack_pkt = make_packet(0, ack, FLAG_ACK, rcv_window)
                sock.sendto(ack_pkt, client_addr)
                log(f"sending ack for the received {ack}")
            else:
                log(f"out-of-order packet {seq} is received (expected {expected})")
                continue
        if t is not None and total_bytes:
            duration_seconds = (datetime.now() - t).total_seconds()
            throughput_mbps = (total_bytes * 8) / (1e6 * duration_seconds)
            print(f"The throughput is {throughput_mbps:.2f} Mbps")
        

        
     

def server(ip, port, window, discard):
    with socket(AF_INET, SOCK_DGRAM) as sock:
        sock.bind((ip, port))
        print("Server running")

        while True:
            try:
                c_addr, start_pkt, agreed_window = handshake_server(sock, window)
                recieve(sock, c_addr, start_pkt, agreed_window, discard)
            except RuntimeError as e:
                print('Server', e)
                continue

if __name__=="__main__":
    server()