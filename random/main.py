import pygame
import argparse
import importlib
import sys
import math
import subprocess
import threading
import tkinter as tk
from tkinter import simpledialog, filedialog, messagebox
import os
import socket
import json
import shutil

# Set up argparse to handle command-line arguments
parser = argparse.ArgumentParser(description="Arguments")
parser.add_argument("-dont_modify_cursor", action="store_true", help="Disable cursor modification")
parser.add_argument("-variables", type=str, help="The module to load variables from")
parser.add_argument("-framerate", type=int, help="The max framerate")
parser.add_argument("-countframerate", action="store_true", help="Display the framerate counter")
parser.add_argument("-show_coordinates", action="store_true", help="Display the players coordinates")
parser.add_argument("-name", type=str, help="Player's name")
parser.add_argument("-show_hitboxes", action="store_true", help="Display hitboxes around player and filled cells")
parser.add_argument("-launcher", action="store_true", help="Launch the launcher on exit")
parser.add_argument("-email", type=str)
parser.add_argument("-offline", action="store_true")
args = parser.parse_args()

# Default values
PLAYER_SIZE = 40
MAX_SPEED = 10
ACCELERATION = 1
DECELERATION = 1
JUMP_HEIGHT = 15
GRAVITY = 1
REACH = 5

# List of required variable names
required_vars = ["PLAYER_SIZE", "MAX_SPEED", "ACCELERATION", "DECELERATION", "JUMP_HEIGHT", "GRAVITY", "REACH"]

if args.variables:
    try:
        # Dynamically import the module specified in the command-line argument
        variables_module = importlib.import_module(args.variables)
        
        # Update variables if they exist in the imported module
        for var in required_vars:
            if hasattr(variables_module, var):
                globals()[var] = getattr(variables_module, var)
    except ImportError:
        sys.exit(1)

# Initialize Pygame
pygame.init()

clock = pygame.time.Clock()
pygame.font.init()
font = pygame.font.Font(None, 36)
name_font = pygame.font.Font(None, 24)

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PLATFORM_HEIGHT = 50
GRID_CELL_SIZE = 50

# Colors
RED = (255, 0, 0)
GREEN = (0, 255, 0)
GRAY = (128, 128, 128)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)  # New color for hitbox outlines
TRANSPARENT_BLACK = (0, 0, 0, 128)  # Transparent black for chat box background

connection_status = ""

# Screen setup
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("SquareGame")

# Load textures
player_idle = pygame.image.load("./assets/player_idle.png")
player_walking_ph1 = pygame.image.load("./assets/player_walk_ph1.png")
player_walking_ph2 = pygame.image.load("./assets/player_walk_ph2.png")
cursor_image = pygame.image.load("./assets/cursor.png")

# Player starting position
player_x = SCREEN_WIDTH // 2 - PLAYER_SIZE // 2
player_y = SCREEN_HEIGHT - PLATFORM_HEIGHT - PLAYER_SIZE  # Adjusted to avoid overlap

# Movement variables
velocity_x = 0
velocity_y = 0
is_jumping = False
is_on_platform = True

# Animation variables
walking_animation_frames = [player_walking_ph1, player_walking_ph2]
current_frame = 0
frame_time = 0.3  # Time in seconds for each frame
last_frame_update_time = 0
is_moving_left = False
is_moving_right = False
facing_right = False

# Grid system variables
grid_cols = SCREEN_WIDTH // GRID_CELL_SIZE
grid_rows = (SCREEN_HEIGHT - PLATFORM_HEIGHT) // GRID_CELL_SIZE
selected_cell_x = 0
selected_cell_y = 0
filled_cells = set()

# Track if left or right mouse button is held down
left_mouse_held = False
right_mouse_held = False

# Pause UI variables
paused = False
pause_buttons = []
button_font = pygame.font.Font(None, 36)

# Multiplayer UI variables
multiplayer_mode = False
ip_input_box = None
ip_address = ""
connect_button_rect = None

# Main Menu variables
main_menu = True
singleplayer_menu = False

# Track current world file
current_world_file = None

# Networking variables
client_socket = None
connected_to_server = False
server_response_thread = None
players = {}

# Chat box variables
chat_mode = False
chat_input = ""
messages = []

