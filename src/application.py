import argparse
from server import server
from client import client 

"""
    Description
    -----------
    Entry point into the application. 
    Parse command-line flags and launch either the DRTP client or server.

    Parameters
    ----------
    None

    Returns
    -------
    It does not return a value.    
"""
def main ():
    parser = argparse.ArgumentParser()

    # Add a mutually exclusive group for server and client
    # This makes them mutually exclusive
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-s", "--server", action="store_true", help="Run as server")
    group.add_argument("-c", "--client", action="store_true", help="Run as client")

    parser.add_argument("-i", "--ip", required=True, help="IP")
    parser.add_argument("-p", "--port", required=True, type=int, help="Port", default=8080)
    parser.add_argument("-f", "--file", help="File")
    parser.add_argument("-w", "--window", type=int, help="Window", default=3)
    parser.add_argument("-d", "--discard", type=int, help="Discard", default=0)

    args = parser.parse_args()

    if args.port < 1024 or args.port > 65535:
        raise SystemExit("Invalid port number. Must be between 1024 and 65535")

    if args.client:
        if args.file is None:
            raise SystemExit("Client mode requires --file to be specified")
        client(args.ip, args.port, args.file, args.window)
    else:  # args.server must be True
        server(args.ip, args.port, args.discard)
    
if __name__ == "__main__":
    main()


