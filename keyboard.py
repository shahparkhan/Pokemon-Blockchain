from pynput.keyboard import Key, Controller
import threading
from time import sleep


def press_something():
    sleep(2)
    keyboard = Controller()
    keyboard.press('a')
    keyboard.release('a')
    keyboard.press(Key.enter)
    keyboard.release(Key.enter)


if __name__ == "__main__":
    print("Enter something: ")
    T1 = threading.Thread(target = press_something).start()
    a = input()
    print("We have pressed: ", a)