import sys
import socket 
import threading
from blockchain import Block
from uuid import uuid4
import random
from pickle import dumps, loads
from ecdsa import SigningKey
from ecdsa.keys import VerifyingKey
from hashutils import hash_object

class Miner:
    # Trusted entity that verifies integrity of transactions
    # Constructors
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.stop = False
        # self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # self.sock.settimeout(None)
        # self.sock.bind((self.host, self.port))
      
        # Starting listen thread
        
        
        
        # Containes transactions, a count of people who have
        # verified the ownership of the card, and the count of
        # positive verifications
        self.transaction_verification = {}
        
        self.members = {}
        # Number of member on the platform
        self.member_count = 0 # 5
        T1 = threading.Thread(target = self.listener)
        T1.start()

    def public_key_to_str(self, public_key):
        return public_key.to_string().hex()

    def public_key_to_obj(self, public_key):
        return VerifyingKey.from_string(bytes.fromhex(public_key))

    def private_key_to_str(self, private_key):
        return private_key.to_string().hex()

    def private_key_to_obj(self, private_key):
        return SigningKey.from_string(bytes.fromhex(private_key))  

    # Listens to messages from members
    def listener(self):

        listener = socket.socket()
        listener.bind((self.host, self.port))
        listener.listen(100)
        while not self.stop:
            client, addr = listener.accept()
            threading.Thread(target = self.handleMessage, args = (client, addr)).start()
        print("Shutting down miner:", self.host, self.port)
        try:
            listener.shutdown(2)
            listener.close()
        except:
            listener.close()
    
    # Deals with incoming messages
    def handleMessage(self, client, addr):

        message_arr = []
        while True:
            packet = client.recv(4096)
            if not packet: break
            message_arr.append(packet)
        content = loads(b"".join(message_arr))

        # content = loads(message)
        
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
            for key, val in self.transaction_verification[content["trade_id"]].items():
                verified_count.append(val["verified"])
                positive_count.append(val["positive"])
            
            if (verified_count[0] == self.member_count) and (verified_count[1] == self.member_count):
                if ((positive_count[0]/verified_count[0]) >= 0.5) and ((positive_count[1]/verified_count[1]) >= 0.5):
                    txn_ids = list(self.transaction_verification[content["trade_id"]].keys())
                    
                    dummy = self.transaction_verification[content["trade_id"]][txn_ids[0]]
                    block = self.create_block(dummy["public_key_sender"], dummy["public_key_receiver"], dummy["pokemon_card_id"], dummy["hash_pokemon_card_id"], dummy["signature"], txn_ids[0])
                    self.broadcast_block(block)

                    
                    dummy = self.transaction_verification[content["trade_id"]][txn_ids[1]]
                    block = self.create_block(dummy["public_key_sender"], dummy["public_key_receiver"], dummy["pokemon_card_id"], dummy["hash_pokemon_card_id"], dummy["signature"], txn_ids[0])
                    self.broadcast_block(block)

                    for key, val in self.transaction_verification[content["trade_id"]].items():
                        message = {"type": "transaction_approved", "transaction_id": key}
                        new_sock = socket.socket()
                        new_sock.connect(('localhost', val["port"]))
                        self.send_message(message, new_sock)

                                  
        
        elif content['type'] == "ownership_not_verified":
            val = self.transaction_verification[content["trade_id"]][content["transaction_id"]]["verified"] + 1
            self.transaction_verification[content["trade_id"]][content["transaction_id"]]["verified"] = val

            verified_count = []
            positive_count = []
            for key, val in self.transaction_verification[content["trade_id"]].items():
                verified_count.append(val["verified"])
                positive_count.append(val["positive"])
            
            if (verified_count[0] == self.member_count) and (verified_count[1] == self.member_count):
                if ((positive_count[0]/verified_count[0]) >= 0.5) and ((positive_count[1]/verified_count[1]) >= 0.5):
                    dummy = self.transaction_verification[content["trade_id"]][content["transaction_id"]]
                    block = self.create_block(dummy["public_key_sender"], dummy["public_key_receiver"], dummy["pokemon_card_id"], dummy["hash_pokemon_card_id"], dummy["signature"], content["transaction_id"])            
                    self.broadcast_block(block)

                    for key, val in self.transaction_verification[content["trade_id"]].items():
                        message = {"type": "transaction_approved", "transaction_id": key}
                        new_sock = socket.socket()
                        new_sock.connect(('localhost', val["port"]))
                        self.send_message(message, new_sock)  

        elif content['type'] == "send_ten_cards":
            block = self.create_block_without_verification(content["public_key_sender"], content["public_key_receiver"], content["pokemon_card_id"], content["hash_pokemon_card_id"], content["signature"], uuid4())
            self.broadcast_block(block)
            new_sock = socket.socket()
            new_sock.connect(('localhost', content["port"]))
            self.add_initial_card(content["card"], new_sock)

        elif content['type'] == "add_member":
            public_key_obj = self.public_key_to_obj(content['public_key'])
            self.members[content['name']] = (content['host'], int(content['port']), public_key_obj)
            self.member_count = self.member_count + 1

    def add_initial_card(self, card, client):
        message = {"type": "add_initial_card", "card": card}

        self.send_message(message, client)


    # Create block using the transaction receieved by 
    def create_block(self, public_key_sender, public_key_receiver, pokemon_card_id, hash_pokemon_card_id, signature, transaction_id):
        if self.verify_signature(signature, public_key_sender, hash_pokemon_card_id, pokemon_card_id):
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
    def verify_signature(self, signature, public_key_sender, hash_pokemon_card_id, card_id):
        return public_key_sender.verify(signature, hash_pokemon_card_id.encode('utf-8'))


    #Create the genesis block
    def create_genesis_block(self, pokemon_master_key, pokemon_card_id_list):
        content = {"pokemon_master_key": pokemon_master_key,
                   "pokemon_card_id_list": pokemon_card_id_list}
        block = Block(content, block_type='genesis')
        return block
    

    # Broadcast message to all members to verify the ownership of card
    def broadcast_verification_message(self, owner_public_key, card_id, transaction_id, trade_id):
        message = {"type": "verify_ownership", "owner_public_key": owner_public_key, "card_id": card_id, "transaction_id": transaction_id, "trade_id": trade_id}
        for key, val in self.members.items():
            new_sock = socket.socket()
            new_sock.connect((val[0], val[1]))
            self.send_message(message, new_sock)

    def send_message(self, content, client):
        packet = dumps(content)
        client.send(packet)
        client.close()


    # Upon receiving update on ownership, update 
    def update_transaction(self, transaction_id):
        pass


        
    # Tells all member to add a block to their blockchain
    def broadcast_block(self, block):
        message = {"type": "add_block", "block": block}
        for key, val in self.members.items():
            new_sock = socket.socket()
            new_sock.connect((val[0], val[1]))
            self.send_message(message, new_sock)
    

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
    try:
        # Start receiving Messages
        print("Starting...\nName: " + "MINER" + "\nHost: " + str(HOST) + "\nPort: " + str(PORT) + "\n")
        
        
        M = Miner(HOST,PORT)

        

    except (KeyboardInterrupt, SystemExit):
        sys.exit()