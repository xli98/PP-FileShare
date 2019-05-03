from hashlib import sha256 as H
import json
import nacl, nacl.signing
from nacl.public import PrivateKey, Box
from binascii import hexlify as encode, unhexlify as decode
from merkle import MerkleTree
import random, datetime

'''
Example exchange will look like:
{"num": <number>, "from": <address>, "to": <address>, "file_hash": <hash>, 
"payment": <pay>, "size": <size>, "sig1": <signature>, "sig2":<signature>, 
"pubkey1": <public key>, "pubkey2": <public key>}
'''

'''
A wrapper around the data node for version control
'''

# Set the global partition to be 100 characters
split_n = 100

class CommitNode:
    def __init__(self, data, size, parent=None):
        # Previous node 
        self.parent = parent
        # Data node 
        self.data = data
        # File address (built from Merkle root hash)
        self.address = self.compute_hash()
        # Use signature to know the update right 
        self.sig = None
        # File size
        self.size = size

    def compute_hash(self):
        '''
        Split the data for every n characters and compute Merkle root hash
        '''
        values = [self.data[i:i+split_n] for i in range(0, len(self.data), split_n)]
        merkle = MerkleTree(values)
        return merkle.address()

    def sign(self, signature):
        self.sig = signature

    def __repr__(self):
        data = {}
        data["parent"] = self.parent
        data["data"] = self.data
        data["address"] = self.address
        data["sig"] = self.sig
        return json.dumps(data)

'''
A block within the public ledger 
'''
class Block:
    def __init__(self, exchange, prev):
        self.prev = prev
        self.exchange = exchange

    def __repr__(self):
        data = {}
        data["exchange"] = self.exchange
        data["prev"] = self.prev
        return json.dumps(data)

class SignException(Exception):
    def __init__(self, message):
        super.__init__(self, message)

'''
Represent an exchange between two users
'''
class Exchange:
    def __init__(self, from_addr, to_addr, from_pub, to_pub, file_size, file_hash):
        self.from_addr = from_addr
        self.to_addr = to_addr
        self.from_pub = from_pub
        self.to_pub = to_pub
        self.file_size = file_size
        self.file_hash = file_hash

        self.sig = {}
        self.number = None

    def __repr__(self):
        data = {}
        data["from"] = self.from_addr
        data["to"] = self.to_addr
        data["file_size"] = self.file_size
        data["file_hash"] = self.file_hash
        data["from_pubkey"] = self.from_pub
        data["to_pubkey"] = self.to_pub
        return json.dumps(data)
    
    def print(self):
        data = {}
        data["number"] = self.number
        data["from"] = self.from_addr
        data["to"] = self.to_addr
        data["file_size"] = self.file_size
        data["file_hash"] = self.file_hash
        data["from_pubkey"] = self.from_pub
        data["to_pubkey"] = self.to_pub
        data["from_sig"] = self.sig['from']
        data["to_sig"] = self.sig['to']
        return json.dumps(data)

    def sign(self, signature, type):
        if len(self.sig) > 2:
            raise SignException("You cannot sign anymore")
        if type != 'from' and type != 'to':
            raise SignException("Your type of signing is not correct")
        self.sig[type] = signature
        return

    def seal(self):
        # Avoid tampering. from, to, file size and hash and 2 signatures
        self.number = H(bytes(str(self.from_addr) + str(self.to_addr) +\
            str(self.file_hash) + str(self.file_size) + str(self.sig['from']) +\
                str(self.sig['to']), "utf-8")).hexdigest()
        return

