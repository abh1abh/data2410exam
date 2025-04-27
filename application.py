import argparse
from server import server
from client import client 

def main ():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--server", required=False, action="store_true", help="Run as server")
    parser.add_argument("-c", "--client", required=False, action="store_true", help="Run as client")
    parser.add_argument("-i", "--ip", required=True, help="IP")
    parser.add_argument("-p", "--port", required=True, help="Port")
    parser.add_argument("-f", "--file", required=False, help="File")
    parser.add_argument("-w", "--window", required=False, help="Window", default=3)
    parser.add_argument("-d", "--discard", required=False, help="Discard")

    args = parser.parse_args()

    is_server = args.server
    is_client = args.client
    ip = args.ip
    port = int(args.port)
    filename = args.file
    window = int(args.window)
    discard = args.discard

    if (is_client):
        client(ip, port, filename, window)
    elif (is_server):
        server(ip, port, window)
    else:
        raise Exception("Not server or client")
    
if __name__ == "__main__":
    main()