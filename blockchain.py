from uuid import uuid4
from hashutils import hash_object

class Block():
    """ Node of the blockchain """
    def __init__(self, content, block_type=None, hash_previous_block=None):
        self.content = content
        self.hash_previous_block = hash_previous_block
        self.type = block_type


    def __str__(self):
        if (self.type == None):
            content_string = "**************\nTransaction ID: " + str(self.content['transaction_id']) + "\nSender: " + self.content['public_key_sender'] + "\nReceiver: " + self.content['public_key_receiver'] + "\nSignature: " + self.content['signature']
            return content_string + "\nHash of previous block: " + str(self.hash_previous_block + "\n*******")
        else:
            content_string = "**************\nGenesis Block\n" + str(self.content['pokemon_master_key']) + "\n" + str(len(self.content['pokemon_card_id_list']))
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


    




