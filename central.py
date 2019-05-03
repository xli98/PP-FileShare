'''
"Centralized" system who will run the proof of stake
'''
import random
from component import Block
import json as JSON
import threading

class House:
    '''
    Implement a class that decides who chooses the next block
    '''
    def __init__(self, filename='instance_addrs'):
        self.total_stake = 0
        self.users = []
        self.prob = []
        self.users_file = filename
        self.block = None
        self.userQueue = queue.Queue()
    
    '''
    Allow the House to get all information from the user
    '''
    def add_user(self):
        # Read all the address from a file right now
        with open(self.users_file) as fin:
            for line in fin:
                values = line.split(' ')
                user = {'addr':values[0], 'port':values[1]}
                self.users.append(user)
        self.prob = [None] * len(self.users)
        return
    '''
    Request to ask for their stakes
    '''
    def request(self, addr, port, msg):
        # Make a connection to addr and ask for their stakes
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #start tcp connection on designated ports and addresses
        s.connect((addr, port))
        s.send(msg.encode("utf-8"))
        s.close()

    def calc(self):
        # Calculate the probability based on their stake
        for stake in self.prob:
            stake = stake/self.total_stake
        # Arrange the bandwidth of randomization based on their stakes
        for i in range(1, len(self.prob)):
            self.prob[i] += self.prob[i-1]
    '''
    Calculate stake in the system 
    '''
    def calculate_stake(self):
        # Ask for the stakes
        receivingThread = threading.Thread(target=receiveMsg, args=(10010, len(self.users),))
        receivingThread.start()

        miningThread = threading.Thread(target=receive, args=(len(self.users),))
        miningThread.start()
        for i in range(len(self.users)):
            stake_request = JSON.dumps({"type": "stake_request", "index":num})
            stake = self.request(self.users[i]['addr'], self.users[i]['port'], stake_request)

        #wait for the other threads to finish computing before computing stake
        calcThread = threading.Thread(target=receive, args=())
        calcThread.start()
        calcThread.join()

        return 

    def receive(self, total):
        i = 0
        while i < total:
            while not self.userQueue.empty():
                received = self.userQueue.get()
                received = JSON.loads(received)
                self.total_stake += int(received["stake"])
                self.prob[int(received["index"])] = int(received["stake"])
                i = i+1

    def receiveMsg(self, port, total):
    #a single thread that can receive from multiple connections 
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #this allows traffic from all incoming addresses to this port
    #only works for AWS instances, your local IP changes
    s.bind(("0.0.0.0", port))
    s.listen(QUEUE_LENGTH)
    i = 0

    clients = [] * QUEUE_LENGTH
    while i < total:
        conn, addr = s.accept()
        clients.append(conn)
        try:
            packet = ""
            while True:
                data = conn.recv(RECV_BUFFER_SIZE)
                if not data:
                    i = i+1
                    break
                else:
                    packet += data.decode("utf-8")
            self.userQueue.put(packet)
            clients.remove(conn)
            conn.close()
        except:
            clients.remove(conn)
            conn.close()
    return


    '''
    Using a pseudorandom number generator to choose the next verifier
    '''
    def choose_stake(self):
        # Random number
        rand = random.random()
        
        # Choose the next verifier
        for i in range(len(self.prob)):
            if rand < self.prob[i]:
                return self.users[i]
        return self.users[len(self.users) - 1]

    '''
    Receive the block from an exchange
    '''
    def receive_block(self, block):
        self.block = block
        return

    '''
    Send the block to the verifier
    '''
    def send_block(self, user):
        # Receive the addr from choose_stake and then send the block
        for i in range(len(self.users)):
            stake = self.request(self.users[i]['addr'], self.users[i]['port'], str(self.block))

        # Set the block back to None to avoid errors
        self.block = None
        return

if __name__ == "__main__":
    house = House()
    # First need to add users of the system
    house.add_user()
    
    # TODO: Check when there is a file coming in soon
    # Queue stuffs?
    block = Block(None, None)
    while True:
        # Receive the block coming in from an exchange
        house.receive_block(block)
        # Calculate stake and choose the next verifier
        house.calculate_stake()
        user = house.choose_stake()
        # Send the block to the user who will verify it
        house.send_block(user)
        # ????
        break 
