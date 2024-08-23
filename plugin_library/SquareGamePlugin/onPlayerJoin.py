import json
import socket

class onPlayerJoin:
    def __init__(self, game):
        self.playerJoin_callback = None
        self.cancel = False
        self.cancel_message = "Blocked by plugin"
        self.join_message = False
        self.socket = game.s
        self.listening = False
        
    def register(self, callback):
        if callable(callback):
            self.playerJoin_callback = callback
        else:
            raise ValueError("Callback must be callable!")
    
    def join(self):
        self.listening = True
        while self.listening:
            try:
                response = json.loads(self.socket.recv(1024).decode("utf-8"))
                if response["target"] == "plugins" and response["type"] == "connect":
                    event = Event(response)
                    actions = []
                    if self.cancel:
                        actions.append(f"event.cancel:{self.cancel_message}")
                    if self.join_message:
                        actions.append(f"join_message:{self.join_message}")
                    self.socket.send(json.dumps({"type": "join", "actions": actions}).encode("utf-8"))
                    
                    if self.playerJoin_callback:
                        self.playerJoin_callback(event)
            except (json.JSONDecodeError, socket.error) as e:
                print(f"Error receiving data: {e}")
                self.listening = False
                
    def leave(self):
        self.listening = False
    
    def cancel_event(self):
        self.cancel = True
        
    def set_cancel_message(self, message: str):
        self.cancel_message = message
        
    def set_join_message(self, message: str):
        self.join_message = message
                
class Event:
    def __init__(self, response):
        self.name = response.get("name", "")

