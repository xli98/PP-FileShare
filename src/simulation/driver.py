from hashlib import sha256 as H
from component import *
import time
import threading
import json as JSON
import queue
from binascii import hexlify as encode, unhexlify as decode
import os, errno
import random
import sys
import socket
import urllib.request
import re


RECV_BUFFER_SIZE = 2048
QUEUE_LENGTH = 10
SEND_BUFFER_SIZE = 2048
TIMEOUT = 0.5
TIMELOCK = 10

userNode = None
miningThread = None
#receivingThreads = []
userQueue = queue.Queue()
neighbors = []
retrieve_requests = {}

"""neighbors of nodes; instead of central thread propagating
the node propagates to adjacent nodes maintained by neighbors list
This neighbors is dag and not gaurenteed to not have closed loops
This can be fixed by manually assigning AWS
contract: give me information with this hash, I promise to give you 
this dedicated amount - matching hash, time lock on proposer to send info
"""

def start_node(neighbor_address):
    global neighbors
    global userNode
    global miningThread
    #get local machine address
    self_addr = urllib.request.urlopen("http://169.254.169.254/latest/meta-data/public-ipv4").read().decode("utf-8")
    self_addr = self_addr.replace(".", "-")
    #implementation given list of all node ips
    """num_of_nodes = len(all_nodes)
        for i in range(num_of_nodes): 
        connects = randint(0, num_of_nodes)
        connected = []
        for j in range(connected): 
            node = all_nodes[randint(num_of_nodes)]
            while node in connected and node != all_nodes[i]:
                node = all_nodes[randint(num_of_nodes)]
            connected.append(node)
        neighbors[node[i]] = connected"""
    #current implementation require knowledge of neighbor given as input
    neighbors = neighbor_address
    port = None
    for neighbor in neighbors: 
        if self_addr in neighbor[0]:
            userNode = User_Node(neighbor[0])
            port = int(neighbor[1])
            neighbors.remove(neighbor)
            # this will not work if there is 
            # multiple process from a single node
            # that occupeis different ports
            # but that shouldn"t happen
            break
    receivingThread = threading.Thread(target=receiveMsg, args=(port,))
    receivingThread.start()
    #receivingThreads.append(t)

    miningThread = threading.Thread(target=receive, args=())
    miningThread.start()
    return

def upload(filename, reward):
    global userNode
    msg = read_data(filename)
    """
    create merkle tree and get its root
    """
    address = userNode.upload(msg, os.path.getsize(filename))
    data = userNode.get_data()
    """
    form upload contract to distribute 
    """
    contract = Upload_Contract(repr(data), userNode.address, reward, userNode.get_public_key(), len(msg), address)
    #Keep track of all the contracts with map id mapping
    userNode.generated_contract[contract.id] = contract
    broadcast(repr(contract))
    #remove local copy 
    userNode.stored_data.remove(address)
    for d in list(userNode.data):
        if address == d:
            del userNode.data[d]
    return

def broadcast(msg):
    global neighbors
    for neighbor in neighbors:
        #first in tuple is ip address, second is port
        sendMsg(msg, neighbor[0], int(neighbor[1]))

def receive():
    """ function to discriminate between different kinds of received info in the network"""
    global userNode
    while True:
        while not userQueue.empty():
            received = userQueue.get()
            print(received)
            received = JSON.loads(received)
            print(received)
            if received["type"] == "contract":
                """ 
                upload contracts
                """
                process_contract(received)
            elif received["type"] == "Block":
                """"
                transactions verified into blocks
                """
                process_block(eval(received["exchange"]))
            elif received["type"] == "store request":
                """ 
                request from node to store
                """
                process_store_request(received)
            elif received["type"] == "receive request":
                """
                asking if this node has the file needed
                """
                retrieve(received["requester"], received["data"], \
                    received["reward"], received["timestamp"], \
                    received["id"], received["challenge"])
            elif received["type"] == "sent request":
                """
                some node received your file
                and is trying to get money from you
                """
                process_store_requested(received)
            elif received["type"] == "refund":
                """
                your contract expired and you are refuneded
                """
                refund(received)
            elif received["type"] == "tx":
                """
                transaction record created between this node
                and other nodes
                """
                receive_file_tx(received)

    return

def receive_file_tx(request):
    global retrieve_requests
    global userNode
    """
    node receives proof from challenger
    sends reward and stores file locally if
    verified that 1) proof is correct 2) nothing from request is modified
    """
    r = retrieve_requests[request["id"]]
    request = request["merkleRoot"] + request["reward"] + r["challenge"]
    if userNode.verify(request["merkleRoot"], r["challenge"], request["proof"]) and \
        H(bytes(str(request), "utf-8")).hexdigest() == request["id"]:
        fund(int(received["reward"]))
        exchange = eval(request["exchange"])
        userNode.sign_exchange(exchange, "to")
        broadcast({"exchange": repr(exchange), "type": "block"})
        #print("should sign the other half of the exchange")

def fund(reward):
    global userNode
    userNode.fund(reward)

