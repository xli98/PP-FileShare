from component import User_Node, CommitNode, Block, Exchange
from merkle import MerkleTree
import os
import nacl
import nacl.signing
from nacl.public import PrivateKey, Box
from binascii import hexlify as encode, unhexlify as decode

def read_data(filename):
    with open(filename) as f:
        data = f.read()
    return data

def check_filesize(filename):
    return os.path.getsize(filename)

def test_merkle():
    # Handle some data
    filename = 'merkle.txt'
    data = read_data(filename)
    size = check_filesize(filename)

    # Test Merkle tree first
    # Split into 8 parts
    values = data.splitlines()
    
    # Test the address is root address is always the same
    merkle = MerkleTree(values)
    # print(merkle.address())

    # Test contain text merkle_1 in merkle (should have)
    test_1 = merkle.prove(0)
    # Prove is correct

    # Need to check for contains
    print(merkle.contains(test_1))
    return


def test_user():
    # Handle some data
    filename = 'small.txt' # This text has 800 characters
    data = read_data(filename)
    size = check_filesize(filename)

    '''
    CREATE USERS FOR EXCHANGE
    '''
    # Create a user
    user1 = User_Node(1)
    user2 = User_Node(2)

    # Fund this user
    user1.fund(1000)
    user1.add_storage(100000)

    # Upload file locally
    address1 = user1.upload(data, size)

    # Check the file stored
    data1 = user1.get_data()

    '''
    VERIFY SIGNATURE FROM FILE
    '''
    sig = data1[address1].sig
    pub_key = user1.get_public_key()
    verify_key = nacl.signing.VerifyKey(pub_key, \
        encoder=nacl.encoding.HexEncoder)
    try:
        verify_key.verify(decode(sig))
    except nacl.exceptions.BadSignatureError:
        print("Key wrong")
        return False

    '''
    CHECK UPLOAD FILE TWICE. SHOULD NOT ADD MORE DATA - Works
    '''
    address = user1.upload(data, size)
    assert(len(user1.get_data()) == 1)
    assert(address == address1)

    '''
    UPDATING NEW FILE - Works
    '''
    # New file
    new_filename = 'second.txt'
    new_data = read_data(new_filename)
    new_size = check_filesize(new_filename)

    # Update file
    addr2 = user1.update(new_data, new_size, address1)

    # Check to see if the update is correct
    # print(user1.get_file(addr2))
    # print(user1.get_file(address1))
    
    '''
    REMOVE FILES - Works
    '''
    # Remove file
    user1.remove_file(address1)
    assert(len(user1.get_data()) == 1)

    '''
    EXCHANGE BETWEEN TWO USERS - Checked!
    '''
    # User 2 requests a file from User 1
    requested_addr = user2.request(addr2)
    # User 1 sends a file over
    requested_file = user1.get_file(requested_addr)
    # User 2 receives the file.
    user2.add_storage(10000)
    user2.receive(requested_addr, requested_file)
    # User 1 asks for a challenge
    bit = user1.challenge(requested_addr)
    # User 2 sends over the response
    proof = user2.respond(requested_addr, bit)
    # User 1 verify the response
    result = user1.verify(requested_addr, bit, proof)
    print(result)
 
    # Generate an exchange if verifying correctly    
    if result:
        exchange = Exchange(user1.address, user2.address, user1.get_public_key(),\
            user2.get_public_key(), new_size, requested_addr)
        user1.sign_exchange(exchange, 'from')
        user2.sign_exchange(exchange, 'to')
    # Need to seal the exchange (avoid tampering)
    user2.seal_exchange(exchange)
    # print(exchange.print())

    '''
    VERIFY EXCHANGE
    '''
    # Just one user to verify exchange for now
    valid = user1.valid_exchange(exchange)
    print(valid)
    '''
    RUNNING PROOF OF STAKES
    ''' 
    # Look at the simulation for proof of stakes
    # Assuming user2 will put in the exchange to the block
    block = user2.create_block(exchange)

    # User 1 will update the exchange
    valid = user1.add_block(block)
    print(valid)    
    return

def main():
    # test_merkle()
    test_user()
    return

if __name__ == "__main__":
    main()