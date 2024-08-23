import socket
import threading
import json
import os
import signal
import yaml
import datetime
import sys
import requests
import logging
import time

properties_default = """
# Server Properties

# The max amount of players allowed on 1 server
max-players: 10

# The name of the default world
world-name: world

# The port that the server will be hosted on
server-port: 5555

# true: only players with an account can play on the server
# false: offline players will be able to connect to the server (not reccomended)
online-mode: true
"""

clients = {
    "count": 0
}
filled_cells = set()
server_running = True
server_port = 5555
max_players = 10
world_name = "world"
world_file_path = ""

def get_time():
    datetime_raw = datetime.datetime.now()
    return datetime_raw.strftime("[%d:%m:%Y %H:%M:%S]")

def check_connection():
    try:
        requests.get("https://www.example.com", timeout=2)
        return True
    except requests.ConnectionError:
        return False

def load_world(file_path):
    global filled_cells
    filled_cells = set()
    with open(file_path, "r") as file:
        data = file.read()
    player_data = data.split("/")[1]
    cells_data = data.split("/")[2]
    cells = cells_data.split("\\")
    for cell in cells:
        if cell == "#":
            break
        x, y = map(int, cell.split("."))
        filled_cells.add((x, y))

def save_world():
    global filled_cells, world_name
    world_file_path = f"./{world_name}.sgworld"
    with open(world_file_path, "w") as file:
        file.write("/NONE/")
        for cell in filled_cells:
            file.write(f"{cell[0]}.{cell[1]}\\")
        file.write("#")

def handle_client(client_socket, client_address):
    global clients, filled_cells
    name = None
    try:
        while True:
            data = client_socket.recv(1024).decode("utf-8")
            if data:
                message = json.loads(data)
                
                if message["type"] == "connect":
                    name = message["name"]
                    print(f"{get_time()} Connection from {client_address}")

                    if not online_mode and not message.get("online", True):
                        send_to_client(client_socket, {"type": "error", "message": "This server does not accept offline clients"})
                        client_socket.close()
                        return
                    
                    if name in clients:
                        send_to_client(client_socket, {"type": "error", "message": "Name already exists"})
                        client_socket.close()
                        return
                    
                    clients[name] = {
                        "socket": client_socket,
                        "address": client_address,
                        "x": message.get("x", 0),
                        "y": message.get("y", 0),
                        "facing_right": True
                    }
                    print(f"{get_time()} {name} connected from {client_address}")
                    clients["count"] += 1

                    # Send world data only once upon connection
                    send_to_client(client_socket, {
                        "target": "players",
                        "type": "world",
                        "filled_cells": list(filled_cells)
                    })

                    # Notify all clients of new player joining
                    broadcast({"type": "message", "message": f"{name} joined the server!"})

                elif message["type"] == "position":
                    if name in clients:
                        clients[name]["x"] = message["x"]
                        clients[name]["y"] = message["y"]
                        clients[name]["facing_right"] = message.get("facing_right", True)

                elif message["type"] == "block":
                    x, y = message["x"], message["y"]
                    if message["action"] == "place":
                        filled_cells.add((x, y))
                        broadcast({"type": "place", "x": x, "y": y})
                    elif message["action"] == "remove":
                        filled_cells.discard((x, y))
                        broadcast({"type": "remove", "x": x, "y": y})

                elif message["type"] == "disconnect":
                    print(f"{get_time()} {name} disconnected")
                    clients.pop(name, None)
                    clients["count"] -= 1
                    broadcast({"type": "message", "message": f"{name} left the server!"})
                    break

                elif message["type"] == "chat":
                    # Send chat message once, avoiding multiple broadcasts
                    broadcast({"type": "chat", "name": name, "message": message["message"]})
                    print(f"{get_time()} [{name}]: {message['message']}")

                # Broadcast player updates to all clients
                update_data = {
                    "type": "update",
                    "players": {k: v for k, v in clients.items() if k != name and isinstance(v, dict)},
                    "filled_cells": list(filled_cells)
                }
                broadcast(update_data)

    except (json.JSONDecodeError, socket.error) as e:
        print(f"{get_time()} Error handling client {client_address}: {e}")
        if name:
            clients.pop(name, None)
            clients["count"] -= 1
            broadcast({"type": "message", "message": f"{name} left the server!"})

