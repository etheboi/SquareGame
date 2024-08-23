import socket
import json
from colorama import Fore, init

init(autoreset=True)

class Plugin:
    def __init__(self):
        print(f"{Fore.LIGHTGREEN_EX}Initializing Plugin...")
        self.name = "SG_Plugin"
        self.version = [1, 0, 0]
        self.description = "A SquareGame Plugin"
        print(f"{Fore.YELLOW}Name: {self.name}\nVersion: {self.version}\nDescription: {self.description}\n{Fore.LIGHTGREEN_EX}Edit these with game.name, game.version and game.description")

    def connect(self, ip: str, port: int):
        self.s = socket.socket()
        try:
            print(f"{Fore.LIGHTGREEN_EX}Connecting to {Fore.YELLOW}{ip}:{str(port)}{Fore.RESET}")
            self.s.connect((ip, port))
            json_data = json.dumps({
                "type": "connect",
                "name": self.name,
                "version": self.version,
                "description": self.description
            })
            self.s.send(json_data.encode())
            print(f"{Fore.LIGHTGREEN_EX}Connected successfully!")
        except Exception as e:
            print(f"{Fore.RED}Error! Unable to connect to server! {e}")

    def send_chat(self, name: str, message: str):
        """
        Sends a message as a player would
        """
        message_data = {
            "type": "chat",
            "name": name,
            "message": message
        }
        self.s.send(json.dumps(message_data).encode())
    
    def send_message(self, message: str):
        """
        Send a message as a Non-Player
        """
        self.s.send(json.dumps({"type": "plugin-message", "message": message, "name": self.name}).encode())
    
    def setblock(self, x: int, y: int, action: str):
        """
        Sets or removes a block at the specified coordinates
        """
        if action.lower() not in ["place", "remove"]:
            raise ValueError("Action must be either 'place' or 'remove'")
        message_data = {
            "type": "block",
            "action": action,
            "x": x,
            "y": y
        }
        self.s.send(json.dumps(message_data).encode())
