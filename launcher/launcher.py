from tkinter import *
import socket
import os
import json
import subprocess
from tkinter import messagebox
import threading
from email_validator import validate_email, EmailNotValidError
import zipfile

lang_json = {
    "english": {
        "titles": {
            "TITLE_Confirmation": "Confirmation",
            "TITLE_Error": "Error!",
            "TITLE_Account_Deletion": "Account Deletion",
            "TITLE_Information": "Information",
            "TITLE_Change_username": "Change username",
            "TITLE_Change_password": "Change password",
            "TITLE_Login_successful": "Login successful",
            "TITLE_Create_account": "Create account",
            "TITLE_SquareGame_launcher": "SquareGame Launcher"
        },
        "buttons": {
            "BUTTON_log_in": "Log in",
            "BUTTON_create_account": "Create Account",
            "BUTTON_play": "Play",
            "BUTTON_try_again": "Try again",
            "BUTTON_play_offline": "Play Offline",
            "BUTTON_Logout": "Logout",
            "BUTTON_Change_Username": "Change Username",
            "BUTTON_Change_Password": "Change Password",
            "BUTTON_Delete_Account": "Delete Account",
            "BUTTON_Change": "Change",
            "BUTTON_Advanced_Options": "Advanced Options",
            "BUTTON_Save": "Save",
            "BUTTON_Settings": "Settings"
        },
        "strings": {
            "STRING_SquareGame_Launcher": "SquareGame Launcher",
            "STRING_Email": "Email",
            "STRING_Password": "Password",
            "STRING_Username": "Username",
            "STRING_Login": "Login",
            "STRING_Framerate_limit": "Framerate limit",
            "STRING_Show_FPS": "Show FPS",
            "STRING_Show_player_coordinates": "Show player coordinates",
            "STRING_Dont_Modify_Cursor": "Dont Modify Cursor",
            "STRING_Show_hitboxes": "Show hitboxes",
            "STRING_Open_Launcher_on_game_quit": "Open Launcher on game quit",
            "STRING_Enter_password_to_continue_with_account_deletion": "Enter your password to continue with account deletion",
            "STRING_Change_username": "Change username",
            "STRING_New_username": "New username",
            "STRING_Enter_your_password": "Enter your password",
            "STRING_Change_your_password": "Change your password",
            "STRING_Old_password": "Old password",
            "STRING_New_password": "New password",
            "STRING_Unable_to_connect_to_servers": "\n\nUnable to connect to servers!",
            "STRING_connecting_to_servers": "\n\nconnecting to servers...",
            "STRING_Language": "Language",
            "STRING_Settings": "Settings"
        },
        "messagebox_strings": {
            "MS_accdel_conf": "Are you sure you would like to delete your account?",
            "MS_Incorrect_password": "Incorrect password!",
            "MS_accdel_succ": "Account deleted successfully",
            "MS_usrchnge_succ": "Username changed successfully!",
            "MS_psswdchnge_succ": "Password changed successfully",
            "MS_invalid_email": "Invalid email address!",
            "MS_logout_succ": "Logged out successfully!",
            "MS_psswd_len": "Password must be at least 8 characters!",
            "MS_user_len<": "Username must be more than 3 characters!",
            "MS_user_len>": "Username cannot be more than 10 characters long!",
            "MS_config_sync_err": "Config does not sync with servers.\nIf you think this is incorrect, please contact [HELP_EMAIL] for help",
            "MS_invalid_lang": "Invalid language!",
            "MS_account_not_found": "Account not found!",
            "MS_logged_into_acc_succ": "Logged into %username% successfully",
            "MS_email_in_use": "Email is already in use!",
            "MS_usr_in_use": "Username already in use!",
            "MS_acc_creation_succ": "Account creation successful!"
        }
    }
}

config_json = {
    "logged_in": False,
    "email": "",
    "password": "",
    "lang": "english",
    "dark_m": 0  # This setting is no longer used, but remains here for compatibility.
}

s = socket.socket()

def initialize_config():
    if not os.path.exists("./config.json"):
        with open("./config.json", "w") as f:
            json.dump(config_json, f, indent=4)

initialize_config()

