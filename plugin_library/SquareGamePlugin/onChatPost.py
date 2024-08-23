import json
import socket

class onChatPost:
    def __init__(self, game):
        self.chatpost_callback = None
        self.cancel = False
        self.socket = game.s
        self.listening = False

    def register(self, callback):
        if callable(callback):
            self.chatpost_callback = callback
        else:
            raise ValueError("Callback must be callable!")

    def join(self):
        self.listening = True
        while self.listening:
            response = json.loads(self.socket.recv(1024).decode("utf-8"))
            if response["type"] == "chat":
                event = Event(response)
                if self.cancel:
                    self.socket.send(json.dumps({"type":"chat","actions": ["event.cancel"]}).encode("utf-8"))

            if self.chatpost_callback:
                self.chatpost_callback(event)

    def leave(self):
        self.listening = False

    def cancel_event(self):
        self.cancel = True

class Event:
    def __init__(self, response):
        self.message = response.get("message", "")
        self.author = response.get("name", "")