def refund(request):
    """ 
    differnet kinds of refund conditions
    upload contract, retrieve contract
    """
    global userNode
    if received["id"] in userNode.stored_data:
        userNode.stored_data.remove()
        userNode.fund(int(received["reward"]))
    elif received["id"] in userNode.generated_contract:
        del userNode.generated_contract[received["id"]]
        userNode.fund(int(received["reward"]))
    elif received["id"] in retrieve_requests: 
        del retrieve_requests[received["id"]]
        userNode.fund(int(received["reward"]))

def process_store_requested(request):
    """
    this node stores the file requested by some other node
    forms a half signed transation with the proof and file info
    signed by the node requested for the file
    """
    global userNode
    userNode.upload(request["data"], len(request["data"]))
    exchange = Exchange(userNode.address, request["storager"], userNode.get_public_key(),\
        request["pubkey"], request["filesize"], request["hash"])
    userNode.sign_exchange(exchange, 'from')
    tx = {"Exchange": repr(exchange), "type" : "tx"}
    for neighbor in neighbors:
        if neighbor[0] == request["storager"]:
            sendMsg(JSON.dumps(tx), neighbor[0], int(neighbor[1]))

    return

def process_store_request(request): 
    """
    A node wants to store your uploaded information
    you make them eligibal to withdraw your reward
    and sends the contract back to them
    """
    global userNode
    if userNode.generated_contract[request["contract"]].withdrawer == userNode.address:
        contract = userNode.generated_contract[request["contract"]]
        contract.withdrawer = request["storager"]
        for neighbor in neighbors:
            if neighbor[0] == contract.withdrawer:
                sendMsg(repr(contract), neighbor[0], int(neighbor[1]))
    return


def process_data(contract):
    """
    store the file and get the reward
    """
    global userNode
    userNode.store(contract["data"], int(contract["filesize"]),  int(contract["reward"]))
    userNode.stored_data.append(contract["contentHash"])

    """
    for users to collect/save in terminal
    used to request the file from a different node
    """
    print("The id of the file you stored is: \n", contract["contentHash"])
    return

def process_contract(contract):
    global userNode
    if contract["withdrawer"] == contract["uploader"]:
        if withinTime(contract["timestamp"], contract["timelock"]):
            # contract returned to me
            if contract["withdrawer"] == userNode.address:
                broadcast(repr(contract))
            elif userNode.storage >= contract["filesize"]:
                #this is new node, contract hasn't expired
                #for sake of simulation, random probability of storing the file
                accept = random.randint(0, 10) < 8
                if accept: 
                    #send message to owner
                    #store local reference of contract
                    userNode.stored_contract.append(contract["id"])
                    msg = {"storager": userNode.address, "contract": contract["id"], "type": "store request"}
                    for neighbor in neighbors:
                        if neighbor[0] == contract["uploader"]:
                            sendMsg(JSON.dumps(msg), neighbor[0], int(neighbor[1]))
                else:
                    #doesn't want to store the file
                    broadcast(repr(contract))
        else:
            #withdraw the money
            if contract["withdrawer"] == userNode.address:
                userNode.fund(contract["reward"])
                userNode.stored_contract.append(contract["id"])
    else: 
        #I am the approved storager for this contract 
        if contract["withdrawer"] == userNode.address:
            process_data(contract)
        else:
            #otherwise refund
            refund = {"type" : "refund", "requester": requester, "reward" : reward, "id" : contract["id"]}
            broadcast(JSON.dumps(refund))
    return


def withinTime(timestring, timelock):
    #has not exceeded timestamp, contract hasn't expired
    previousTime = datetime.datetime.strptime(timestring, "%Y-%m-%d %H:%M:%S.%f") 
    return (datetime.datetime.now() - previousTime).total_seconds() < int(timelock)

def inStorage(merkleRoot):
    #does this node have the file that is requested
    global userNode
    for d in userNode.data:
        if merkleRoot == d:
            return userNode.data[d].data

def retrieve(requester, merkleRoot, reward, curtime, retrieve_id, challenge):
    global userNode
    global retrieve_requests
    data = inStorage(merkleRoot)
    if data:
        print("the data you stored is:", data)
        # if I have the data locally and I"m requester
        if(userNode.address == requester):
            #print(userNode.data[merkleRoot])
            userNode.fund(int(reward))
            return 
        else:
            # I have data but im not requester
            proof = userNode.respond(merkleRoot, challenge)
            sent_request = {"proof" : proof, "merkleRoot": merkleRoot, "filesize": len(data), "storager" : userNode.address, \
                        "id" : retrieve_id, "type" : "sent request", "data" : data,\
                        "pubkey": userNode.get_public_key()}
            for neighbor in neighbors:
                if neighbor[0] == requester:
                    sendMsg(JSON.dumps(sent_request), neighbor[0], int(neighbor[1]))

    # request within time but im don"t have data
    if withinTime(curtime, 10): 
        receive_request = {"requester": requester, "data": merkleRoot, \
            "type" : "receive request", "reward" : reward, \
            "timestamp" : curtime, "id" : retrieve_id, "challenge" : challenge}
        if requester == userNode.address:
            userNode.withdraw(reward)
            retrieve_requests[retrieve_id] = receive_request
        for neighbor in neighbors:
            if neighbor[0] != requester:
                sendMsg(JSON.dumps(receive_request), neighbor[0], int(neighbor[1]))
    else:
        #expired request, refund the person
        refund = {"type" : "refund", "requester": requester, "reward" : reward, "id" : retrieve_id}
        broadcast(JSON.dumps(refund))