with open("./config.json", "r") as f:
    config_data = json.load(f)

def load_languages():
    global lang_data, language, titles, buttons, strings, messagebox_strings
    if os.path.exists("./lang.json"):
        with open("./lang.json", "r") as lang_file:
            lang_data = json.load(lang_file)
    else:
        with open("./lang.json", "w") as lang_file_n:
            json.dump(lang_json, lang_file_n, indent=4)
            lang_file_n.close()
            load_languages()
    language = config_data["lang"]
    if language in lang_data:
        titles = lang_data[language]['titles']
        buttons = lang_data[language]['buttons']
        strings = lang_data[language]['strings']
        messagebox_strings = lang_data[language]['messagebox_strings']
    else:
        messagebox.showinfo("Error", "Invalid language!")
        exit()

def delete_account():
    conf = messagebox.askyesno(titles["TITLE_Confirmation"], messagebox_strings["MS_accdel_conf"])
    if conf:
        s.send(json.dumps({"request": "delete_account", "email": config_data['email'], "password": password_ent.get()}).encode("utf-8"))
        listening = True
        while listening:
            try:
                response = json.loads(s.recv(1024).decode("utf-8"))
                if response["response"] == "incorrect_password":
                    messagebox.showinfo(titles["TITLE_Error"], messagebox_strings["MS_Incorrect_password"])
                elif response["response"] == "successful":
                    logout()
                    messagebox.showinfo(titles["TITLE_Account_Deletion"], messagebox_strings["MS_accdel_succ"])
                    del_acc.destroy()
                    relaunch()
            except Exception:
                pass
    else:
        del_acc.destroy()

def delete_account_screen():
    global password_ent, del_acc
    del_acc = Toplevel()
    del_acc.geometry("350x150")
    del_acc.title(titles["TITLE_Account_Deletion"])
    del_acc.resizable(False, False)
    
    Label(del_acc, text=strings["STRING_Enter_password_to_continue_with_account_deletion"]).pack()
    password_ent = Entry(del_acc, width=30, show="*")
    password_ent.pack()
    Button(del_acc, text=buttons["BUTTON_Delete_Account"], command=delete_account).pack()

def change_username():
    new_username = new_username_ent.get()
    password = user_psswd_ent.get()
    s.send(json.dumps({"request": "change_username", "username": new_username, "password": password, "email": config_data['email']}).encode("utf-8"))
    listening = True
    while listening:
        try:
            response = json.loads(s.recv(1024).decode("utf-8"))
            if response["response"] == "incorrect_password":
                messagebox.showinfo(titles["TITLE_Error"], messagebox_strings["MS_Incorrect_password"])
            elif response["response"] == "successful":
                messagebox.showinfo(titles["TITLE_Information"], messagebox_strings["MS_usrchnge_succ"])
                listening = False
                change_user.destroy()
                relaunch()
        except Exception as e:
            print(f"Error: {e}")
            pass

def change_username_screen():
    global new_username_ent, user_psswd_ent, change_user
    change_user = Toplevel()
    change_user.geometry("300x200")
    change_user.title(titles["TITLE_Change_username"])
    change_user.resizable(False, False)
    
    Label(change_user, text=strings["STRING_Change_username"]).pack()
    Label(change_user, text=strings["STRING_New_username"], font=(None, 7)).pack()
    new_username_ent = Entry(change_user, width=30)
    new_username_ent.pack()
    Label(change_user, text=strings["STRING_Enter_your_password"]).pack()
    user_psswd_ent = Entry(change_user, show="*", width=30)
    user_psswd_ent.pack()
    Button(change_user, text=buttons["BUTTON_Change"], command=change_username).pack()

    change_user.mainloop()

def change_password():
    old_password = old_password_ent.get()
    new_password = new_password_ent.get()
    s.send(json.dumps({"request": "change_password", "old_password": old_password, "new_password": new_password, "email": config_data['email']}).encode("utf-8"))
    listening = True
    while listening:
        try:
            response = json.loads(s.recv(1024).decode("utf-8"))
            if response["response"] == "incorrect_password":
                messagebox.showinfo(titles["TITLE_Error"], messagebox_strings["MS_Incorrect_password"])
            elif response["response"] == "successful":
                messagebox.showinfo(titles["TITLE_Information"], messagebox_strings["MS_psswdchnge_succ"])
                config_data["password"] = new_password
                with open("./config.json", "w") as config_file:
                    json.dump(config_data, config_file, indent=4)
                listening = False
                change_psswd.destroy()
                relaunch()
        except Exception as e:
            print(f"Error: {e}")
            pass

