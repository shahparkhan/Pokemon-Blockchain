import sys
import socket 
import threading
from blockchain import Block
from uuid import uuid4
import random
from pickle import dumps, loads
from hashutils import hash_object

class Miner:
    # Trusted entity that verifies integrity of transactions
    # Constructors
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.stop = False
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(None)
        self.sock.bind((self.host, self.port))
        
        
        # Containes transactions, a count of people who have
        # verified the ownership of the card, and the count of
        # positive verifications
        self.transaction_verification = {}
        
        self.members = {}
        # Number of member on the platform
        self.member_count = 0 # 5


        # Starting listen thread
        threading.Thread(target = self.listener).start()

    # Listens to messages from members
    def listener(self):
        while not self.stop:
            message_byte, _ = self.sock.recvfrom(4096)
            message = message_byte
            self.handleMessage(message)
            # threading.Thread(target = self.handleConnection, args = (client, addr)).start()
        print("Shutting down miner:", self.host, self.port)
        try:
            self.sock.shutdown(2)
            self.sock.close()
        except:
            self.sock.close()
    
    # Deals with incoming messages
    def handleMessage(self, message):
        socket, _ = self.sock.accept()
        message = socket.recv(4096)
        message = message
        content = loads(message)
        
        if content['type'] == "transaction":

            if content['trade_id'] not in list(self.transaction_verification.keys()):
                self.transaction_verification[content['trade_id']] = {}
    
            self.transaction_verification[content['trade_id']][content['transaction_id']] = {"verified": 0, "positive": 0, "public_key_sender": content["public_key_sender"], "public_key_receiver": content["public_key_receiver"], "pokemon_card_id": content["pokemon_card_id"], "hash_pokemon_card_id": content["hash_pokemon_card_id"], "signature": content["signature"], "port": content["port"]}
            self.broadcast_verification_message(content["public_key_sender"], content["pokemon_card_id"], content['transaction_id'], content['trade_id'])
        
        elif content['type'] == "ownership_verified":
            val = self.transaction_verification[content["trade_id"]][content["transaction_id"]]["verified"] + 1
            self.transaction_verification[content["trade_id"]][content["transaction_id"]]["verified"] = val

            val = self.transaction_verification[content["trade_id"]][content["transaction_id"]]["positive"] + 1
            self.transaction_verification[content["trade_id"]][content["transaction_id"]]["positive"] = val

            verified_count = []
            positive_count = []
            for key, val in self.transaction_verification[content["trade_id"]]:
                verified_count.append(val["verified"])
                positive_count.append(val["positive"])
            
            if (verified_count[0] == self.member_count) and (verified_count[1] == self.member_count) and (verified_count[0] == verified_count[1]):
                if ((positive_count[0]/verified_count[0]) >= 0.5) and ((positive_count[1]/verified_count[1]) >= 0.5):
                    dummy = self.transaction_verification[content["trade_id"]][content["transaction_id"]]
                    block = self.create_block(dummy["public_key_sender"], dummy["public_key_receiver"], dummy["pokemon_card_id"], dummy["hash_pokemon_card_id"], dummy["signature"], dummy["transaction_id"])
                    message = {"type": 'approved_transaction', }
                    self.broadcast_block(block)

                    for key, val in self.transaction_verification[content["trade_id"]]:
                        message = {"type": "transaction_approved", "transaction_id": key}
                        self.send_message(message, 'localhost', val["port"])                 
        
        elif content['type'] == "ownership_not_verified":
            val = self.transaction_verification[content["trade_id"]][content["transaction_id"]]["verified"] + 1
            self.transaction_verification[content["trade_id"]][content["transaction_id"]]["verified"] = val

            verified_count = []
            positive_count = []
            for key, val in self.transaction_verification[content["trade_id"]]:
                verified_count.append(val["verified"])
                positive_count.append(val["positive"])
            
            if (verified_count[0] == self.member_count) and (verified_count[1] == self.member_count) and (verified_count[0] == verified_count[1]):
                if ((positive_count[0]/verified_count[0]) >= 0.5) and ((positive_count[1]/verified_count[1]) >= 0.5):
                    dummy = self.transaction_verification[content["trade_id"]][content["transaction_id"]]
                    block = self.create_block(dummy["public_key_sender"], dummy["public_key_receiver"], dummy["pokemon_card_id"], dummy["hash_pokemon_card_id"], dummy["signature"], dummy["transaction_id"])            
                    self.broadcast_block(block)

                    for key, val in self.transaction_verification[content["trade_id"]]:
                        message = {"type": "transaction_approved", "transaction_id": key}
                        self.send_message(message, 'localhost', val["port"])  

        elif content['type'] == "send_ten_cards":
            block = self.create_block_without_verification(content["public_key_sender"], content["public_key_receiver"], content["pokemon_card_id"], content["hash_pokemon_card_id"], content["signature"], uuid4())
            self.broadcast_block(block)
            self.add_initial_card(content["card"], content["port"])

    def add_initial_card(self, card, port):
        message = {"type": "add_intitial_card", "card": card}
        self.send_message(message, 'localhost', port)


    # Create block using the transaction receieved by 
    def create_block(self, public_key_sender, public_key_receiver, pokemon_card_id, hash_pokemon_card_id, signature, transaction_id):
        if self.verify_signature(signature, public_key_sender, pokemon_card_id):
            content = {"transaction_id" : transaction_id,
                        "public_key_sender": public_key_sender,
                        "public_key_receiver": public_key_receiver,
                        "pokemon_card_id": pokemon_card_id,
                        "hash_pokemon_card_id": hash_pokemon_card_id,
                        "signature": signature}
            block = Block(content)
            return block
        else:
            return None


    def create_block_without_verification(self, public_key_sender, public_key_receiver, pokemon_card_id, hash_pokemon_card_id, signature, transaction_id):
        
        content = {"transaction_id" : transaction_id,
                    "public_key_sender": public_key_sender,
                    "public_key_receiver": public_key_receiver,
                    "pokemon_card_id": pokemon_card_id,
                    "hash_pokemon_card_id": hash_pokemon_card_id,
                    "signature": signature}
        block = Block(content)
        return block
    


    #Verify signature of sender    
    def verify_signature(self, signature, public_key_sender, pokemon_card_id):
        return public_key_sender.verify(signature, hash_object(pokemon_card_id))


    #Create the genesis block
    def create_genesis_block(self, pokemon_master_key, pokemon_card_id_list):
        content = {"pokemon_master_key": pokemon_master_key,
                   "pokemon_card_id_list": pokemon_card_id_list}
        block = Block(content, block_type='genesis')
        return block
    

    # Broadcast message to all members to verify the ownership of card
    def broadcast_verification_message(self, owner_public_key, card_id, transaction_id, trade_id):
        message = {"type": "verify_ownership", "owner_public_key": owner_public_key, "card_id": card_id, "transaction_id": transaction_id, "trade_id": trade_id}
        for key, val in self.members:
            self.send_message(message, val[0], val[1])

    def send_message(self, content, addr, port):
        packet = dumps(content)
        socket, _ = self.sock.connect((addr, port))
        socket.sendall(packet, (addr, port))


    # Upon receiving update on ownership, update 
    def update_transaction(self, transaction_id):
        pass


        
    # Tells all member to add a block to their blockchain
    def broadcast_block(self, block):
        message = {"type": "add_block", "block": block}
        for key, val in self.members:
            self.send_message(message, val[0], val[1])
    

    # Tells member to add card upon successful confirmation of transaction
    def add_card(self, card):
        pass
    
    # Tells member to remove card upon successful confirmation of transaction
    def remove_card(self, card):
        pass
    
    




# Starting miner to listen on port 10000 and host localhost
if __name__ == "__main__":

    HOST = "localhost"    
    PORT = 10000

    M = Miner(HOST,PORT)
    try:
        # Start receiving Messages
        T = threading.Thread(target=M.listener)
        T.daemon = True
        T.start()

    except (KeyboardInterrupt, SystemExit):
        sys.exit()