class Upload_Contract:
    #TODO: periodically check timelock
    def __init__(self, info, uploader, reward, pubkey, filesize, merkle):
        self.data = info
        self.timelock = 100
        self.uploader = uploader
        self.withdrawer = uploader
        self.pub = pubkey
        self.filesize = filesize
        self.sig = None
        self.contentHash = merkle
        if reward > 0: 
            self.reward = reward
        else:
            raise NotEnoughMoney("please deposit some reward")
        #python doesn't have constants
        #this is pseudo contract bc anyone can modify
        #also python doesn't take into consideration of timezone
        self.timestamp = datetime.datetime.now()
        self.id = H(bytes(str(self.timestamp), "utf-8")).hexdigest()
    def deposit(self, amount):
        self.reward += amount
    def becomeStorager(self, storager, sig):
        verify_key = nacl.signing.VerifyKey(self.pub, encoder=nacl.encoding.HexEncoder)
        if verify_key.verify(sig): 
            self.withdrawer = storager
    def withdraw(self, storager):
        #once again, not constants so security is only in logic but not in simulation
        if(storager == self.withdrawer):
            total = self.reward
            self.reward = 0
            return total
    def __repr__(self):
        data = {}
        data["data"] = self.data
        data["timelock"] = self.timelock
        data["withdrawer"] = self.withdrawer
        data["uploader"] = self.uploader
        data["pub"] = self.pub
        data["filesize"] = self.filesize
        data["reward"] = self.reward
        data["timestamp"] = str(self.timestamp)
        data["type"] = "contract"
        data["id"] = self.id
        data["contentHash"] = self.contentHash
        #to recover from string: 
        #previousTime = datetime.datetime.strptime(str(line), "%Y-%m-%d %H:%M:%S.%f") 
        return json.dumps(data)


'''
Exception class for clarity
'''
class NotEnoughStorageSpace(Exception):
    def __init__(self, message):
        super().__init__(message)

class NotEnoughMoney(Exception):
    def __init__(self, message):
        super().__init__(message)

