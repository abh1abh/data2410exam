from socket import socket, AF_INET, SOCK_DGRAM, timeout as sock_timeout
from drtp import *

"""
    Description
    -----------
    Performs the client side of a three-way handshake over UDP.

    The client sends a SYN packet to the server, waits for a SYN-ACK response,
    and replies with an ACK to establish the connection. If no SYN-ACK is 
    received, it retries up to a specified number of times before failing.

    Parameters
    ----------
    sock : Bound UDP socket.
    server_addr : (ip, port) tuple of the server.
    rcv_window : Client-advertised receive window (packets).
    max_retry : Maximum SYN-ACK retransmissions before giving up.

    Returns
    -------
    window : Advertised window agreed on.
"""
def handshake_client(sock: socket, server_addr: tuple, rcv_window: int, max_retry: int=5):
    print('Connection Establishment Phase:\n')

    syn_pkt = make_packet(0, 0, FLAG_SYN, 0) # Makes SYN packet 

    retries = 0
    while retries < max_retry: 
        sock.sendto(syn_pkt, server_addr) # Sends packet
        print(f'SYN packet is sent')

        try:
            data, _ = sock.recvfrom(HEADER_LEN)   # receives header. Blocks timeout
        except sock_timeout:                      # Socket_timeout error 
            retries += 1
            print('Timeout: retransmit SYN')
            continue                              # Go back and resend

        if len(data) != HEADER_LEN: # Checks header lenght
            print('HEADER has incorrect lenght, skipping')
            continue # Go back and resend

        _, s_ack, s_flags, s_window = parse_header(data) # Parsing header
        
        wanted_flags = FLAG_SYN | FLAG_ACK 
        if (s_flags & wanted_flags) == wanted_flags and s_ack == 0: # Checking if header has SYN-ACK (used AI for this IF-test)
                print(f'SYN-ACK packet is received')
                window = min(rcv_window, s_window) # Selecting the adveristed window
                ack_pkt = make_packet(0, 0, FLAG_ACK, window) # Making ACK packet
                sock.sendto(ack_pkt, server_addr) # Sending ACK packet
                print(f'ACK packet is sent') # This packet can be lost, but the server as a timeout set for this. 
                print('Connection established')

                return window                 
        else:
            print('HEADER unexpected packet during handshake, ignoring…') 
    # Raises an RuntimeError if we retry more than max_retry 
    raise RuntimeError('Three-way handshake failed')

"""
    Description
    -----------
    Send data to server using Go-Back-N over UDP.

    At most rcv_window packets can be unacknowledged (in-flight) at a time.  
    If a timeout occurs before acknowledgments are received, all unacknowledged 
    packets in the current window are retransmitted. The function returns the 
    first unused sequence number after the entire file has been acknowledged.

    Parameters
    ----------
    sock : Bound UDP socket.
    server_addr : (ip, port)  tuple of the server.
    start_seq : Sequence number to assign to the first DATA packet.
    rcv_window : Peer-advertised receive window.
    filename : Path to the file whose contents will be transmitted.
    
    Returns
    -------
    final_seq_no : last byte sent and acknowledged.
"""
def send_data(sock: socket , server_addr: tuple, start_seq: int, rcv_window: int, filename: str):
    
    print('\nData Transfer:\n')
    payloads = []

    # Opens outfile with 'with open' to ensure that the file descriptor closes
    with open(filename, 'rb') as f: 
        while True:
            chunk = f.read(DATA_LEN) # Breaks the file into correct length
            if not chunk:
                break
            payloads.append(chunk) # Adds them to payloads for use later

    base = start_seq # seq of the earliest un-ACKed packet
    next_pkt = start_seq # seq to be assigned to the next DATA packet
    outstanding = {}

    # Helper output to terminal
    def window_output(): 
        return "{" + ", ".join(map(str, sorted(outstanding))) + "}"
    
    # Main loop until every packet is ACKed
    while base - start_seq < len(payloads):

        #  Fill the sliding window while space remains 
        while next_pkt < base + rcv_window and next_pkt - start_seq < len(payloads):
            pkt_bytes = make_packet(next_pkt, 0, 0, rcv_window, payloads[next_pkt-start_seq]) # Make packet
            sock.sendto(pkt_bytes, server_addr) # Send packet
            outstanding[next_pkt] = pkt_bytes # Adding pakcet dict for packets 
            log(f"packet with seq = {next_pkt} is sent, sliding window = {window_output()}")
            next_pkt += 1

        try: #  Wait for an ACK 
            header, _ = sock.recvfrom(HEADER_LEN)
        except sock_timeout: # The timer has expired. Go-Back-N
            log('RTO occured')
            for pkt_id, pkt in outstanding.items(): 
                sock.sendto(pkt, server_addr) # Resend all packets that we have in our sliding window.  
                log(f'retransmitting packet with seq={pkt_id} is resent, sliding window = {window_output()}')
            continue

        _, ack, flags, _ = parse_header(header) # Parse header
        if not (flags & FLAG_ACK): 
            continue

        if ack in outstanding: 
            log(f'ACK for packet = {ack} is recieved')
            while base <= ack:
                outstanding.pop(base, None) # Removing packet from tracking 
                base +=1
    print("DATA Finished\n\n")

    total_pkts   = next_pkt - start_seq          # how many DATA packets
    final_seq_no = start_seq + total_pkts        # first unused seq number
    return final_seq_no  