def process_block(exchange):
    global userNode
    """
    Verify exchange
    """
    userNode.valid_exchange(exchange)
    block = userNode.create_block(exchange)
    valid = userNode.add_block(block)
#TCP connection to all neighbors
def sendMsg(msg, addr, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #start tcp connection on designated ports and addresses
    s.connect((addr, port))
    #break up msg if the entire thing is too large
    msg = [msg[i:i+SEND_BUFFER_SIZE] for i in range(0, len(msg), SEND_BUFFER_SIZE)]
    for m in msg:
        #sys.stdout.write(m.decode("utf-8"))
        s.send(m.encode("utf-8"))
        #print(m)
    s.close()
    return

def receiveMsg(port):
    global userQueue
    #a single thread that can receive from multiple connections 
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #s.settimeout(TIMEOUT)
    #this allows traffic from all incoming addresses to this port
    #only works for AWS instances, your local IP changes
    s.bind(("0.0.0.0", port))
    s.listen(QUEUE_LENGTH)

    clients = [] * QUEUE_LENGTH
    while True:
        conn, addr = s.accept()
        clients.append(conn)
        try:
            packet = ""
            while True:
                #try:
                data = conn.recv(RECV_BUFFER_SIZE)
                if not data:
                    break
                else:
                    packet += data.decode("utf-8")
                """except socket.timeout:
                    continue"""
            userQueue.put(packet)
            clients.remove(conn)
            conn.close()
        except:
            clients.remove(conn)
            conn.close()
    return

def read_data(filename):
    data = ""
    with open(filename, "r") as file:
        data = file.read()
    return data

def handle_input(): 
    global userNode
    global retrieve_requests
    """
    thread that interacts with the user
    allows for 1) deposit 2) add storage 3) upload 4) download

    """
    #userNode.fund(1000)
    #userNode.add_storage(100000)
    manuel = read_data("userManual.txt")
    cur_input = ""
    print(manuel)
    while True: 
        cur_input = input().strip()
        if cur_input.lower() == "exit": 
            break
        commands = cur_input.split(" ")
        if(cur_input[:12].lower() == "add balance:"):
            try: 
                reward = int(commands[2])
                userNode.fund(reward)
                print("adding balance\n")
            except Exception as e:
                print(e)
                print("There are some mistakes in adding balance, try again")
        elif(cur_input[:12].lower() == "add storage:"):
            try: 
                storage = int(commands[2])
                userNode.add_storage(storage)
                print("adding storage\n")
            except Exception as e:
                print(e)
                print("There are some mistakes in adding stroage, try again")
        elif(cur_input[:6].lower() == "upload"): 
            try: 
                filepath = commands[1]
                reward = int(commands[3])
                upload(filepath, reward)
                print("Uploading", filepath, "for $",reward, "\n")
            except Exception as e:
                print(e)
                print("There are some mistakes in uploading file, try again")
        elif(cur_input[:9].lower() == "get file:"):
            try: 
                merkleRoot = commands[2]
                reward = int(commands[4])
                request = str(merkleRoot) + str(reward) + str(userNode.challenge(merkleRoot))
                retrieve(userNode.address, merkleRoot, reward, \
                    str(datetime.datetime.now()), \
                    H(bytes(str(request), "utf-8")).hexdigest(),\
                    userNode.challenge(merkleRoot))
                print("retriving", commands[2])
            except Exception as e:
                print(e)
                print("There are some mistakes in retriving file, try again")
            """merkleRoot = commands[2]
            reward = int(commands[4])
            request = str(merkleRoot) + str(reward) + str(userNode.challenge(merkleRoot))
            retrieve(userNode.address, merkleRoot, reward, \
                    str(datetime.datetime.now()), \
                    H(bytes(str(request), "utf-8")).hexdigest(),\
                    userNode.challenge(merkleRoot))"""
        else:
            print("wrong input, try again")
            print(manuel)

    os._exit(1)

def main():
    #neighbor address and associated ports
    neighbor_address = []
    try:
        with open(sys.argv[1]) as fin:
            for line in fin:
                neighbor_address.append(line.rstrip().split(" "))
    except Exception as e:
        pass
    #start the node functionality threads
    nodesThread = threading.Thread(target=start_node, args=([neighbor_address]))
    nodesThread.start()

    #give time for the node to set up
    time.sleep(0.1)

    #start the user interactive nodes
    inputThread = threading.Thread(target=handle_input, args=())
    inputThread.start()
    return

if __name__ == "__main__":
    main()