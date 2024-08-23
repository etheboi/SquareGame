import json
import socket

class onPlayerLeave:
    def __init__(self, game):
        self.playerLeave_callback = None
        self.leave_message = None
        self.socket = game.s
        self.listening = False
        
    def register(self, callback):
        if callable(callback):
            self.playerLeave_callback = callback
        else:
            raise ValueError("Callback must be callable!")
    
    def join(self):
        self.listening = True
        while self.listening:
            try:
                response = json.loads(self.socket.recv(1024).decode("utf-8"))
                if response["type"] == "disconnect":
                    event = Event(response)
                    actions = {}
                    if self.leave_message:
                        actions["leave_message"] = self.leave_message
                    self.socket.send(json.dumps({"type": "leave", "actions": actions}).encode("utf-8"))
                    
                    if self.playerLeave_callback:
                        self.playerLeave_callback(event)
            except (json.JSONDecodeError, socket.error) as e:
                print(f"Error receiving data: {e}")
                self.listening = False
                
    def leave(self):
        self.listening = False

    def set_leave_message(self, message: str):
        self.leave_message = message
        
class Event:
    def __init__(self, response):
        self.name = response.get("name", "")

