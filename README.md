# PP-FileShare

PP-FileShare is a distributed file sharing system that a small group of computers can adopt to exchange file securely. The system is inspired by current system like InterPlanetary File Sharing (IPFS) and FileCoin; however, these systems are complicated with a grand mission (replace HTTP protocol in IPFS case). We want to introduce a system at a smaller scale where small group of nodes can adopt quickly and only need to make small adjustments depending on their needs. 


## Getting Started
### Paper
Complement with the implementation, we also wrote a paper where you can read [here](https://github.com/xli98/PP-FileShare/blob/master/paper.pdf). The paper explains many components within our implementation and why we adopt these policies and implementations. 

### Prerequisites
We implemented this system using [Python 3](https://www.python.org/downloads/). Each node in the system is simulated as an AWS EC2 [instance](https://aws.amazon.com/ec2/) communicating through TCP connections.


### Set up AWS EC2 Instance
For this implementation, we simulate nodes as AWS EC2 instances. Therefore, we need to set them up, which can be accomplished through this set of [instructions](https://docs.aws.amazon.com/efs/latest/ug/gs-step-one-create-ec2-resources.html). We then put all the addresses and port into a file called [instance_addrs](https://github.com/xli98/PP-FileShare/blob/master/src/simulation/instance_addrs), which House class (representing the distributed network) takes in to calculate proof of stake and choose the next verifier.


### Installing
* EC2 enviroment preparation

If you have already set up an AWS EC2 instance following the instructions above, you can install the packages required for installing python dependencies using the following command:

```
./setup.sh
```

The command is for linux systesm. Comment out the first line if you are on a ubuntu system.


* Python 3 and Pip

You can download and install Python 3 [here](https://www.python.org/downloads/). Pip should come installed when you install Python 3. 

* Install packages and dependencies

We have prepared [requirement.txt](https://github.com/xli98/PP-FileShare/blob/master/requirement.txt) to make it easier to install all dependencies. You can install these with:

```
pip3 install -r requirement.txt
```

## Sample Run
We attached two small files called [small.txt](https://github.com/xli98/PP-FileShare/blob/master/src/simulation/small.txt) and [second.txt](https://github.com/xli98/PP-FileShare/blob/master/src/simulation/second.txt), each has 800 characters. We used these files to test upload, update, and exchange between nodes in the system. You can check out a sample code below of how you can run the simulation.
```
python3 driver.py instance_addr
add balance: 1000
add storage: 10000
upload small.txt reward: 10
get file: 6cf51f9d62f3889622449177b20069c7dbcf71af3b8e6c3076c9b97831af299c reward: 10
```

## Authors
* Coco Li
* Tan Nguyen
