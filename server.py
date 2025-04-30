from drtp import *
from socket import socket, AF_INET, SOCK_DGRAM

"""
    Description
    -----------
    Perform the server side of a UDP three-way handshake.

    Parameters
    ----------
    sock : Bound UDP socket used for the session.
    rcv_window : Server-advertised receive window (packets).
    timeout : Seconds to wait for the client’s ACK before retransmitting SYN-ACK.
    max_retry : Maximum SYN ACK retransmissions before giving up.

    Returns
    -------
    client_addr : Address of the client that successfully completed the handshake.
    agreed_wnd : Flow-control window agreed on.
"""
def handshake_server(sock: socket, rcv_window: int=15, timeout: float=0.4, max_retry: int=5):
    while True:
        # Here we receive the packet and check if its only the length of header. 
        data, client_addr = sock.recvfrom(HEADER_LEN)
        if len(data) != HEADER_LEN:
            continue

        _, _, c_flags, _ = parse_header(data) # Parses packet header

        # Ignore anything that is not a bare SYN
        if not (c_flags & FLAG_SYN) or (c_flags & FLAG_ACK):
            continue          # stay in the loop and wait for a real SYN
        
        print(f'SYN packet is received seq')

        # Makes a packet with a SYN ACK flag with our standard receiving window
        synack_pkt  = make_packet(0, 0 , FLAG_SYN | FLAG_ACK, rcv_window)
        
        sock.settimeout(timeout) # Sets timeout for if we dont receive an ACK
        retries = 0
        while retries < max_retry:
            sock.sendto(synack_pkt, client_addr) # Send SYN-ACK packet
            print(f'SYN-ACK packet is sent seq')
            try:
                data, addr = sock.recvfrom(HEADER_LEN) # Receive packet from client 
            except: # If no packet is recieved from client we resend the SYN-ACK
                retries += 1
                print('Server timeout -> resend SYN-ACK')
                continue # Resend SYN-ACK by doing continue
            
            # If the address from the received packet is not the client address from the first packet we try again.
            if addr != client_addr or len(data) != HEADER_LEN:
                continue

            _, _, c_flags2, c_wnd = parse_header(data) # Parse packet
            wanted_flags = FLAG_ACK  # The flag we want
            if(c_flags2 & wanted_flags) == wanted_flags: # Checks if the packet as the flag
                print(f'ACK packet is received')  # Restore blocking mode
                sock.settimeout(None) # Flow-control safety        
                agreed_wnd = min(rcv_window, c_wnd)   
                print('Connection established')
                return client_addr, agreed_wnd
        # Raises an RuntimeError if we retry more than max_retry 
        raise RuntimeError('client did not finish handshake')


"""
    Description
    -----------
    Receive a contiguous sequence of packets from client and write their
    payloads to outfile.

    The routine implements Go-Back-N. The transfer terminates cleanly when a packet 
    carrying the FIN flag is received, at which point the server replies with FIN-ACK
    and closes the connection. At the end of a successful session the function prints 
    the measured throughput in Mbps (megabits per second).

    Parameters
    ----------
    sock : UDP socket already bound by the caller.
    client_addr : IP/port tuple identifying the client accepted by the handshake.
    start_pkt : Sequence number expected for the first data packet.
    rcv_window : Size of the advertised receive window (in packets).
    discard_seq : ptional sequence number to intentionally lose once per session.
    outfile : File path where incoming payload bytes are written.

    Returns
    -------
    bool : True when the file transfer finishes successfully and the connection
        is torn down.
"""
def receive(sock: socket, client_addr: tuple, start_pkt: int, rcv_window: int, discard_seq: int=0, outfile: str='output.bin'):

    # Asigning different variable
    expected = start_pkt
    to_discard = discard_seq 
    total_bytes = 0
    t = None  
    
    # Opens outfile with 'with open' to ensure that the file descriptor closes
    with open(outfile, 'wb') as out:
        while True:
            data, addr = sock.recvfrom(HEADER_LEN + DATA_LEN) # Waits for packet from client

            if addr != client_addr: # Check if address form packet is same as clients 
                continue

            seq, _, flags, _ = parse_header(data[:HEADER_LEN]) # Parses packet header

            payload = data[HEADER_LEN:] # Gets payload
            packet_bytes = len(data) # Total bytes of packet  

            # Discard logic for discarding packet 
            if seq == to_discard:
                to_discard = float('inf')
                continue

            # Connection teardown
            if flags & FLAG_FIN: 
                print(f'\nFIN packet is received seq={seq}')
                fin_ack = make_packet(1, seq, FLAG_FIN | FLAG_ACK, rcv_window) # Making FIN-ACK packet
                sock.sendto(fin_ack, client_addr) # Sending FIN-ACK packet
                print(f'FIN-ACK packet is sent')
                print("Connection closed")
                break # Break out of while loop

            if seq == expected: # Checks if the seq number is the same as we expected
                if t is None: # If we dont time we start one
                    t = timestamp()
                log(f"packet {seq} is received")
                out.write(payload) # Write to outfile
                total_bytes += packet_bytes # Counting total bytes
                expected += 1 
                ack = seq

                ack_pkt = make_packet(0, ack, FLAG_ACK, rcv_window) # Making ACK packet
                sock.sendto(ack_pkt, client_addr) 
                log(f'sending ack for the received {ack}')
            else: # If seq number is not what we expected 
                log(f'out-of-order packet {seq} is received (expected {expected})')
                continue # Drops packet and wait for the correct one
        # Throughput calcuation
        if t is not None and total_bytes:
            end = timestamp()
            # To calcuated the total time it took to recieve all the packets
            duration_seconds = (end - t).total_seconds() 
            throughput_mbps = (total_bytes * 8) / (1e6 * duration_seconds)
            print(f'The throughput is {throughput_mbps:.2f} Mbps')
        print('Connection Closes')
        return True;   

"""
    Description
    -----------
    Run a single–file UDP transfer service. The function binds a UDP socket to the 
    given ip-address and port, accepts exactly one client via a three-way handshake, 
    receives the file using the Go-Back-N protocol, and then terminates.

    Parameters
    ----------
    ip : Local IP address to bind the listening socket to.
    port : UDP port number to listen on.
    discard : Sequence number to drop intentionally once per session for 
    retransmission testing.  

    Exceptions:
    -----------
    Any `RuntimeError` raised during the handshake is caught and logged, after
    which the server waits for a new client.
    """

def server(ip, port, discard):
    # Using 'with open' so that if any exceptions are raised the socket closes.
    with socket(AF_INET, SOCK_DGRAM) as sock: 
        sock.bind((ip, port)) # Binds socket to IP and port
        while True:
            try:
                start_pkt = 1 # Starting packet
                c_addr, agreed_window = handshake_server(sock) # Handshake with client
                if receive(sock, c_addr, start_pkt, agreed_window, discard): # Recieves file from users 
                    #Exit after exactly one successful transfer – simplifies 
                    break
            except RuntimeError as e: # Handles any runtime excpetions raised and prints the to terminal
                print('Server', e)
                continue