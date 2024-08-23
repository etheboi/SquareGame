import json
import socket

class onBlockPlace:
    def __init__(self, game):
        self.blockPlace_callback = None
        self.cancel = False
        self.socket = game.s
        self.listening = False
        
    def register(self, callback):
        if callable(callback):
            self.blockPlace_callback = callback
        else:
            raise ValueError("Callback must be callable!")
    
    def join(self):
        self.listening = True
        while self.listening:
            try:
                response = json.loads(self.socket.recv(1024).decode("utf-8"))
                if response["type"] == "place":
                    event = Event(response)
                    actions = []
                    if self.cancel:
                        actions.append("event.cancel")
                    self.socket.send(json.dumps({"type": "place", "actions": actions}).encode("utf-8"))
                    
                    if self.blockPlace_callback:
                        self.blockPlace_callback(event)
            except (json.JSONDecodeError, socket.error) as e:
                print(f"Error receiving data: {e}")
                self.listening = False
                
    def leave(self):
        self.listening = False

    def cancel_event(self):
        self.cancel = True
        
class Event:
    def __init__(self, response):
        self.name = response.get("name", "")
        self.x = response.get("x", "")
        self.y = response.get("y", "")

