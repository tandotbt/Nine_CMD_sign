from flask import Flask, request, jsonify
from flask_httpauth import HTTPBasicAuth
from flask_cors import CORS
from urllib.parse import unquote
import platform
import subprocess
import os
import re

# Username và password xác thực
USERNAME_API = "admin"
PASSWORD_API = "admin"
# Danh sách IP cho phép ngăn truy cập lạ, với lần truy cập đầu bạn sẽ biết được ip của mình
# Để trống [] sẽ cho phép tất cả các ip truy cập
ALLOWED_IPS = []
# Danh sách các giao dịch không mong muốn ví dụ "transfer_asset" là chuyển NCG
UNWANTED_KEYWORDS = ["transfer_asset"]

app = Flask(__name__)
auth = HTTPBasicAuth()
VERSION_NOW = "0.1"

@auth.verify_password
def verify_password(username, password):
    # Kiểm tra thông tin đăng nhập từ người dùng và trả về True hoặc False
    # dựa vào kết quả xác thực
    if username == USERNAME_API and password == PASSWORD_API:
        return True
    else:
        return False

@app.before_request
def check_allowed_ips():
    # Lấy địa chỉ IP thực tế của máy khách từ header 'X-Real-IP'
    client_ip = request.headers.get('X-Real-IP')

    # Kiểm tra xem danh sách ALLOWED_IPS có rỗng hay không
    if ALLOWED_IPS and client_ip not in ALLOWED_IPS:
        return "Forbidden ip: " + client_ip, 403

# Thiết lập CORS
origins = [
    #"http://localhost",
    #"http://localhost:8000",
    "https://tandotbt.github.io",
    "https://tandotbt.github.io/",
    "https://tandotbt.github.io/*",
    "https://tandotbt.github.io/Nine_CMD",
    # Thêm các origin khác mà bạn muốn cho phép
]

CORS(app, resources={r"/*": {"origins": origins}})

ERROR_MESSAGE = {
    #English
    "en": {
        "10000": "Error 10000: The system %yourSystem% does not support",
        "10001": "Error 10001: No wallet",
        "10002": "Error 10002: Cann't find wallet %agentAddress%",
        "10003": "Error 10003: Code unsign wrong",
        "10004": "Error 10004: Code unsign contains unwanted keywords",
    },
    #Việt Nam
    "vi": {
        "10000": "Lỗi 10000: Hệ thống %yourSystem% không hỗ trợ",
        "10001": "Lỗi 10001: Ví trống",
        "10002": "Lỗi 10002: Không tìm thấy ví %agentAddress%",
        "10003": "Lỗi 10003: Mã unsign không đúng",
        "10004": "Lỗi 10004: Mã unsign chứa từ khóa không mong muốn",
    },
}

LIST_COMMAND = {
    "windows": {
        "getKeyid": '"./planetWindows/planet" key --path "./UTC"',
        "getPublicKey": '"./planetWindows/planet" key export --passphrase %password% --public-key --path "./UTC" %keyId%',
        "getSignature": '"./planetWindows/planet" key sign --passphrase %password% --store-path "./UTC" %keyId% action',
    },
    "linux": {
        "getKeyid": '"./planetLinux/planet" key --path "./UTC"',
        "getPublicKey": '"./planetLinux/planet" key export --passphrase %password% --public-key --path "./UTC" %keyId%',
        "getSignature": '"./planetLinux/planet" key sign --passphrase %password% --store-path "./UTC" %keyId% action',
    },
}

def chmodPlanet():
    file_path = "./planetLinux/planet"
    if not os.access(file_path, os.X_OK):
        os.chmod(file_path, 0o775)

def haveWallet(agentAddress,osCommand,locale):
    command = LIST_COMMAND[osCommand]["getKeyid"]
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    error = 10001
    keyId = ERROR_MESSAGE[locale][str(error)]
    if len(result.stdout) == 0:
        return error, keyId
    error = 10002
    keyId = ERROR_MESSAGE[locale][str(error)].replace("%agentAddress%", str(agentAddress))
    lines = result.stdout.split("\n")
    for line in lines:
        cols = line.split(" ")
        if len(cols) == 2 and cols[1].lower() == agentAddress.lower():
            error = 0
            keyId = cols[0]
            break
    return error, keyId

def is_not_valid_hex(string):
    try:
        bytes.fromhex(string)
        return False
    except ValueError:
        return True