def connect_to_server(ip, port):
    global client_socket, connected_to_server, server_response_thread, connection_status
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((ip, port))
        connected_to_server = True
        connection_status = "Connected to server"
        server_response_thread = threading.Thread(target=handle_server_responses)
        server_response_thread.start()
        send_to_server({"type": "connect", "name": args.name, "x": player_x, "y": player_y, "online": {False if args.offline else True}})
        return True
    except Exception as e:
        connection_status = f"Connection failed: {e}"
        return False

def handle_server_responses():
    global running, players, filled_cells, messages, connected_to_server
    while running:
        try:
            data = client_socket.recv(1024).decode("utf-8")
            if data:
                message = json.loads(data)
                if message["target"] == "players":
                    if message["type"] == "update":
                        players = message["players"]
                        filled_cells = set(tuple(cell) for cell in message["filled_cells"])
                    elif message["type"] == "disconnect":
                        players.pop(message["name"], None)
                    elif message["type"] == "chat":
                        messages.append(f"{message["name"]}: {message["message"]}")
                    elif message["type"] == "message":
                        messages.append(message["message"])
                    elif message["type"] == "place":
                        filled_cells.add((message["x"], message["y"]))
                    elif message["type"] == "remove":
                        filled_cells.discard((message["x"], message["y"]))
                    elif message["type"] == "error":
                        connection_status = message["message"]
                        running = False
                        break
                    
        except:
            running = False
            break
            
    connected_to_server = False
    client_socket.close()

def send_to_server(data):
    if connected_to_server:
        try:
            client_socket.send(json.dumps(data).encode("utf-8"))
        except:
            pass

def disconnect_from_server():
    global connected_to_server, client_socket
    if connected_to_server:
        client_socket.close()
        connected_to_server = False

def check_collision(rect, cells):
    collisions = []
    for cell in cells:
        cell_rect = pygame.Rect(cell[0] * GRID_CELL_SIZE, cell[1] * GRID_CELL_SIZE, GRID_CELL_SIZE, GRID_CELL_SIZE)
        if rect.colliderect(cell_rect):
            collisions.append(cell_rect)
    return collisions

def clamp_cursor_position(x, y):
    return max(0, min(SCREEN_WIDTH, x)), max(0, min(SCREEN_HEIGHT, y))

def get_player_coordinates(x, y):
    return f"Coordinates: X: {x}, Y: {y}"

def reset_game():
    global player_x, player_y, velocity_x, velocity_y, is_jumping, is_on_platform, filled_cells, current_world_file
    player_x = SCREEN_WIDTH // 2 - PLAYER_SIZE // 2
    player_y = SCREEN_HEIGHT - PLATFORM_HEIGHT - PLAYER_SIZE  # Adjusted to avoid overlap
    velocity_x = 0
    velocity_y = 0
    is_jumping = False
    is_on_platform = True
    filled_cells.clear()
    current_world_file = None

def load_world(file_path):
    global filled_cells, current_world_file, player_x, player_y
    filled_cells = set()
    with open(file_path, "r") as file:
        data = file.read()
    player_data, cells_data = data.split("/")
    player_x, player_y = map(int, player_data.split("-"))
    cells = cells_data.split("\\")
    for cell in cells:
        if cell == "#":
            break
        x, y = map(int, cell.split("."))
        filled_cells.add((x, y))
    current_world_file = file_path

def save_world(file_name=None):
    global filled_cells, current_world_file
    if file_name:
        current_world_file = file_name
    if current_world_file:
        with open(current_world_file, "w") as file:
            file.write(f"{player_x}-{player_y}/")
            for cell in filled_cells:
                file.write(f"{cell[0]}.{cell[1]}\\")
            file.write("#")
        show_messagebox("Success", f"World saved as {current_world_file}")

