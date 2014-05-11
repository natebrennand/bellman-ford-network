
# Bellman-Ford Network

- Nate Brennand
- nsb2142




## Running It

### Execution

Execute the `bfclient.py` file with a config file passed as an argument.

```bash
python bfclient.py config.txt
```

### Config Files

The config files follow the specified format with one addition, the user can specify the number of chunks to the file as a 5th parameter on the 1st line.
This allows transfering of larger files that are split into many chunks.

### Caveats

Chunk sequence numbers are 1 indexed.

In some linux distributions (not the one CLIC is running), the commands used to get the local IP may return 127.0.0.1 due to the hosts file.
This causes errors in how the client binds to a port.

### Test Files

A set of config files (and the file chunks) I used in testing are locatedin the `/src/test_config/` directory.






## Network

### Dynamic Network

Nodes will try to connect to the neighbors specified in the config file, if those neighbors are unrseponsive they will timeout and be removed from their routing table.
When any node recieves a routing table broadcast from another node, a link is created between them.
This differs from the assignment specification (see Piazza #339) but results in a much more dynamic network.
The lack of constraints allows the network to truly become distributed as there is no initial limit on the number nodes in the network.


### Protocols

All messages between nodes are sent in JSON format.
Basic format:

- type: a constant name that varies by the message type
- name: name of the sending node
- ip: ip of the sending node
- port: port of the sending node
- data: routing table or image chunk

The exact specs can be viewed within the `routing_table.py` file.

I experimented with using the gzip Python library but the compression gained was very meager so I chose to not add complexity.

#### Message Types

- ROUTE\_UPDATE
  - broadcasted to all neighbors to transfer the sending node's routing table
- CHUNK\_TRANSFER
  - sent towards the node that is recieving the file
  - will be forward by nodes until it reaches it's target
- TRANSFER\_BROADCAST
  - a message that is forwarded to all nodes in the network the from the node requesting all file chunks.
  - aach individual broadcast message has a destination and will be forwarded until it is reached.





## User Commands

### Linkup

Can be used both to relink a node with the specified cost.
Can also be used to change the weight of an existing node if it's cheaper a cheaper weight.

### Linkdown

Linkdown works as described in the assignment.
After severing the link to the specified neighbor, the new routing table is broadcasted to all other neighbors and that specified neighbor is ignored for 4 * timeout.
The link can then be remade from either of the two nodes.

### Show RT

The SHOWRT command works as specified in the assignment.
The cheapest routes to all nodes known in the network are displayed.







## File Transfers

Chunk sequence numbers are 1 indexed.

There is an optional 5th config option on the first line to declare how many chunks are in the file.
By default the node will assume that there is only 2 chunks to a file.


Example output:
```
python bfclient.py test_config/d_config
Operating at 160.39.154.219:4003
GET
Recieved chunk #2 from 160.39.154.219:4001 @ 05/11/2014 15:35:17.216521
Steps:
05/11/2014 15:35:17.214952 Step #1 @ 160.39.154.219:4001
05/11/2014 15:35:17.215675 Step #2 @ 160.39.154.219:4002
Recieved chunk #1 from 160.39.154.219:4000 @ 05/11/2014 15:35:17.218086
Steps:
05/11/2014 15:35:17.215095 Step #1 @ 160.39.154.219:4000
05/11/2014 15:35:17.216893 Step #2 @ 160.39.154.219:4002
Recieved all 2 chunks, writing file to ouput
```


### Transfer

This transfers the file chunk (if there is one) to the specified recipient.
Nodes who the file is routed through will print out a message when the chunk passes through them.
When a file chunk is received the path they took is printed out.
Once the receiving node has recieved all file chunks, they are written to `output`.

### Get

This command broadcasts a request to all nodes in the network asking to be sent the file chunks.
The calling node is then forwarded all file chunks.
When a file chunk is received the path they took is printed out.
Upon having every chunk for the file, they are written to `output`.


### Status

This command prints out the status of the file receiving process for the node it is called on.
It will display how many chunks have been recived of the number expected.
After the file has been fully received this will display 0/N.







##Extra Features

- Truly dynamic networking see the Network section
  - not relying on the intitial config file for all neighbors added significant complexity
- Variable number of file chunks as specifed in the Execution section.
- The GET command mentioned in the File Transfers section.