"""
    Description
    -----------
    Connection teardown by performing a FIN / FIN-ACK exchange.

    The client sends a FIN segment with the given sequence number and waits for 
    a FIN-ACK from the server. If no valid FIN-ACK is received, the FIN is 
    resent. After `max_retry` unsuccessful attempts, the function raises 
    a RuntimeError.

    Parameters
    ----------
    sock : Bound UDP socket.
    server_addr : (ip, port) tuple of the server.
    seq : Sequence number to place in the FIN segment.
    max_retry : Maximum number of FIN retransmissions before aborting.

    Raises
    ------
    RuntimeError
        If no valid FIN-ACK is received within max_retry attempts.
    
"""
def teardown_client(sock: socket, server_addr: tuple, seq: int, max_retry: int=5):

    print('\nConnection Teardown:\n')

    fin_pkt = make_packet(seq, 0, FLAG_FIN, 0) # Client initiated FIN
    retries = 0

    while retries < max_retry:
        sock.sendto(fin_pkt, server_addr)
        print(f'FIN packet packet is sent {seq}')
        try:
            header, _ = sock.recvfrom(HEADER_LEN) # Waiting on FIN-ACK
        except sock_timeout: # Timeout - the timer has expired. 
            retries += 1
            print('Timeout - resend FIN') # Resends FIN packet
            continue
        
        s_seq, s_ack, s_flags, _ = parse_header(header)
        wanted = FLAG_ACK | FLAG_FIN  # Expect FIN-ACK

        # Accept only a FIN-ACK whose ack matches our FIN’s seq
        if(s_flags & wanted) == wanted and s_ack == seq: # (used AI for this IF-test)
            print(f'FIN-ACK packet is received seq={s_seq} ack={s_ack}')
            print('Connection closes')
            return
    
    # If we fall through the loop, the server never acknowledged our FIN
    raise RuntimeError('Teardown failed: FIN not acknowledged')


"""
    Description
    -----------
    Uploads a file to a UDP server in three phases: handshake, data transfer, and teardown.

    This function creates a UDP socket, executes the three phases using helper functions, and 
    handles any `RuntimeError` raised during the process by printing an error message to the console.

    Parameters
    ----------
    ip : Server IP address.
    port : Server UDP port.
    filename : Path to the file that will be transmitted.
    window : Receive-window size the client advertises during the handshake.

    Returns
    -------
    None
        The function terminates when the connection is cleanly torn down.
        It does not return a value.
"""
def client(ip: str, port: int, filename: str, window: int):

    with socket(AF_INET, SOCK_DGRAM) as sock:

        server_addr = ((ip, port)) # Makes the server address
        # Binds the socket ot the local port so the OS chooses on for us. And ip as well.
        sock.bind(('', 0))
        # Setting timeout for the client 
        sock.settimeout(0.4)  
        try:
            start_seq = 1
            agreed_window = handshake_client(sock, server_addr, window) # Three-way handshake 
            final_seq = send_data(sock, server_addr, start_seq, agreed_window, filename) # File transfer 
            teardown_client(sock, server_addr, final_seq) # Connection teardown
        except RuntimeError as e:
            # Any of the helper routines may raise RuntimeError on failure.
            print('Client', e)

        return