def is_contains_unwanted_keywords(string):
    # Kiểm tra từng từ không mong muốn trong danh sách
    for keyword in UNWANTED_KEYWORDS:
        hex_keyword = keyword.encode().hex()  # Chuyển từ khóa sang hex
        if hex_keyword in string:
            return True

    return False

@app.route("/")
@auth.login_required
def index():
    if platform.system() == "Windows":
        osCommand = "windows"
    elif platform.system() == "Linux":
        osCommand = "linux"
        chmodPlanet()
    else:
        message = ERROR_MESSAGE["en"]["10000"].replace("%yourSystem%", str(platform.system()))
        return jsonify({"error": 10000, "message": message})
    command = LIST_COMMAND[osCommand]["getKeyid"]
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    stderr = re.sub(r"\n", "<br>", result.stderr)
    stderr = re.sub(r"\t", "&nbsp;&nbsp;&nbsp;&nbsp;", stderr)

    stdout = re.sub(r"\n", "<br>", result.stdout)
    stdout = re.sub(r"\t", "&nbsp;&nbsp;&nbsp;&nbsp;", stdout)
    client_ip = request.headers.get('X-Real-IP')
    message = f"""<html>
    <head>
        <title>Nine CMD Sign v{VERSION_NOW}</title>
    </head>
    <body>
    <p>More info here: <a href="https://github.com/tandotbt/Nine_CMD_sign">GitHub - tandotbt/Nine_CMD_sign</a>
    <br>Your ip: <b>{client_ip}</b>
    <br>Address available:
    <pre>{stderr}</pre>
    <pre>{stdout}</pre>
    </p>
    </body>
    </html>"""
    return message
@app.route("/publicKey", methods=["POST"])
@auth.login_required
def get_public_key():
    inputData = request.json
    agentAddress = inputData.get("agentAddress")
    password = unquote(inputData.get("password"))
    locale = inputData.get("locale", "en")

    if platform.system() == "Windows":
        osCommand = "windows"
    elif platform.system() == "Linux":
        osCommand = "linux"
        chmodPlanet()
    else:
        message = ERROR_MESSAGE[locale]["10000"].replace("%yourSystem%", str(platform.system()))
        return jsonify({"error": 10000, "message": message})
    error, keyId = haveWallet(agentAddress,osCommand,locale)
    if error != 0:
        return jsonify({"error": error, "message": keyId})
    command = LIST_COMMAND[osCommand]["getPublicKey"].replace("%password%",str(password)).replace("%keyId%",str(keyId))
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    publicKey = result.stdout
    err = result.stderr
    if len(err) > 0:
        message = err
        error = 1
    else:
        message = publicKey.replace('\n', '')
        error = 0
    return jsonify({"error": error, "message": message})

@app.route("/signature", methods=["POST"])
@auth.login_required
def get_signature():
    inputData = request.json
    agentAddress = inputData.get("agentAddress")
    password = unquote(inputData.get("password"))
    unsignedTransaction = inputData.get("unsignedTransaction")
    locale = inputData.get("locale", "en")

    if platform.system() == "Windows":
        osCommand = "windows"
    elif platform.system() == "Linux":
        osCommand = "linux"
        chmodPlanet()
    else:
        message = ERROR_MESSAGE[locale]["10000"].replace("%yourSystem%", str(platform.system()))
        return jsonify({"error": 10000, "message": message})
    if is_not_valid_hex(unsignedTransaction):
        message = ERROR_MESSAGE[locale]["10003"]
        return jsonify({"error": 10003, "message": message})
    if is_contains_unwanted_keywords(unsignedTransaction):
        message = ERROR_MESSAGE[locale]["10004"]
        return jsonify({"error": 10004, "message": message})
    error, keyId = haveWallet(agentAddress,osCommand,locale)
    if error != 0:
        return jsonify({"error": error, "message": keyId})
    with open('action' , 'wb') as f:
      f.write(bytes.fromhex(unsignedTransaction))
    command = LIST_COMMAND[osCommand]["getSignature"].replace("%password%",str(password)).replace("%keyId%",str(keyId))
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    signature = result.stdout
    err = result.stderr
    if len(err) > 0:
        message = err
        error = 1
    else:
        message = signature.replace('\n', '')
        error = 0
    return jsonify({"error": error, "message": message})

if __name__ == "__main__":
    app.run()