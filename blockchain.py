from uuid import uuid4
from hashutils import hash_object
from ecdsa import SigningKey
from ecdsa.keys import VerifyingKey


def public_key_to_str(public_key):
    return public_key.to_string().hex()

def public_key_to_obj(public_key):
    return VerifyingKey.from_string(bytes.fromhex(public_key))

def private_key_to_str(private_key):
    return private_key.to_string().hex()

def private_key_to_obj(private_key):
    return SigningKey.from_string(bytes.fromhex(private_key))

class Block():
    """ Node of the blockchain """
    def __init__(self, content, block_type=None, hash_previous_block=None):
        self.content = content
        self.hash_previous_block = hash_previous_block
        self.type = block_type


    def __str__(self):
        if (self.type == None):
            public_key_sender = public_key_to_str(self.content['public_key_sender'])
            public_key_receiver = public_key_to_str(self.content['public_key_receiver'])

            # + "\nSignature: " + self.content['signature']

            content_string = "**************Block**************\nTransaction ID: " + str(self.content['transaction_id']) + "\nSender: " + public_key_sender + "\nReceiver: " + public_key_receiver + "\n" + str(self.content['pokemon_card_id'])
            return content_string + "\nHash of previous block: " + str(self.hash_previous_block) + "\n**************Block**************\n" 
        else:
            content_string = "**************Genesis Block**************\n" + str(self.content['pokemon_master_key']) + "\n" + str(len(self.content['pokemon_card_id_list'])) + "\n**************Genesis Block**************\n"
            return content_string

class Blockchain():
    """ Blockchain is composed by the blockchain itself
        (represented as an array of blocks), and a series
        of functions to manage it.
    """
    def __init__(self):
        self.blocks = []

    def add_block(self, block):  
        if len(self.blocks) > 0: 
            block.hash_previous_block = hash_object(self.blocks[-1])

        self.blocks.append(block)

    def check_blockchain(self):
        if len(self.blocks) == 0:
            return False
        for i in range(1,len(self.blocks)):
            if (self.blocks[i].hash_previous_block != hash_object(self.block[i-1])):
                return False
        return True

    def __str__(self):
        blockchain_string = ""
        for block in self.blocks:
            blockchain_string = blockchain_string + str(block)
        return blockchain_string
            


    




