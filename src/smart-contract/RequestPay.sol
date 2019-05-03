 pragma solidity >=0.4.22 <0.6.0;
contract RequestPay {
    
    struct Request {
        address requester;
        string hash;
        uint rewards; 
        //TODO: is this problematic
        address proposer;
        uint timelock; 
    }
    
    Request r; 
    bool can_withdraw = false;
    uint _some_time_in_future = 10000;
    string data;
    /// Create a new ballot with $(_numProposals) different proposals.
    constructor(string memory hash_request) public payable {
        //TODO: if someone else calls the constructor, does it override the current request
        r = Request({
            requester: msg.sender,
            hash: hash_request,
            rewards: msg.value,
            //TODO: this sets address to null, might be problem?
            proposer: address(0),
            timelock: now + _some_time_in_future
        });
    }
    
    function deposit() public payable{
        //TODO: do we need to confirm the sender is the requester or no
        r.rewards += msg.value;
    }
    
    function propose_data(string memory hash_data) public{
        if(keccak256(abi.encodePacked(hash_data)) == keccak256(abi.encodePacked(r.hash))){
            if(r.proposer != address(0)){
                r.proposer = msg.sender;
            }
        }
    }
    
    //TOOD: change can_withdraw = true; with timelock when requester gets data
    
    function withdraw(uint256 token, address payable to) public{
        require(r.rewards >= token, "not enough total balance");
        r.rewards -= token;
        if(can_withdraw){
            require(to == r.proposer, "only proposer gets money");
        } else {
            require(to == r.requester, "only proposer gets money");
        }
        require(to.send(token), "send failure");

    }
}
