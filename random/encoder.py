from cryptography.fernet import Fernet
import base64
import os

key = Fernet.generate_key()
cipher_suite = Fernet(key)

filename = input("Enter file name: ")
if not os.path.exists(filename):
    print("Invalid path!")
    exit()
output_filename = input("Enter output file name: ")
if os.path.exists(output_filename):
    print("Path already exists!")
    exit()
with open(filename, 'r') as file:
    file_contents = file.read()
encrypted_data = cipher_suite.encrypt(file_contents.encode('utf-32'))
contents = f"from cryptography.fernet import Fernet\nimport base64\nexec(Fernet({key}).decrypt({encrypted_data}).decode('utf-32'))"
with open(output_filename, 'w') as file:
    file.write(contents)

