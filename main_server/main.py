import socket
import json
from threading import Thread
import requests
import datetime

with open("accounts.json", "r") as accounts_file:
    accounts = json.load(accounts_file)

server_running = False

def get_time():
    datetime_raw = datetime.datetime.now()
    return datetime_raw.strftime("[%d:%m:%Y %H:%M:%S]")

def get_date():
    dt_raw = datetime.datetime.now()
    return dt_raw.strftime("%d/%m/%Y")

def check_email(email):
    for account in accounts["accounts"]:
        if account["email"] == email:
            return False
    return True

def check_username(username):
    for account in accounts["accounts"]:
        if account["username"] == username:
            return False
    return True

def save_accounts():
    with open("accounts.json", "w") as accounts_file:
        json.dump(accounts, accounts_file, indent=4)

def main():
    global server_running
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", 1357))
    server_socket.listen(5)
    print(f"{get_time()} SquareGame official server open on port '1357'")
    server_running = True

    while server_running:
        client_socket, client_address = server_socket.accept()
        client_thread = Thread(target=client_handler, args=(client_socket, client_address))
        client_thread.start()
        print(f"{get_time()} Connection from {client_address}")

def client_handler(cs, ca):
    global server_running
    while server_running:
        try:
            data = json.loads(cs.recv(1024).decode("utf-8"))
            if data["request"] == "check-account":
                print(f"{get_time()} {ca} has requested account check: {data}")
                username = data["username"]
                email = data["email"]
                no_acc = 0
                for account in accounts["accounts"]:
                    if account["email"] == email:
                        cs.send(json.dumps({"response": "exists"}).encode("utf-8"))
                        no_acc += 1
                if no_acc == 0:
                    cs.send(json.dumps({"response": "not_exists"}).encode("utf-8"))
            elif data["request"] == "create":
                print(f"{get_time()} {ca} has requested an account creation: {data}")
                username = data["username"]
                email = data["email"]
                password = data["password"]
                if check_username(username):
                    if check_email(email):
                        accounts["accounts"].append({"username": username, "email": email, "password": password, "date_created": get_date()})
                        save_accounts()
                        cs.send(json.dumps({"response": "successful"}).encode("utf-8"))
                    else:
                        cs.send(json.dumps({"response": "email_exists"}).encode("utf-8"))
                else:
                    cs.send(json.dumps({"response": "username_exists"}).encode("utf-8"))
            elif data["request"] == "login":
                print(f"{get_time()} {ca} has requested a log in: {data}")
                email = data["email"]
                password = data["password"]
                no_acc = 0
                for account in accounts["accounts"]:
                    if account["email"] == email:
                        no_acc += 1
                        if account["password"] == password:
                            cs.send(json.dumps({"response": "login_successful", "username": account["username"]}).encode("utf-8"))
                            break
                        else:
                            cs.send(json.dumps({"response": "incorrect_password"}).encode("utf-8"))
                if no_acc == 0:
                    cs.send(json.dumps({"response": "account_not_found"}).encode("utf-8"))
            elif data["request"] == "change_password":
                print(f"{get_time()} {ca} has requested a password change: {data}")
                email = data["email"]
                old_password = data["old_password"]
                new_password = data["new_password"]
                for account in accounts["accounts"]:
                    if account["email"] == email:
                        if account["password"] == old_password:
                            account["password"] = new_password
                            save_accounts()
                            cs.send(json.dumps({"response": "successful"}).encode("utf-8"))
                        else:
                            cs.send(json.dumps({"response": "incorrect_password"}).encode("utf-8"))
            elif data["request"] == "get_username":
                print(f"{get_time()} {ca} has requested an account username: {data}")
                email = data["email"]
                password = data["password"]
                for account in accounts["accounts"]:
                    if account["email"] == email:
                        if account["password"] == password:
                            cs.send(json.dumps({"response": account["username"]}).encode("utf-8"))
                        else:
                            cs.send(json.dumps({"response": "incorrect_password"}).encode("utf-8"))
            elif data["request"] == "delete_account":
                print(f"{get_time()} {ca} has requested an account deletion: {data}")
                email = data["email"]
                password = data["password"]
                for account in accounts["accounts"]:
                    if account["email"] == email:
                        if account["password"] == password:
                            accounts["accounts"].remove(account)
                            save_accounts()
                            cs.send(json.dumps({"response": "successful"}).encode("utf-8"))
                        else:
                            cs.send(json.dumps({"response": "incorrect_password"}).encode("utf-8"))
            elif data["request"] == "change_username":
                print(f"{get_time()} {ca} has requested a username change: {data}")
                email = data["email"]
                password = data["password"]
                new_username = data["username"]
                for account in accounts["accounts"]:
                    if account["email"] == email:
                        if account["password"] == password:
                            account["username"] = new_username
                            save_accounts()
                            cs.send(json.dumps({"response": "successful"}).encode("utf-8"))
                        else:
                            cs.send(json.dumps({"response": "incorrect_password"}).encode("utf-8"))
                        
        except json.decoder.JSONDecodeError:
            pass

if __name__ == "__main__":
    main()

