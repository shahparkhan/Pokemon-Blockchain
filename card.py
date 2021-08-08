from ecdsa import SigningKey
from ecdsa.keys import VerifyingKey

class Card:
    def __init__(self, poke_id, name, poke_type, hp, attack, defense, speed, total, legendary):
        self.poke_id = poke_id
        self.name = name
        self.poke_type = poke_type
        self.hp = hp
        self.attack = attack
        self.defense = defense
        self.speed = speed
        self.total = total
        self.legendary = legendary

    def give_print_str(self, key, value):
        temp_str = key + " " + str(value)
        space_left = 50 - len(temp_str) - 4
        print_str = "| " + temp_str + " "*space_left + " |"
        return print_str

    def view_card(self):          
        print("*******************POKEMON CARD*******************")
        print(self.give_print_str("ID:", self.poke_id))
        print(self.give_print_str("NAME:", self.name))
        print(self.give_print_str("TYPE:", self.poke_type))
        print(self.give_print_str("HP:", self.hp))
        print(self.give_print_str("ATTACK:", self.attack))
        print(self.give_print_str("DEFENSE:", self.defense))
        print(self.give_print_str("SPEED:", self.speed))
        print(self.give_print_str("TOTAL:", self.total))
        print(self.give_print_str("LEGENDARY:", self.legendary))
        print("*******************POKEMON CARD*******************")