def change_password_screen():
    global old_password_ent, new_password_ent, change_psswd
    change_psswd = Toplevel()
    change_psswd.geometry("300x200")
    change_psswd.resizable(False, False)
    change_psswd.title(titles["TITLE_Change_password"])
    
    Label(change_psswd, text=strings["STRING_Change_your_password"], font=(None, 15)).pack()
    Label(change_psswd, text=strings["STRING_Old_password"], font=(None, 10)).pack()
    old_password_ent = Entry(change_psswd, width=30, show="*")
    old_password_ent.pack()
    Label(change_psswd, text=strings["STRING_New_password"], font=(None, 10)).pack()
    new_password_ent = Entry(change_psswd, width=30, show="*")
    new_password_ent.pack()
    Button(change_psswd, text=buttons["BUTTON_Change"], command=change_password).pack()

    change_psswd.mainloop()

def valid_email(email: str):
    try:
        v = validate_email(email)
        email = v["email"]
        return True
    except EmailNotValidError as e:
        return False

def get_username():
    try:
        s.send(json.dumps({"request": "get_username", "email": config_data['email'], "password": config_data['password']}).encode("utf-8"))
        while True:
            try:
                response = json.loads(s.recv(1024).decode("utf-8"))
                if response['response'] == "incorrect_password":
                    return False
                else:
                    return response['response']
            except json.JSONDecodeError:
                pass
    except Exception as e:
        print(f"Error: {e}")
        return False

def connect():
    try:
        s.connect(("0.0.0.0", 1357))
        return True
    except Exception as e:
        print(f"Connection Error: {e}")
        return False

def logout():
    os.remove("config.json")
    messagebox.showinfo(titles["TITLE_Information"], messagebox_strings["MS_logout_succ"])
    relaunch()

def login():
    global username
    if not valid_email(login_email_ent.get()):
        messagebox.showinfo(titles["TITLE_Error"], messagebox_strings["MS_invalid_email"])
        return False
    s.send(json.dumps({"request": "login", "email": login_email_ent.get(), "password": login_password_ent.get()}).encode("utf-8"))
    listening = True
    while listening:
        try:
            response = json.loads(s.recv(1024).decode("utf-8"))
            if response["response"] == "incorrect_password":
                messagebox.showinfo(titles["TITLE_Error"], messagebox_strings["MS_Incorrect_password"])
            elif response["response"] == "account_not_found":
                messagebox.showinfo(titles["TITLE_Error"], messagebox_strings["MS_account_not_found"])
            elif response["response"] == "login_successful":
                username = response["username"]
                listening = False
                messagebox.showinfo(titles["TITLE_Login_successful"], messagebox_strings["MS_logged_into_acc_succ"].replace("%username%", username))
                config_data["logged_in"] = True
                config_data["email"] = login_email_ent.get()
                config_data["password"] = login_password_ent.get()
                with open("./config.json", "w") as f:
                    json.dump(config_data, f, indent=4)
                log_in.destroy()
                relaunch()
        except Exception:
            pass

def log_in_screen():
    global login_email_ent, login_password_ent, log_in
    log_in = Toplevel()
    log_in.geometry("300x200")
    log_in.resizable(False, False)
    
    Label(log_in, text=strings["STRING_Email"]).pack()
    login_email_ent = Entry(log_in, width=30)
    login_email_ent.pack()
    Label(log_in, text=strings["STRING_Password"]).pack()
    login_password_ent = Entry(log_in, show="*", width=30)
    login_password_ent.pack()
    login_btn = Button(log_in, text=strings["STRING_Login"], command=login)
    login_btn.pack()

    log_in.mainloop()

