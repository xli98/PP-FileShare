from hashlib import sha256 as H
from binascii import hexlify as encode, unhexlify as decode
from collections import OrderedDict, deque

# Customized Data Structure for Merkle Tree and Merkle DAG
# Reference: https://hackernoon.com/merkle-tree-introduction-4c44250e2da7

class MissingNodeError(Exception):
    def __init__(self, message):
        super().__init__(message)

class Node:
    def __init__(self, hash, height, children=[]):
        self.height = height
        self.hash = hash
        self.parents = []
        self.children = children

class MerkleTree:
    def __init__(self, values):
        self.root = None
        
        # Assume that values are input as a list
        self.values = values
        self.build_tree()

    def address(self):
        return self.root.hash

    def add(self, value):
        # Holy shit, how do we do this efficiently???
        self.values.append(value)
        self.build_tree()

    def get(self, position):
        return H(bytes(self.values[position], "utf-8")).hexdigest()

    # Tested: Checked
    def contains(self, layers):
        # Layers should be a dict(height: hash)
        # Make the node first
        node = layers.pop(-1)[0]
        
        # Now construct the hash of the root
        current = 0
        while len(layers) > 0:
            if current in layers:
                # regular case
                sibling = layers.pop(current)
                if sibling[1]:
                    node = H(bytes(sibling[0] + node, "utf-8")).hexdigest()
                else:
                    node = H(bytes(node + sibling[0], "utf-8")).hexdigest()

            elif current + 1 in layers:
                # If your node is accidentally a far right, lonely node
                node = H(bytes(node, "utf-8")).hexdigest()
            else:
                raise MissingNodeError("Not providing enough nodes in layers")
            
            current += 1
        
        # Check with hash of the root
        if current == self.root.height and node == self.root.hash:
            return True
        return False

    # Tested: Correct
    def build_tree(self):
        # Compute the hashes
        nodes = []
        for value in self.values:
            hash_value = H(bytes(value, "utf-8")).hexdigest()
            node = Node(hash=hash_value, height=0)
            nodes.append(node)
        
        # Combining hashes together
        while len(nodes) > 1:
            temp = []
            while len(nodes) > 0:
                daughter = nodes.pop(0)
                if len(nodes) != 0:
                    son = nodes.pop(0)
                    hash_value = H(bytes(daughter.hash + son.hash, "utf-8")).hexdigest()
                    node = Node(hash=hash_value, height=daughter.height + 1,\
                        children=[daughter, son])
                    # Make parents
                    daughter.parents.append(node)
                    son.parents.append(node)
                else:
                    # When there is only one node left
                    hash_value = H(bytes(daughter.hash, "utf-8")).hexdigest()
                    node = Node(hash=hash_value, height=daughter.height + 1, \
                        children=[daughter])
                    # Make parents
                    daughter.parents.append(node)
                temp.append(node)
            nodes = temp.copy()
        
        # Update root
        assert(len(nodes) == 1)
        self.root = nodes.pop(0)

    # Tested: Correct!
    def prove(self, pos):
        '''
        Construct a dict path of your merkle tree

        Return: A dict (height: (value, True/False))
        '''
        layers = dict()
        height = 0
        nodes = []
        for value in self.values:
            hash_value = H(bytes(value, "utf-8")).hexdigest()
            node = Node(hash=hash_value, height=0)
            nodes.append(node)
        
        # Need to add 2 in the first layer
        
        # Complementary node here
        if pos % 2 == 0:
            layers[-1] = (nodes[pos].hash, True)
            layers[height] = (nodes[pos + 1].hash, False)
        else:
            layers[-1] = (nodes[pos - 1].hash, True)
            layers[height] = (nodes[pos].hash, False)
        pos = pos//2
        height += 1

        while (len(nodes) > 1):
            temp = []
            while (len(nodes) > 0):
                daughter = nodes.pop(0)
                if len(nodes) != 0:
                    son = nodes.pop(0)
                    hash_value = H(bytes(daughter.hash + son.hash, "utf-8")).hexdigest()
                    node = Node(hash=hash_value, height=daughter.height + 1,\
                        children=[daughter, son])
                    # Make parents
                    daughter.parents.append(node)
                    son.parents.append(node)
                else:
                    # When there is only one node left
                    hash_value = H(bytes(daughter.hash, "utf-8")).hexdigest()
                    node = Node(hash=hash_value, height=daughter.height + 1, \
                        children=[daughter])
                    # Make parents
                    daughter.parents.append(node)

                temp.append(node)
                
            nodes = temp.copy()
            if len(nodes) > 1:
                # Take the complementary
                if pos % 2 == 0:
                    layers[height] = (nodes[pos + 1].hash, False)
                else:
                    layers[height] = (nodes[pos - 1].hash, True)
            pos = pos//2
            height += 1
        return layers

class InvalidMerkleDAG(Exception):
    def __init__(self, message):
        super.__init__(message)

class MerkleDAG:
    def __init__(self):
        self.graph = OrderedDict()

    def add_node(self, node):
        if node in self.graph:
            raise KeyError("Node already existed")
        self.graph[node] = set()

    def delete_node(self, node):
        if node not in self.graph:
            raise KeyError("Node does not exist")
        self.graph.pop(node)

        # Delete edges
        for _, edges in self.graph.items():
            if node in edges:
                edges.remove(node)

    def add_edge(self, from_node, to_node):
        if from_node not in self.graph or to_node not in self.graph:
            raise KeyError('Nodes do not existed in graph')
        
        self.graph[from_node].add(to_node)
        if not self.validate():
            self.graph[from_node].remove(to_node)
            raise InvalidMerkleDAG('Cannot add edge to create cycle')


    def remove_edge(self, from_node, to_node):
        if from_node not in self.graph or to_node not in self.graph:
            raise KeyError("Nodes do not existed in graph")
        if to_node not in self.graph.get(from_node, []):
            raise KeyError("Edge does not exist in graph")
        self.graph[from_node].remove(to_node)

    
    def validate(self):
        '''
        Return True if valid DAG, False if invalid
        '''
        # Run topological sort on this
        in_degree = {}
        for u in self.graph:
            in_degree[u] = 0
        
        for u in self.graph:
            for v in self.graph[u]:
                in_degree[v] += 1
        
        queue = deque()
        for u in in_degree:
            if in_degree[u] == 0:
                queue.appendleft(u)
        
        l = []
        while queue:
            u = queue.pop()
            l.append(u)

            for v in self.graph[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.appendleft(v)
        
        if len(l) == len(self.graph):
            return True
        else:
            return False
