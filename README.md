# Pokemon-Blockchain
A trading market for pokemon card. 

Disclaimer:
The code is not executable/functional. We were unable to resolve socket programming issues.


- Using public and private key pairs for encryption of data and communication between peers.

We used public private keys for signing and verifying blocks of block chain


- Using tokens for transactions in your marketplace.

We used pokemon cards as tokens itself.


- Allowing transfer of tokens between different clients (wallets/public keys).

We allowed user to put their card up for trade and all the other trainers can offer a card for trade.
If the original trade setter accepts the card then the transaction is sent to the miner to verify ownership, verify signature, broadcast new block.



- Mining transactions in blocks or sending confirmations to those involved in the blockchain once the block is mined successfully.

A transaction is sent to the miner to verify ownership, verify signature, broadcast new block.



- Calculating nonce values by the miners to mine the block.

N/A



- Implying the concept of immutability to make sure previous data cannot be changed. The data on blockchain is always the true state.

We have a single miner. The blockchain was only appended and never changed from the middle. The responsibility of doing work for appending and verfiying the transaction/block is
solely upon the trusted miner.




- Implementing a distributed ledger (this can be done in whatever way suits you, from socket programming to using file handling).

Each trainer has a ledger/blockchain of all the transaction/trades that have been carried out since the start.




- Applying Byzantine Fault Tolerance to make sure a consensus is reached among all the peers.

N/A