def create():
    if not valid_email(create_email_ent.get()):
        messagebox.showinfo(titles["TITLE_Error"], messagebox_strings["MS_invalid_email"])
        return False
    if len(create_password_ent.get()) < 8:
        messagebox.showinfo(titles["TITLE_Error"], messagebox_strings["MS_psswd_len"])
        return False
    s.send(json.dumps({"request": "create", "email": create_email_ent.get(), "password": create_password_ent.get(), "username": username_ent.get()}).encode("utf-8"))
    listening = True
    while listening:
        try:
            response = json.loads(s.recv(1024).decode("utf-8"))
            if response["response"] == "email_exists":
                messagebox.showinfo(titles["TITLE_Error"], messagebox_strings["MS_email_in_use"])
            elif response["response"] == "username_exists":
                messagebox.showinfo(titles["TITLE_Error"], messagebox_strings["MS_usr_in_use"])
            elif response["response"] == "successful":
                messagebox.showinfo(titles["TITLE_Create_account"], messagebox_strings["MS_acc_creation_succ"])
                username = username_ent.get()
                listening = False
                messagebox.showinfo(titles["TITLE_Login_successful"], messagebox_strings["MS_logged_into_acc_succ"].replace("%username%", username))
                config_data["logged_in"] = True
                config_data["email"] = create_email_ent.get()
                config_data["password"] = create_password_ent.get()
                with open("./config.json", "w") as f:
                    json.dump(config_data, f, indent=4)
                create_acc.destroy()
                login_frame.pack_forget()
                online_launcher.pack()
                relaunch()
        except Exception:
            pass

def create_account_screen():
    global create_email_ent, create_password_ent, username_ent, create_acc
    create_acc = Toplevel()
    create_acc.geometry("300x250")
    create_acc.resizable(False, False)
    create_acc.title(titles["TITLE_Create_account"])
    
    Label(create_acc, text=strings["STRING_Username"]).pack()
    username_ent = Entry(create_acc, width=30)
    username_ent.pack()
    Label(create_acc, text=strings["STRING_Email"]).pack()
    create_email_ent = Entry(create_acc, width=30)
    create_email_ent.pack()
    Label(create_acc, text=strings["STRING_Password"]).pack()
    create_password_ent = Entry(create_acc, show="*", width=30)
    create_password_ent.pack()
    create_account_btn = Button(create_acc, text=buttons["BUTTON_create_account"], command=create)
    create_account_btn.pack()

    create_acc.mainloop()

def check_logged_in():
    return config_data["logged_in"]

def show_offline_launcher():
    if connecting_frame.winfo_ismapped():
        connecting_frame.pack_forget()
    offline_launcher.pack()

def toggle_advanced_options():
    if ao_frame.winfo_ismapped():
        ao_frame.pack_forget()
    else:
        ao_frame.pack()

def online_launch():
    with zipfile.ZipFile("../versions/v1.0.zip", 'r') as game_f:
        game_f.extract('main.py', 'extracted_temp/')
        game_f.extract('assets/cursor.png', 'extracted_temp/')
        game_f.extract('assets/player_idle.png', 'extracted_temp/')
        game_f.extract('assets/player_walk_ph1.png', 'extracted_temp/')
        game_f.extract('assets/player_walk_ph2.png', 'extracted_temp/')
    count_framerate = fps_counter_bool.get()
    show_coordinates = coord_bool.get()
    dont_modify_cursor = cursor_modify_bool.get()
    show_hitboxes = hitbox_bool.get()
    open_launcher = launcher_bool.get()
    fps_limit = framerate_ent.get()

    os.chdir('extracted_temp')
    command = ["python", "main.py", "-framerate", fps_limit, "-name", get_username()]
    
    print(f"Count fps: {str(count_framerate)}\n"
          f"Show Coordinates: {str(show_coordinates)}\n"
          f"Don't modify cursor: {str(dont_modify_cursor)}\n"
          f"Show hitboxes: {str(show_hitboxes)}\n"
          f"Launcher: {str(open_launcher)}"
          )
    if count_framerate == 1:
        command.append("-countframerate")
    if show_coordinates == 1:
        command.append("-show_coordinates")
    if dont_modify_cursor == 1:
        command.append("-dont_modify_cursor")
    if show_hitboxes == 1:
        command.append("-show_hitboxes")
    if open_launcher == 1:
        command.append("-launcher")
        
    root.destroy()
    subprocess.run(command)