class User_Node:
    def __init__(self, address):
        # Data format should be {hash: object}
        self.data = dict()
        # Data length dict {hash: len}
        self.data_len = dict()
        # Budget
        self.budget = 0
        # Address of the node 
        self.address = address

        # We need a ledger here to check past transaction
        # No longer have fork (proof of stake), so not need a tree
        self.current = Block(None, None)

        # Storage in total
        self.storage = 0
        self.avail_storage = self.storage

        # Signing Key
        self.signing_key = nacl.signing.SigningKey.generate()
        self.public_key = self.signing_key.verify_key
        self.generated_contract ={}
        self.stored_contract = []
        self.stored_data = []

    def fund(self, amount):
        # Assuming that the node transfer money in from real cash
        self.budget += amount
        return

    def withdraw(self, amount):
        if self.budget - amount < 0:
            raise NotEnoughMoney("Not enough money to do this exchange. \
                Mine more!")
        self.budget -= amount
        return

    def fake_stake(self):
        # USE THIS FOR TESTING ONLY
        return self.avail_storage

    def stake(self):
        return self.storage - self.avail_storage

    def get_data(self):
        return self.data

    def get_file(self, address):
        return self.data[address]

    def get_public_key(self):
        return str(self.public_key.encode(encoder=nacl.encoding.HexEncoder),'utf-8')

    def add_storage(self, storage):
        self.storage += storage
        self.avail_storage += storage

    def remove_storage(self, storage):
        if self.avail_storage - storage < 0:
            raise NotEnoughStorageSpace("Cannot delete storage. Please delete\
                 some data first")
        self.avail_storage -= storage
        self.storage -= storage

    def upload(self, data, filesize):
        '''
        Add file locally or receive files for free storage
        '''
        # Add storage here
        if self.avail_storage - filesize < 0:
            raise NotEnoughStorageSpace("You don't have enough storage")
        self.avail_storage -= filesize
        
        # Wrap node around the data
        obj = CommitNode(data, filesize)

        # Sign the data to avoid tampering
        signature = str(encode(self.signing_key.sign(H(bytes(obj.data, "utf-8")).digest())),'utf-8')
        obj.sign(signature)
        self.data[obj.address] = obj

        # Add to data length 
        self.data_len[obj.address] = len(data)

        return obj.address

    def remove_file(self, file_hash):
        '''
        Remove your file at the position 
        '''
        try:
            self.data.pop(file_hash)
            return True
        except:
            return False

    def store(self, data, filesize, value):
        '''
        Receive files to gain monetary value 
        '''
        self.fund(value)
        return self.upload(data, filesize)
        
    def update(self, data, filesize, current_hash):
        '''
        Update file for version control
        '''
        addr = self.upload(data, filesize)
        self.data[addr].parent = current_hash
        return addr

    def distribute(self, file_hash):
        ''' 
        Distribute the file with this certain hash

        Return a tuple of file_hash
        '''
        return (file_hash, self.data[file_hash])

    def request(self, file_hash):
        ''' 
        Request the file with that hash
        '''
        if file_hash not in self.data:
            return file_hash
        return None

    def compute_hash(self, data):
        '''
        Split the data for every n characters and compute Merkle root hash
        '''
        values = [data[i:i+split_n] for i in range(0, len(data), split_n)]
        merkle = MerkleTree(values)
        return merkle.address()

    def receive(self, requested_hash, obj):
        '''
        Receive the requested file with certain hash
        '''
        hash_value = self.compute_hash(obj.data)
        if hash_value == requested_hash:
            self.data[hash_value] = obj
        else:
            raise KeyError("File does not have the same requested hash")
        # Check size to make sure you have enough
        if self.avail_storage - obj.size < 0:
            raise NotEnoughStorageSpace("You don't have enough storage space")
        self.avail_storage -= obj.size
        return
    
    def challenge(self, data_hash):
        '''
        Send out a challenge for the storager
        '''
        partition = self.data_len[data_hash]/split_n
        return random.randint(0, partition-1)

    def respond(self, data_hash, position):
        '''
        Respond to a challenge
        '''
        try:
            data = self.data[data_hash].data
        except:
            # You don't have this data. Can implement code to cheat?
            return None
        values = [data[i:i+split_n] for i in range(0, len(data), split_n)]
        merkle = MerkleTree(values)
        return merkle.prove(position)

    def verify(self, data_hash, position, proof):
        ''' 
        Proof will have the format of dict(height: hash)
        '''
        data = self.data[data_hash].data
        values = [data[i:i+split_n] for i in range(0, len(data), split_n)]
        merkle = MerkleTree(values)
        # Need to make sure the position is right as well?
        block_hash = merkle.get(position)
        if proof[-1][0] == block_hash or proof[0][0] == block_hash:
            return merkle.contains(proof)
        return None

    def sign_exchange(self, exchange, type):
        '''
        Sign the exchange after verifying it
        '''
        signature = str(encode(self.signing_key.sign(H(bytes(str(exchange), "utf-8")).digest())),'utf-8')
        exchange.sign(signature, type)
        return

    def seal_exchange(self, exchange):
        '''
        Seal exchange to avoid tampering
        '''
        exchange.seal()
        return

    def valid_exchange(self, exchange):
        '''
        Validate the exchange 
        '''
        # Check number
        number = H(bytes(str(exchange.from_addr) + str(exchange.to_addr) +\
            str(exchange.file_hash) + str(exchange.file_size) + \
            str(exchange.sig["from"]) + str(exchange.sig["to"]), "utf-8")).hexdigest()
        if number != exchange.number:
            print("Number is wrong")
            return False

        # Verify signature on file
        verify_key1 = nacl.signing.VerifyKey(exchange.from_pub, \
            encoder=nacl.encoding.HexEncoder)
        verify_key2 = nacl.signing.VerifyKey(exchange.to_pub,\
            encoder=nacl.encoding.HexEncoder)
        try:
            verify_key1.verify(decode(exchange.sig["from"]))
            verify_key2.verify(decode(exchange.sig["to"]))
        except nacl.exceptions.BadSignatureError:
            print("wrong key")
            return False
        return True
    
    def create_block(self, exchange):
        '''
        Update the block for the running public ledger 
        '''
        # Check if the exchange is valid or not
        if not self.valid_exchange(exchange):
            return None
        block = Block(exchange, self.current.exchange)
        self.current = block
        return block

    def valid_block(self, block):
        '''
        Check if the block is valid or not
        '''
        # You want the block to connect to the current one
        if block.prev != self.current.exchange:
            print("Prev wrong")
            return False
        if not self.valid_exchange(block.exchange):
            print("Exchange wrong")
            return False
        return True
        
    def add_block(self, block):
        '''
        Add block to the public ledger that we are maintaining
        '''
        if not self.valid_block(block):
            return False
        self.current = block
        return True