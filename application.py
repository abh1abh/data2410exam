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
    parser.add_argument("-s", "--server", action="store_true", help="Run as server")
    parser.add_argument("-c", "--client", action="store_true", help="Run as client")
    parser.add_argument("-i", "--ip", required=True, help="IP")
    parser.add_argument("-p", "--port", required=True, type=int, help="Port")
    parser.add_argument("-f", "--file", help="File")
    parser.add_argument("-w", "--window", type=int, help="Window", default=3)
    parser.add_argument("-d", "--discard", type=int, help="Discard", default=0)

    args = parser.parse_args()

    if args.client:
        if args.file is None:
            raise SystemExit("Client mode requires --file to be specified")
        client(args.ip, args.port, args.file, args.window)
    elif (args.server):
        server(args.ip, args.port, args.discard)
    else:
        raise SystemExit("Not server or client")
    
if __name__ == "__main__":
    main()