def draw_main_menu():
    menu_buttons = ["Singleplayer", "Multiplayer", "Quit"]
    button_width = 200
    button_height = 50
    button_spacing = 20
    total_height = len(menu_buttons) * (button_height + button_spacing) - button_spacing
    start_y = (SCREEN_HEIGHT - total_height) // 2

    for i, text in enumerate(menu_buttons):
        x = (SCREEN_WIDTH - button_width) // 2
        y = start_y + i * (button_height + button_spacing)
        button_rect = pygame.Rect(x, y, button_width, button_height)
        pygame.draw.rect(screen, WHITE, button_rect)
        button_text = button_font.render(text, True, BLACK)
        screen.blit(button_text, (x + (button_width - button_text.get_width()) // 2, y + (button_height - button_text.get_height()) // 2))
        menu_buttons[i] = (button_rect, text)

    return menu_buttons

def draw_singleplayer_menu():
    menu_buttons = ["New World", "Load World", "Back"]
    button_width = 200
    button_height = 50
    button_spacing = 20
    total_height = len(menu_buttons) * (button_height + button_spacing) - button_spacing
    start_y = (SCREEN_HEIGHT - total_height) // 2

    for i, text in enumerate(menu_buttons):
        x = (SCREEN_WIDTH - button_width) // 2
        y = start_y + i * (button_height + button_spacing)
        button_rect = pygame.Rect(x, y, button_width, button_height)
        pygame.draw.rect(screen, WHITE, button_rect)
        button_text = button_font.render(text, True, BLACK)
        screen.blit(button_text, (x + (button_width - button_text.get_width()) // 2, y + (button_height - button_text.get_height()) // 2))
        menu_buttons[i] = (button_rect, text)

    return menu_buttons

def draw_pause_ui():
    global pause_buttons
    pause_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    pause_overlay.set_alpha(128)  # Semi-transparent overlay
    pause_overlay.fill(BLACK)
    screen.blit(pause_overlay, (0, 0))

    button_texts = ["Resume", "Save", "New Game", "Quit"]
    button_width = 200
    button_height = 50
    button_spacing = 20
    total_height = len(button_texts) * (button_height + button_spacing) - button_spacing
    start_y = (SCREEN_HEIGHT - total_height) // 2

    pause_buttons = []

    for i, text in enumerate(button_texts):
        x = (SCREEN_WIDTH - button_width) // 2
        y = start_y + i * (button_height + button_spacing)
        button_rect = pygame.Rect(x, y, button_width, button_height)
        pause_buttons.append((button_rect, text))

        pygame.draw.rect(screen, WHITE, button_rect)
        button_text = button_font.render(text, True, BLACK)
        screen.blit(button_text, (x + (button_width - button_text.get_width()) // 2, y + (button_height - button_text.get_height()) // 2))

def draw_multiplayer_ui():
    global ip_input_box, connect_button_rect, ip_address
    multiplayer_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    multiplayer_overlay.set_alpha(128)  # Semi-transparent overlay
    multiplayer_overlay.fill(BLACK)
    screen.blit(multiplayer_overlay, (0, 0))

    label_font = pygame.font.Font(None, 36)
    input_font = pygame.font.Font(None, 24)

    # Draw label
    label_text = label_font.render("Server IP address", True, WHITE)
    label_rect = label_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40))
    screen.blit(label_text, label_rect)

    # Draw input box
    ip_input_box = pygame.Rect(SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2, 300, 50)
    pygame.draw.rect(screen, WHITE, ip_input_box)
    
    # Render the IP address text
    ip_text = input_font.render(ip_address, True, BLACK)
    screen.blit(ip_text, (ip_input_box.x + 10, ip_input_box.y + 10))

    # Draw connect button
    connect_button_rect = pygame.Rect(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 60, 200, 50)
    pygame.draw.rect(screen, WHITE, connect_button_rect)
    connect_button_text = input_font.render("Connect", True, BLACK)
    screen.blit(connect_button_text, (connect_button_rect.x + (connect_button_rect.width - connect_button_text.get_width()) // 2, connect_button_rect.y + (connect_button_rect.height - connect_button_text.get_height()) // 2))

def show_file_dialog():
    os.chdir("../../worlds")
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(filetypes=[("SG World files", "*.sgworld")])
    root.destroy()
    os.chdir("../launcher/extracted_temp/")
    return file_path

def show_messagebox(title, message):
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(title, message)
    root.destroy()

def show_text_input(title, prompt):
    root = tk.Tk()
    root.withdraw()
    user_input = simpledialog.askstring(title, prompt)
    root.destroy()
    return user_input

def handle_load_world():
    file_path = show_file_dialog()
    if file_path:
        load_world(file_path)

def handle_save_world():
    global current_world_file
    if current_world_file is None:
        file_name = show_text_input("Save World", "Enter world name:")
        if file_name:
            save_world(f"./worlds/{file_name}.sgworld")
    else:
        save_world()

def send_message(message):
    if connected_to_server:
        send_to_server({"type": "chat", "name": args.name, "message": message})
    messages.append(f"{args.name}: {message}")

def draw_chat_ui():
    chat_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    chat_overlay.set_alpha(128)  # Semi-transparent overlay
    chat_overlay.fill(BLACK)
    screen.blit(chat_overlay, (0, 0))

    chat_box_rect = pygame.Rect(10, SCREEN_HEIGHT - 150, 780, 140)
    pygame.draw.rect(screen, TRANSPARENT_BLACK, chat_box_rect)

    chat_font = pygame.font.Font(None, 24)
    input_font = pygame.font.Font(None, 24)
    
    # Draw chat messages
    for i, msg in enumerate(messages[-6:]):
        msg_text = chat_font.render(msg, True, WHITE)
        screen.blit(msg_text, (20, SCREEN_HEIGHT - 140 + i * 20))

    # Draw input box
    input_box_rect = pygame.Rect(20, SCREEN_HEIGHT - 30, 760, 20)
    pygame.draw.rect(screen, WHITE, input_box_rect)
    input_text = input_font.render(chat_input, True, BLACK)
    screen.blit(input_text, (25, SCREEN_HEIGHT - 28))

# Main loop
running = True
mouse_clamped = True
menu_buttons = []
singleplayer_menu_buttons = []
while running:
    is_jumping = True
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            if connected_to_server:
                send_to_server({"type": "disconnect", "name": args.name})
                disconnect_from_server()
        elif event.type == pygame.KEYDOWN:
            if chat_mode:
                if event.key == pygame.K_RETURN:
                    send_message(chat_input)
                    chat_input = ""
                    chat_mode = False
                elif event.key == pygame.K_BACKSPACE:
                    chat_input = chat_input[:-1]
                else:
                    chat_input += event.unicode
            else:
                if event.key == pygame.K_SPACE and is_on_platform:
                    is_jumping = True
                    velocity_y = -JUMP_HEIGHT
                    is_on_platform = False
                elif event.key == pygame.K_ESCAPE:
                    if chat_mode:
                        chat_mode = False
                    elif paused:
                        paused = False
                        mouse_clamped = True
                    else:
                        paused = not paused
                        mouse_clamped = not paused
                        pygame.mouse.set_visible(paused)
                elif event.key == pygame.K_t and not paused:
                    chat_mode = True
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if main_menu:
                mouse_x, mouse_y = event.pos
                for button_rect, text in menu_buttons:
                    if button_rect.collidepoint(mouse_x, mouse_y):
                        if text == "Singleplayer":
                            main_menu = False
                            singleplayer_menu = True
                        elif text == "Multiplayer":
                            main_menu = False
                            multiplayer_mode = True
                        elif text == "Quit":
                            running = False
            elif singleplayer_menu:
                mouse_x, mouse_y = event.pos
                for button_rect, text in singleplayer_menu_buttons:
                    if button_rect.collidepoint(mouse_x, mouse_y):
                        if text == "New World":
                            singleplayer_menu = False
                            paused = False
                            reset_game()
                        elif text == "Load World":
                            threading.Thread(target=handle_load_world).start()
                            singleplayer_menu = False
                            paused = False
                        elif text == "Back":
                            singleplayer_menu = False
                            main_menu = True
            elif not paused and not multiplayer_mode:
                if event.button == 1:  # Left click
                    left_mouse_held = True
                elif event.button == 3:  # Right click
                    right_mouse_held = True
            elif paused:
                mouse_x, mouse_y = event.pos
                for button_rect, text in pause_buttons:
                    if button_rect.collidepoint(mouse_x, mouse_y):
                        if text == "Resume":
                            paused = False
                            mouse_clamped = True
                        elif text == "Save":
                            threading.Thread(target=handle_save_world).start()
                        elif text == "New Game":
                            reset_game()
                            paused = False
                            mouse_clamped = True
                        elif text == "Quit":
                            main_menu = True
                            paused = False
            elif multiplayer_mode:
                mouse_x, mouse_y = event.pos
                if connect_button_rect and connect_button_rect.collidepoint(mouse_x, mouse_y):
                    screen.fill(BLACK)
                    locating_text = font.render("Locating server...", True, WHITE)
                    screen.blit(locating_text, ((SCREEN_WIDTH - locating_text.get_width()) // 2, (SCREEN_HEIGHT - locating_text.get_height()) // 2))
                    pygame.display.flip()
                    try:
                        ip, port = ip_address.split(":")
                        port = int(port)
                        if connect_to_server(ip, port):
                            main_menu = False
                            multiplayer_mode = False
                            paused = False
                            connection_status = ""
                        else:
                            error_text = font.render(connection_status, True, RED)
                            screen.blit(error_text, ((SCREEN_WIDTH - error_text.get_width()) // 2, (SCREEN_HEIGHT - error_text.get_height()) // 2))
                            pygame.display.flip()
                            pygame.time.wait(2000)
                    except ValueError:
                        error_text = font.render("Invalid IP address or port", True, RED)
                        screen.blit(error_text, ((SCREEN_WIDTH - error_text.get_width()) // 2, (SCREEN_HEIGHT - error_text.get_height()) // 2))
                        pygame.display.flip()
                        pygame.time.wait(2000)
        elif event.type == pygame.MOUSEBUTTONUP:
            if not paused and not multiplayer_mode:
                if event.button == 1:  # Left click
                    left_mouse_held = False
                elif event.button == 3:  # Right click
                    right_mouse_held = False
        elif event.type == pygame.TEXTINPUT and multiplayer_mode:
            ip_address += event.text
        elif event.type == pygame.KEYDOWN and multiplayer_mode:
            if event.key == pygame.K_BACKSPACE or pygame.K_DELETE:
                ip_address = ip_address[0:-1]
            elif event.key != pygame.K_ESCAPE:  # Prevent escape from adding to the input
                ip_address += event.unicode

    if main_menu:
        screen.fill(BLACK)
        menu_buttons = draw_main_menu()
    elif singleplayer_menu:
        screen.fill(BLACK)
        singleplayer_menu_buttons = draw_singleplayer_menu()
    elif not paused and not multiplayer_mode and not chat_mode:
        # Mouse hover detection
        mouse_x, mouse_y = pygame.mouse.get_pos()
        if mouse_clamped:
            mouse_x, mouse_y = clamp_cursor_position(mouse_x, mouse_y)
            pygame.mouse.set_pos(mouse_x, mouse_y)

        selected_cell_x = mouse_x // GRID_CELL_SIZE
        selected_cell_y = mouse_y // GRID_CELL_SIZE

        # Calculate the distance from the player to the selected cell
        player_center_x = player_x + PLAYER_SIZE // 2
        player_center_y = player_y + PLAYER_SIZE // 2
        selected_cell_center_x = selected_cell_x * GRID_CELL_SIZE + GRID_CELL_SIZE // 2
        selected_cell_center_y = selected_cell_y * GRID_CELL_SIZE + GRID_CELL_SIZE // 2

        distance = math.sqrt((selected_cell_center_x - player_center_x) ** 2 + (selected_cell_center_y - player_center_y) ** 2)
        max_reach_distance = REACH * GRID_CELL_SIZE

        # Determine if the selected cell is within reach
        within_reach = distance <= max_reach_distance

        # Place block if left mouse button is held down and within reach
        if right_mouse_held and within_reach:
            player_rect = pygame.Rect(player_x, player_y, PLAYER_SIZE, PLAYER_SIZE)
            selected_cell_rect = pygame.Rect(selected_cell_x * GRID_CELL_SIZE, selected_cell_y * GRID_CELL_SIZE, GRID_CELL_SIZE, GRID_CELL_SIZE)
            if not player_rect.colliderect(selected_cell_rect):
                filled_cells.add((selected_cell_x, selected_cell_y))
                send_to_server({"type": "block", "action": "place", "x": selected_cell_x, "y": selected_cell_y})

        # Remove block if right mouse button is held down and within reach
        if left_mouse_held and within_reach:
            filled_cells.discard((selected_cell_x, selected_cell_y))
            send_to_server({"type": "block", "action": "remove", "x": selected_cell_x, "y": selected_cell_y})

        # Key states
        keys = pygame.key.get_pressed()

        # Horizontal movement with acceleration
        if keys[pygame.K_a]:
            is_moving_left = True
            is_moving_right = False
            facing_right = False
            if keys[pygame.KMOD_SHIFT] & pygame.KMOD_LSHIFT:
                velocity_x -= 2 * ACCELERATION  # Sprint speed (double acceleration)
            else:
                velocity_x -= ACCELERATION
        elif keys[pygame.K_d]:
            is_moving_right = True
            is_moving_left = False
            facing_right = True
            if keys[pygame.KMOD_SHIFT] & pygame.KMOD_LSHIFT:
                velocity_x += 2 * ACCELERATION  # Sprint speed (double acceleration)
            else:
                velocity_x += ACCELERATION
        else:
            is_moving_left = False
            is_moving_right = False
            if velocity_x > 0:
                velocity_x -= DECELERATION
                if velocity_x < 0:
                    velocity_x = 0
            elif velocity_x < 0:
                velocity_x += DECELERATION
                if velocity_x > 0:
                    velocity_x = 0

        # Clamp the velocity to max speed
        if velocity_x > MAX_SPEED:
            velocity_x = MAX_SPEED
        elif velocity_x < -MAX_SPEED:
            velocity_x = -MAX_SPEED

        # Update the player"s horizontal position
        player_x += velocity_x

        # Ensure the player stays within screen bounds
        if player_x < 0:
            player_x = 0
            velocity_x = 0
        elif player_x > SCREEN_WIDTH - PLAYER_SIZE:
            player_x = SCREEN_WIDTH - PLAYER_SIZE
            velocity_x = 0

        # Collision detection for horizontal movement
        player_rect = pygame.Rect(player_x, player_y, PLAYER_SIZE, PLAYER_SIZE)
        horizontal_collisions = check_collision(player_rect, filled_cells)
        for collision_rect in horizontal_collisions:
            if velocity_x > 0:  # Moving right
                player_x = collision_rect.left - PLAYER_SIZE
            elif velocity_x < 0:  # Moving left
                player_x = collision_rect.right
            velocity_x = 0
            player_rect.x = player_x

        # Jumping and gravity
        if is_jumping:
            player_y += velocity_y
            velocity_y += GRAVITY
            if player_y >= SCREEN_HEIGHT - PLATFORM_HEIGHT - PLAYER_SIZE - 5:
                player_y = SCREEN_HEIGHT - PLATFORM_HEIGHT - PLAYER_SIZE - 5
                is_jumping = False
                is_on_platform = True

        # Collision detection for vertical movement
        player_rect.y = player_y
        vertical_collisions = check_collision(player_rect, filled_cells)
        for collision_rect in vertical_collisions:
            if velocity_y > 0:  # Falling down
                player_y = collision_rect.top - PLAYER_SIZE
                is_jumping = False
                is_on_platform = True
            elif velocity_y < 0:  # Jumping up
                player_y = collision_rect.bottom
            velocity_y = 0
            player_rect.y = player_y

        # Send player position to server
        if connected_to_server:
            send_to_server({"type": "position", "name": args.name, "x": player_x, "y": player_y})

        # Update the player"s texture based on movement
        current_time = pygame.time.get_ticks() / 1000.0  # Convert to seconds
        if is_moving_left or is_moving_right:
            if current_time - last_frame_update_time > frame_time:
                current_frame = (current_frame + 1) % len(walking_animation_frames)
                last_frame_update_time = current_time
            player_texture = walking_animation_frames[current_frame]
            if is_moving_right:
                player_texture = pygame.transform.flip(player_texture, True, False)
        else:
            player_texture = player_idle
            if facing_right:
                player_texture = pygame.transform.flip(player_texture, True, False)

        # Fill the screen with white
        screen.fill(WHITE)

        # Draw the platform
        pygame.draw.rect(screen, GRAY, (0, SCREEN_HEIGHT - PLATFORM_HEIGHT, SCREEN_WIDTH, PLATFORM_HEIGHT))

        # Draw the player texture
        screen.blit(player_texture, (player_x, player_y))

        # Draw the player"s name above the player
        if args.name:
            if len(args.name) > 10:
                exit()
            else:
                name_text = name_font.render(args.name, True, WHITE)
                name_bg = pygame.Surface((name_text.get_width() + 10, name_text.get_height()))
                name_bg.set_alpha(128)  # Set transparency
                name_bg.fill(BLACK)
                screen.blit(name_bg, (player_x + PLAYER_SIZE // 2 - name_text.get_width() // 2 + 10, player_y - name_text.get_height() - 10))
                screen.blit(name_text, (player_x + PLAYER_SIZE // 2 - name_text.get_width() // 2 + 10, player_y - name_text.get_height() - 10))

        # Draw other players
        for player_name, player_data in players.items():
            if player_name != args.name:
                other_player_x, other_player_y = player_data["x"], player_data["y"]
                other_player_texture = player_idle
                if player_data["facing_right"]:
                    other_player_texture = pygame.transform.flip(other_player_texture, True, False)
                screen.blit(other_player_texture, (other_player_x, other_player_y))
                other_name_text = name_font.render(player_name, True, WHITE)
                other_name_bg = pygame.Surface((other_name_text.get_width() + 10, other_name_text.get_height()))
                other_name_bg.set_alpha(128)
                other_name_bg.fill(BLACK)
                screen.blit(other_name_bg, (other_player_x + PLAYER_SIZE // 2 - other_name_text.get_width() // 2 + 10, other_player_y - other_name_text.get_height() - 10))
                screen.blit(other_name_text, (other_player_x + PLAYER_SIZE // 2 - other_name_text.get_width() // 2 + 10, other_player_y - other_name_text.get_height() - 10))

        # Draw the grid
        for x in range(grid_cols):
            for y in range(grid_rows):
                rect = pygame.Rect(x * GRID_CELL_SIZE, y * GRID_CELL_SIZE, GRID_CELL_SIZE, GRID_CELL_SIZE)
                pygame.draw.rect(screen, GRAY, rect, 1)
                if (x, y) in filled_cells:
                    pygame.draw.rect(screen, GRAY, rect)

        # Highlight the selected cell with the appropriate color
        selected_rect = pygame.Rect(selected_cell_x * GRID_CELL_SIZE, selected_cell_y * GRID_CELL_SIZE, GRID_CELL_SIZE, GRID_CELL_SIZE)
        if within_reach:
            pygame.draw.rect(screen, GREEN, selected_rect, 3)
        else:
            pygame.draw.rect(screen, RED, selected_rect, 3)

        # Draw hitboxes if enabled
        if args.show_hitboxes:
            pygame.draw.rect(screen, BLUE, player_rect, 1)  # Player hitbox
            for cell in filled_cells:
                cell_rect = pygame.Rect(cell[0] * GRID_CELL_SIZE, cell[1] * GRID_CELL_SIZE, GRID_CELL_SIZE, GRID_CELL_SIZE)
                pygame.draw.rect(screen, BLUE, cell_rect, 1)  # Filled cell hitboxes

        # Draw the custom cursor if not disabled
        if not args.dont_modify_cursor:
            screen.blit(cursor_image, (mouse_x, mouse_y))
            pygame.mouse.set_visible(False)

        if args.countframerate:
            fps = clock.get_fps()
            fps_text = font.render(f"FPS: {int(fps)}", True, (255, 255, 255))
            fps_box = pygame.Surface((100, 40))
            fps_box.fill((0, 0, 0))
            fps_box.blit(fps_text, (10, 5))
            screen.blit(fps_box, (10, 10))

        if args.show_coordinates:
            coords_text = font.render(get_player_coordinates(player_x, player_y), True, (255, 255, 255))
            coords_box = pygame.Surface((350, 40))
            coords_box.fill((0, 0, 0))
            coords_box.blit(coords_text, (10, 5))
            screen.blit(coords_box, (10, 50))
    elif paused:
        draw_pause_ui()
    elif multiplayer_mode:
        draw_multiplayer_ui()
        if connection_status:
            status_text = font.render(connection_status, True, WHITE)
            screen.blit(status_text, ((SCREEN_WIDTH - status_text.get_width()) // 2, (SCREEN_HEIGHT - status_text.get_height()) // 2))
    elif chat_mode:
        draw_chat_ui()

    # Update the display
    pygame.display.flip()

    # Cap the frame rate
    if args.framerate:
        clock.tick(args.framerate)
    else:
        clock.tick(60)

pygame.quit()
if args.launcher:
    os.remove("main.py")
    shutil.rmtree("../extracted_temp")
    os.chdir("../../launcher")
    subprocess.run(["python", "launcher.py"])
sys.exit()