def offline_launch():
    with zipfile.ZipFile("../versions/v1.0.zip", 'r') as game_f:
        game_f.extract('main.py', 'extracted_temp/')
        game_f.extract('assets/cursor.png', 'extracted_temp/')
        game_f.extract('assets/player_idle.png', 'extracted_temp/')
        game_f.extract('assets/player_walk_ph1.png', 'extracted_temp/')
        game_f.extract('assets/player_walk_ph2.png', 'extracted_temp/')
    count_framerate = fps_counter_bool.get()
    show_coordinates = coord_bool.get()
    dont_modify_cursor = cursor_modify_bool.get()
    show_hitboxes = hitbox_bool.get()
    open_launcher = launcher_bool.get()
    fps_limit = framerate_ent.get()

    if len(username_ent.get()) > 10:
        messagebox.showinfo(titles["TITLE_Error"], messagebox_strings["MS_user_len>"])
    elif len(username_ent.get()) < 3:
        messagebox.showinfo(titles["TITLE_Error"], messagebox_strings["MS_user_len<"])
    else:
        os.chdir("./extracted_temp")
        command = ["python", "main.py", "-framerate", fps_limit, "-name", username_ent.get(), "-offline"]
        
        print(f"Count fps: {str(count_framerate)}\n"
            f"Show Coordinates: {str(show_coordinates)}\n"
            f"Don't modify cursor: {str(dont_modify_cursor)}\n"
            f"Show hitboxes: {str(show_hitboxes)}\n"
            f"Launcher: {str(open_launcher)}"
        )
        if count_framerate == 1:
            command.append("-countframerate")
        if show_coordinates == 1:
            command.append("-show_coordinates")
        if dont_modify_cursor == 1:
            command.append("-dont_modify_cursor")
        if show_hitboxes == 1:
            command.append("-show_hitboxes")
        if open_launcher == 1:
            command.append("-launcher")
        
        root.destroy()
        subprocess.run(command)

def relaunch():
    global s
    s.close()
    s = socket.socket()
    root.destroy()
    main()

def settings_screen():
    global settings_frame, language_ent
    settings_frame = Frame(root)
    
    Label(settings_frame, text=strings["STRING_Settings"], font=(None, 10)).pack()
    Label(settings_frame, text=strings["STRING_Language"]).pack()
    language_ent = Entry(settings_frame)
    language_ent.insert(0, config_data["lang"])
    language_ent.pack()
    
    Button(settings_frame, text=buttons["BUTTON_Save"], command=save_settings).pack()
    
    if offline_launcher.winfo_ismapped():
        offline_launcher.pack_forget()
    if online_launcher.winfo_ismapped():
        online_launcher.pack_forget()

    settings_frame.pack()

def save_settings():
    print(f"Language: {language_ent.get()}")
    available_languages = ["english".lower(), "french".lower(), "german".lower()]
    if not language_ent.get().lower() in available_languages:
        messagebox.showinfo(titles["TITLE_Error"], messagebox_strings["MS_invalid_lang"])
        return False
    config_data["lang"] = language_ent.get().lower()
    
    with open("./config.json", "w") as f:
        json.dump(config_data, f, indent=4)
        
    relaunch()

def handle_connection(connecting_label):
    global username
    if connect():
        if config_data["logged_in"]:
            username = get_username()
            if username:
                # Defer GUI operations to the main thread
                root.after(0, lambda: connecting_frame.pack_forget())
                root.after(0, lambda: show_online_launcher())
            else:
                root.after(0, lambda: messagebox.showinfo(titles["TITLE_Error"], messagebox_strings["MS_config_sync_err"]))
                exit()
        else:
            root.after(0, lambda: connecting_frame.pack_forget())
            root.after(0, lambda: login_frame.pack())
    else:
        root.after(0, lambda: connecting_label.config(text=strings["STRING_Unable_to_connect_to_servers"]))
        root.after(0, lambda: Button(connecting_frame, text=buttons["BUTTON_try_again"], command=relaunch).pack())
        root.after(0, lambda: Button(connecting_frame, text=buttons["BUTTON_play_offline"], command=show_offline_launcher).pack())

