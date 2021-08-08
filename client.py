# import blockchain
from ecdsa.keys import VerifyingKey
from hashutils import hash_object
import socket 
import threading
import os
import time
import hashlib
import shutil
from blockchain import Blockchain, Block
from card import Card
import uuid
from json import dumps, loads
import pandas as pd
import numpy as np
import random
from uuid import uuid4
from ecdsa import SigningKey
import getopt
import sys
import zlib
from io import BytesIO


class Trainer:
    def __init__(self, name, host, port):
        self.host = host
        self.port = port
        self.name = name
        self.my_cards = []
        self.blockchain = None
        self.members = {}         # key: member_name, value: (addr, port, public_key)
        self.private_key = SigningKey.generate()    # need to update this
        self.public_key = self.private_key.get_verifying_key()
        
        self.stop = False  # False: User is online

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(None)
        
        self.port = port
        self.sock.bind((host, port))

        self.initial_display()
        self.auctioned_card = {}

        # only for genesis
        self.isGenesis = False
        self.cards = None
        self.card_index = 0


        self.pending_transaction = {} # transaction id: {approved: false, card_add: card, card_remove: card}
        

    
    # Blockchain methods
    #Sign the pokemon card that is up for trade
    def sign(self, hash_pokemon_card_id):
        """ Sign a hash_pokemon_card_id using the private key """
        return self.private_key.sign(hash_pokemon_card_id)

    # Add received block from the miner to the blockchain
    def add_block(self, block):
        self.blockchain.add_block(block)

    def assign_blockchain(self, blockchain):
        self.blockchain = blockchain

    def verify_ownership(self, owner_public_key, card_id):

        for i in reversed(range(len(self.blockchain))):
            contents = self.blockchain[i].contents
            if contents['pokemon_card_id'] == card_id:
                if contents['public_key_receiver'] == owner_public_key:
                    return True
                elif contents['public_key_sender'] == owner_public_key:
                    return False
        
        return False

        
    def public_key_to_str(self, public_key):
        return public_key.to_string().hex()

    def public_key_to_obj(self, public_key):
        return VerifyingKey.from_string(bytes.fromhex(public_key))

    def private_key_to_str(self, private_key):
        return private_key.to_string().hex()

    def private_key_to_obj(self, private_key):
        return SigningKey.from_string(bytes.fromhex(private_key))    
        
    def create_genesis_block(self, pokemon_master_key, pokemon_card_id_list):
        content = {"pokemon_master_key": pokemon_master_key,
                   "pokemon_card_id_list": pokemon_card_id_list}
        block = Block(content, block_type='genesis')
        return block

    # New member joins
    def join(self):
        
        lines = []
        with open('./members.txt', "r") as f:
            lines = f.readlines()
        print("lines: ", lines)
        # genesis
        if lines == []:

            print("here1")
            lines = []
            with open("./pokemons.csv", "r") as f:
                lines = f.readlines()
                lines = lines[1:]
            # striping /n, splitting on ",", specifying legendary as yes or no
            lines = list(map(lambda x: x.rstrip(), lines))
            lines = list(map(lambda x: x.split(","), lines))    
            lines = list(map(lambda x:  x[0:-1]+["No"] if x[-1] == "0"else x[0:-1]+["Yes"], lines))
            
            cards = list(map(lambda x: Card(x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7], x[8]), lines))

            self.isGenesis = True
            self.cards = cards

            f = open("./members.txt", "a")
            temp_string = self.name + "," + self.host + "," + str(self.port) + "," + self.public_key_to_str(self.public_key) + "\n"
            f.write(temp_string)
            f.close()

            genesis_block = self.create_genesis_block(self.public_key, self.cards)
            self.blockchain = Blockchain()
            self.add_block(genesis_block)
            
        else:
            print("here2")
            
            lines = []
            with open("./members.txt", "r") as f:
                lines = f.readlines()
            
            
            lines = list(map(lambda x: x.rstrip(), lines))
            lines = list(map(lambda x: x.split(","), lines))
            
            for i in range(len(lines)):
                self.members[lines[i][0]] = (lines[i][1], int(lines[i][2]), self.public_key_to_obj(lines[i][3]))
            
            message = {"type": "add_member", "name": self.name, "host": self.host, "port": self.port, "public_key": self.public_key_to_str(self.public_key)}
            self.flood(message)

            f = open("./members.txt", "a")
            temp_string = self.name + "," + self.host + "," + str(self.port) + "," + self.public_key_to_str(self.public_key)
            f.write(temp_string)
            f.close()

            rand_port = random.randint(40000, 50000)       
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(None)    
            sock.bind(('localhost', rand_port))
            
            block_chains = []
            block_chains_sizes = []     
            for key, val in self.members.items():
                
                
                message = {"type": "send_blockchain", "host": self.host, "port": rand_port}

                packet = dumps(message).encode("utf-16")

                filename = str(uuid4())
                complete_path = "./temp_files/" + filename + ".bin"

                with open(complete_path, "wb") as f:
                    f.write(packet)

                sock.sendto(filename.encode("utf-8"), ('localhost', val[1]))

                message_byte, _ = sock.recvfrom(4096)
                message = message_byte
                content = loads(message)
                block_chains.append(content["blockchain"])
                block_chains_sizes.append(len(content["blockchain"].blocks))
            
            sock.close()
            index = block_chains.index(max(block_chains_sizes))
            self.blockchain = block_chains[index]

            self.first_ten_cards()

        print("starting action thread")
        # T2 = threading.Thread(target = self.action)
        # T2.daemon = True
        # T2.start()
        self.action()

    def first_ten_cards(self):
        message = {"type": "first_ten_cards", "host": self.host, "port": self.port, "public_key": self.public_key_to_str(self.public_key)}
        genesis = list(self.members.keys())[0]
        self.send_message(message, self.members[genesis][0], self.members[genesis][1])

    # Always listening port
    def listener(self):
        while not self.stop:
            message_byte, _ = self.sock.recvfrom(4096)
            message = message_byte.decode("utf-8")
            self.handleMessage(message)
            # threading.Thread(target = self.handleConnection, args = (client, addr)).start()
        print("Shutting down player: ", self.name , '_', self.host,'_' , self.port)
        try:
            self.sock.shutdown(2)
            self.sock.close()
        except:
            self.sock.close()

    # General function to initiate an action (trade, gift, etc)
    def action(self):
        print("in action1")
        while not self.stop:
            print("in action2")

            user_input = input("input: ")

            input_split = user_input.split(" ")

            if input_split[0] == 'trade': 
                self.trade()
            elif input_split[0] == 'gift':
                self.gift_card()
            elif input_split[0] == 'my_cards':
                self.view_my_cards()
            elif input_split[0] == 'help':
                self.display_help()
            elif input_split[0] == 'view_trade':
                self.view_trade_offers()
            elif input_split[0] == 'exit':
                self.stop = True
            else:
                print("\nThe input keyword is not correct, please type again\n")
                print("\nType 'help' for keyword information...")

    
    # Deals with incoming messages        
    def handleMessage(self, message):
        complete_path = "./temp_files/" + message + ".bin"

        content = None

        with open(complete_path, "rb") as f:
            content = f.read().decode("utf-16")

        content = loads(content)
        
        if content['type'] == "trade":
            print("\nTRADE OFFER!\nHere is the card up for trade\n")
            content['card'].view_card()
            print("\n   'accept'/'reject':  ")
            decision = input()
            if decision == 'accept':
                self.accept_trade(content['addr'], content['port'])
            else:
                self.decline_trade(content['addr'], content['port'])
                

        elif content['type'] == "accept_trade":
            trade_card = list(self.auctioned_card.keys())[0]
            self.auctioned_card[trade_card][(content['name'], content['port'])] = content['card']
            self.check_response_count()

            
        
        elif content['type'] == "decline_trade":
            trade_card = list(self.auctioned_card.keys())[0]
            self.auctioned_card[trade_card][(content['name'], content['port'])] = None
            self.check_response_count()

        elif content['type'] == "verify_ownership":
            check = self.verify_ownership(content["owner_public_key"], content["card_id"])
            
            if check:
                message = {"type": "ownership_verified", "transaction_id": content["transaction_id"], "trade_id": content["trade_id"]}
                self.send_message(message, 'localhost', 10000)
            else:
                message = {"type": "ownership_not_verified", "transaction_id": content["transaction_id"], "trade_id": content["trade_id"]}
                self.send_message(message, 'localhost', 10000)

        elif content['type'] == "add_block":
            self.add_block(content['block'])

        elif content['type'] == "add_member":
            self.members[content['name']] = (content['host'], int(content['port']), self.public_key_to_obj(content['public_key']))
            

        elif content['type'] == "send_blockchain":
            print("my bchain:", self.blockchain)
            
            message = {"type": "blockchain", "blockchain": self.blockchain}
            self.send_message(message, content["host"], content["port"])

        elif content['type'] == "first_ten_cards":
            self.initialize_cards(content["host"], content["port"], content["public_key"])

        elif content['type'] == "transaction_approved":
            self.approve_transaction(content["transaction_id"])

        elif content['type'] == "add_initial_card":
            self.my_cards.append(content["card"])

    def approve_transaction(self, transaction_id):
        self.pending_transaction[transaction_id]["approve"] = True
        self.my_cards.remove(self.pending_transaction[transaction_id]["card_add"])
        self.my_cards.remove(self.pending_transaction[transaction_id]["card_remove"])


    def initialize_cards(self, host, port, public_key_receiver):
        ten_cards = self.cards[self.card_index: (self.card_index+10)]
        self.card_index = self.card_index + 10

        for card in ten_cards:
            message = {"type": "send_ten_cards", "card": card, "host": host, "port": port, "public_key_sender": self.public_key, "public_key_receiver":  public_key_receiver, "pokemon_card_id": card.poke_id, "hash_pokemon_card_id": hash_object(card.poke_id), "signature": self.sign(hash_object(card.poke_id))}

            self.send_message(message, 'localhost', 10000)

    # Checks whether each member has responded to the auctioned card
    def check_response_count(self):
        if len(list(self.members.keys())) == len(list(self.auction_card[list(self.auctioned_card.keys())[0]].keys())):
            self.evaluate_auction()

    def evaluate_auction(self):
        trade_card = list(self.auctioned_card.keys())[0]
        
        print("\n!___WOOHOO! All members have responded to trade offer__!\n")
        print("\nYour card:\n")
        trade_card.view_card()
        print("\nCards offered for trade against your card:\n")
        
        for card in list(self.auctioned_card[trade_card].values()):
            if card != None:
                card.view_card()
                print("\n")
            
        print("\nEnter the ID of card you want to accept trade of\n")
        print("\nOtherwise enter 999\n")

        user_input = input()

        if user_input != "999":
            temp_card = None
            temp_name_port = None
            temp_public_key = None
            temp_trade_number = uuid4()

            for key, val in self.auctioned_card[trade_card]:
                if val != None:
                    if val.poke_id == user_input:
                        temp_card = val
                        temp_name_port = key

            for key, val in self.members:
                if key == temp_name_port[0]:
                    temp_public_key = val[2]

            sender_txn_id = uuid4()
            receiver_txn_id = uuid4()

            self.pending_transaction[sender_txn_id] = {"approve": False, "card_add": temp_card, "card_remove": trade_card}
            

            temp_dict = {"approve": False, "card_add": trade_card, "card_remove": temp_card}
            message = {"type": "add_pending_transaction", "transaction_id": receiver_txn_id, "transaction_content": temp_dict}
            self.send_message(message, 'localhost', temp_name_port[1])

            message_1 = {"type":"transaction","public_key_sender": self.public_key, "public_key_receiver":  temp_public_key, "pokemon_card_id": trade_card.poke_id, "hash_pokemon_card_id": hash_object(trade_card.poke_id), "port": self.port, "trade_id": temp_trade_number, "transaction_id": sender_txn_id, "signature": self.sign(hash_object(trade_card.poke_id))}
            message_2 = {"type":"transaction", "public_key_sender": temp_public_key, "public_key_receiver":  self.public_key, "pokemon_card_id": temp_card.poke_id, "hash_pokemon_card_id": hash_object(temp_card.poke_id), "port": temp_name_port[1], "trade_id": temp_trade_number, "transaction_id": receiver_txn_id, "signature": self.sign(hash_object(temp_card.poke_id))}
            
            self.send_message(message_1, 'localhost', 10000)
            self.send_message(message_2, 'localhost', 10000)

    # Adds selfs credentials to text file upon join
    def add_to_txt(self, name, host, port):
        with open("./members.txt", 'a') as my_file:
            to_write = name + ',' + 'localhost' + ',' + str(port) + ',' + str(self.public_key) 
            my_file.write(to_write)
            # lines = my_file.readlines()
            # for line in lines:
            #     temp = line.split(",")
            #     # check is self.name already exists in memebrs.txt
            #     if temp[0] == name:
            #         print("\nName already taken, type new name")
                    
                
                
                
    # Reads already joined members and returs dictionay
    # key: member name, value: other attributes 
    def read_text(self):
        members_info = {}
        with open("./members.txt", 'r') as my_file:
            lines = my_file.readlines
            for line in lines:
                temp = line.split(',')
                member = temp.pop(0)
                members_info[member] = temp
        return members_info
    
    # Sends message to all members
    def flood(self, message):
        print(self.members)
        for key, val in self.members.items():
            self.send_message(message, val[0], val[1])

    # Put for trade
    def trade(self, card):
        print("\nCards list:\n")
        self.view_my_cards()
        print("\nEnter Card Pokemon ID: ")
        poke_ID = int(input())
        for card in self.my_cards:
            if card.poke_id == poke_ID:
                message = {"type":"trade", "addr":"localhost", 'port':self.port, 'card': card}
                self.auctioned_cards[card] = {}
                self.flood(message)
            else:
                print("!__Invalid Pokemon ID entered__!")

         
    # Bid card against a card on auction
    def bid_card(self, addr, port):
        print("\nCards list:\n")
        self.view_my_cards()
        print("\nEnter Card Pokemon ID: ")
        poke_ID = input()
        for card in self.my_cards:
            if card.poke_id == poke_ID:
                message = {"type":"trade", "addr":"localhost", 'port':self.port, 'card': card}
                self.send_message(message, addr, port)
            else:
                print("!__Invalid Pokemon ID entered__!")
    
    # Accept a card trade. Generate a block
    def accept_trade(self, addr, port):
        print("\nCards list:\n")
        
        self.view_my_cards()
        
        print("\nEnter Card Pokemon ID you want to give for trade: \n")
        
        poke_ID = input()
        
        for card in self.my_cards:
            if card.poke_id == poke_ID:
                message = {"type":"accept_trade", "name": self.name, "addr":"localhost", 'port':self.port, 'card': card}
                self.send_message(message, addr, port)
        else:
            print("!__Invalid Pokemon ID entered__!")
            self.decline_trade(addr, port)

    # Decline a card trade
    def decline_trade(self, addr, port):
        message = {"type":"decline_trade", "name": self.name, "addr":"localhost", 'port':self.port}
        self.send_message(message, addr, port)
    
    # View my cards
    def view_my_cards(self):
        for card in self.my_cards:
            card.view_card()
            print("\n")
    
    # View all trade offers
    def view_trade_offers(self):
        print()
    
    # Gift a card
    def gift_card(self):
        members_info = self.read_text()
        
        print("\n Type the member you want to gift card\n ")
        print(list(members_info.keys()))
        chosen_member = input()
        
        print("\n Enter Card Name to gift\n")
        self.view_my_cards()
        card_name = input()
        
    def send_message(self, content, addr, port):
        packet = dumps(content).encode("utf-16")

        filename = str(uuid4())
        complete_path = "./temp_files/" + filename + ".bin"

        with open(complete_path, "wb") as f:
            f.write(packet)

        # self.sock.connect((addr, port))
        self.sock.sendto(filename.encode("utf-8"), (addr, port))

    
    
    # Display the possible actions and format for the user's reference
    def initial_display(self):
        print("*****__Welcome to Pokemon Card Trading Marketplace__*****")
        print("\nHello Pokemon Trainer ", self.name, ", here is how you become a Pokemon Master\n")
        print("Option 1: Trade a card- type 'trade'\n")
        print("Option 2: Gift a card - type 'gift' \n")
        print("Option 3: View Cards - type 'my cards'\n")
        print("Option 4: Get Help - type 'help'\n")
        print("Option 5: View trade offers - type 'view trade'\n")
        print("Option 6: Exit - type 'exit' ")
        print("Disclamer --> Exiting will permanently result in loosing cards")
        print("Also be on a lookout for trade requests, you don't waant to miss out on that fantastic deal!\n")
        
    def display_help(self):
        print("\nDo not worry Pokemon trainer :P, we are here to help!\n")
        print("Here are the options available:\n")
        print("Option 1: Trade a card- type 'trade'\n")
        print("Option 2: Gift a card - type 'gift' \n")
        print("Option 3: View Cards - type 'my cards'\n")
        print("Option 4: Get Help - type 'help'\n")
        print("Option 5: View trade offers - type 'view trade'\n")
        print("Option 6: Exit - type 'exit' ")
        




# Do not change this part of code
if __name__ == "__main__":
    def helper():
        '''
        This function is just for the sake of our Client module completion
        '''
        
        print("-u username | --user=username The username of Client")
        print("-h | --help Print this help")
    try:
        OPTS, ARGS = getopt.getopt(sys.argv[1:],
                                   "u:", ["user="])
    except getopt.error:
        helper()
        exit(1)

    PORT =  random.randint(11000, 40000)
    DEST = "localhost"
    USER_NAME = None
    WINDOW_SIZE = 3
    for o, a in OPTS:
        if o in ("-u", "--user="):
            USER_NAME = a

    if USER_NAME is None:
        print("Missing Username.")
        helper()
        exit(1)

    # create trainer class instance
    S = Trainer(USER_NAME, DEST, PORT)
    
    try:

        # Start receiving Messages
        T1 = threading.Thread(target = S.listener)
        T1.daemon = True
        T1.start()
        
        # initializations
        # S.add_to_txt(USER_NAME, DEST, PORT)
        S.initial_display()
        

        # Start Action Window
        S.join()

        # T2 = threading.Thread(target = S.action)
        # T2.daemon = True
        # T2.start()

    except (KeyboardInterrupt, SystemExit):
        sys.exit()