
from sys import argv, exit

import client


if __name__ == '__main__':
    if len(argv) != 2:
        print 'USAGE: python bfclient.py <config file>'
        exit(1)
    c = client.Client(argv[1])
    c.run()