def show_online_launcher():
    menu_button = Menubutton(online_launcher, text=".", relief=RAISED)
    menu = Menu(menu_button, tearoff=0)
    menu_button.config(menu=menu)
    menu.add_command(label=buttons["BUTTON_Logout"], command=logout)
    menu.add_command(label=buttons["BUTTON_Change_Username"], command=change_username_screen)
    menu.add_command(label=buttons["BUTTON_Change_Password"], command=change_password_screen)
    menu.add_command(label=buttons["BUTTON_Delete_Account"], command=delete_account_screen)
    menu.add_command(label=buttons["BUTTON_Settings"], command=settings_screen)
    menu_button.pack(side=RIGHT)

    Label(online_launcher, text=f"\n{strings['STRING_Username']}: {username}").pack()

    Button(online_launcher, text=buttons["BUTTON_play"], command=online_launch).pack()
    Button(online_launcher, text=buttons["BUTTON_Advanced_Options"], command=toggle_advanced_options).pack()

    online_launcher.pack()

def main():
    global connecting_frame, offline_launcher, online_launcher, username_ent, ao_frame, root, login_frame, language_ent
    load_languages()
    root = Tk()
    root.geometry("500x400")
    root.title(titles["TITLE_SquareGame_launcher"])
    root.resizable(False, False)
    
    Label(root, text=strings["STRING_SquareGame_Launcher"], font=(None, 20)).pack()
    Label(root, text="v1.1.0", font=(None, 10)).pack()
    
    connecting_frame = Frame(root)
    connecting_label = Label(connecting_frame, text=strings["STRING_connecting_to_servers"])
    connecting_label.pack()
    connecting_frame.pack()
    
    online_launcher = Frame(root)
    
    threading.Thread(target=handle_connection, args=(connecting_label,)).start()
    
    offline_launcher = Frame(root)
    Label(offline_launcher, text=f"\n\n{strings['STRING_Username']}", font=(None, 7)).pack()
    username_ent = Entry(offline_launcher)
    username_ent.pack()
    
    Button(offline_launcher, text=buttons["BUTTON_play"], command=offline_launch).pack()
    Button(offline_launcher, text=buttons["BUTTON_Advanced_Options"], command=toggle_advanced_options).pack()
    
    global fps_counter_bool, coord_bool, hitbox_bool, cursor_modify_bool, launcher_bool, framerate_ent
    
    ao_frame = Frame(root)
    Label(ao_frame, text=strings["STRING_Framerate_limit"]).pack()
    framerate_ent = Entry(ao_frame)
    framerate_ent.insert(0, "60")
    framerate_ent.pack()
    
    fps_counter_bool = IntVar()
    coord_bool = IntVar()
    hitbox_bool = IntVar()
    cursor_modify_bool = IntVar()
    launcher_bool = IntVar(value=1)
    
    fps_counter_cb = Checkbutton(ao_frame, text=strings["STRING_Show_FPS"], variable=fps_counter_bool)
    fps_counter_cb.pack()

    coord_cb = Checkbutton(ao_frame, text=strings["STRING_Show_player_coordinates"], variable=coord_bool)
    coord_cb.pack()

    cm_cb = Checkbutton(ao_frame, text=strings["STRING_Dont_Modify_Cursor"], variable=cursor_modify_bool)
    cm_cb.pack()

    hitbox_cb = Checkbutton(ao_frame, text=strings["STRING_Show_hitboxes"], variable=hitbox_bool)
    hitbox_cb.pack()

    launcher_cb = Checkbutton(ao_frame, text=strings["STRING_Open_Launcher_on_game_quit"], variable=launcher_bool)
    launcher_cb.pack()
    
    login_frame = Frame(root)
    if not check_logged_in():
        Button(login_frame, text=buttons["BUTTON_log_in"], command=log_in_screen).pack()
        Button(login_frame, text=buttons["BUTTON_create_account"], command=create_account_screen).pack()
        
    root.mainloop()

if __name__ == "__main__":
    main()