def broadcast(message):
    for client in clients.values():
        if isinstance(client, dict):
            try:
                client["socket"].send(json.dumps(message).encode("utf-8"))
            except Exception as e:
                print(f"{get_time()} Error broadcasting message: {e}")


def send_to_client(client_socket, message):
    try:
        client_socket.send(json.dumps(message).encode("utf-8"))
    except Exception as e:
        print(f"{get_time()} Error: {e}")

def start_server():
    global server_running, server_port, max_players, world_name, world_file_path
    connection = check_connection()
    if not connection:
        print(f"{get_time()} Error! You are not connected to any networks!")
        stop_server()
        return
    
    world_file_path = f"./{world_name}.sgworld"
    if os.path.exists(world_file_path):
        load_world(world_file_path)
        print(f"{get_time()} Loaded world from {world_file_path}")
    else:
        with open(world_file_path, "w") as file:
            file.write("/NONE/#")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", server_port))
    server_socket.listen(5)
    print(f"{get_time()} Server started on port {server_port}")

    def accept_clients():
        while server_running:
            try:
                client_socket, client_address = server_socket.accept()
                if clients["count"] >= max_players:
                    send_to_client(client_socket, {"type": "error", "message": "Player limit reached"})
                    client_socket.close()
                    print(f"{get_time()} Connection attempt from {client_address} rejected: player limit reached")
                    continue
                client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
                client_thread.start()
            except OSError:
                break

    threading.Thread(target=accept_clients).start()

def stop_server():
    global server_running
    server_running = False
    print(f"{get_time()} Stopping server...")
    
    print(f"{get_time()} Notifying clients...")
    broadcast({"type": "message", "message": "Server is stopping"})
    
    print(f"{get_time()} Kicking all clients...")
    for client in clients.values():
        if isinstance(client, dict):
            client["socket"].close()
    
    print(f"{get_time()} Saving world...")
    save_world()
    
    print(f"{get_time()} Server stopped")
    return

def load_files():
    global server_port, max_players, world_name
    print(f"{get_time()} Loading server")
    print(f"{get_time()} Checking EULA...")
    if os.path.exists("./eula.txt"):
        with open("./eula.txt", "r") as eula_f:
            eula_lines = eula_f.readlines()
        eula_bool = False
        for line in eula_lines:
            if "eula=" in line:
                eula_bool = line.split("=")[1].strip().lower() == "true"
        if eula_bool:
            print(f"{get_time()} EULA confirmed")
        else:
            print(f"{get_time()} Error! EULA has not been accepted, go to 'eula.txt' and change status to 'eula=true'")
            exit(1)
    else:
        with open("./eula.txt", "w") as eula_nf:
            eula_nf.write("EULA for SquareGame server\nRead more at [LINK]\n\neula=false")
            print(f"{get_time()} Please accept the EULA")
            exit(1)
    
    if os.path.exists("./server-properties.yml"):
        with open("./server-properties.yml", "r") as sp_file:
            global server_port, max_players, world_name, online_mode
            properties = yaml.safe_load(sp_file)
            server_port = properties.get("server-port", 5555)
            max_players = properties.get("max-players", 10)
            world_name = properties.get("world-name", "world")
            online_mode = properties.get("online-mode", "true")
            
            print(f"{get_time()} Loaded server properties:\nMax players: {max_players}\nWorld name: {world_name}\nServer port: {server_port}\nonline-mode: {online_mode}")
    else:
        print(f"{get_time()} Generating properties file...")
        with open("./server-properties.yml", "w") as nsp_file:
            nsp_file.write(properties_default)

def signal_handler(sig, frame):
    print(f"{get_time()} Interrupt received, stopping server...")
    stop_server()
    sys.exit(0)

if __name__ == "__main__":
    print(f"{get_time()} Starting log...")
    if not os.path.exists("./logs/"):
        os.mkdir("./logs")
    logging.basicConfig(filename=f"./logs/{get_time()}-log.txt", filemode="w", format="%(message)s")
    logger = logging.getLogger()
    print(f"{get_time()} Logging started!")
    signal.signal(signal.SIGINT, signal_handler)
    load_files()
    start_server()

    while server_running:
        command = input("> ")
        if command.strip().lower() == "stop":
            stop_server()
            break

    print(f"{get_time()} Exiting program.")
    sys.exit(0)

