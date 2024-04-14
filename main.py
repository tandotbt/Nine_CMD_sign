from flask import Flask, request, render_template, jsonify
from flask_httpauth import HTTPBasicAuth
from flask_cors import CORS
from urllib.parse import unquote
import platform
import subprocess
import os
import re
import json

VERSION_NOW = "1.0"
MAX_SIZE_FILE_UTC = 500


def load_config(filename="config.json"):
    # Kiểm tra sự tồn tại của file config.json
    if not os.path.exists(filename):
        # Tạo một dictionary mới với các giá trị mặc định
        default_config = {
            "username": "admin",
            "password": "admin",
            "ips": [],
            "allowed_actions": [],
            "disallowed_actions": ["transfer_asset"],
            "websites": ["https://9cmd.top/", "https://tandotbt.github.io/"],
            "useNewSetting": False,
        }

        # Lưu dictionary này vào file config.json
        with open(filename, "w") as f:
            json.dump(default_config, f, indent=2)

    # Đọc file config.json và load nó vào biến config
    with open(filename, "r") as f:
        config = json.load(f)

    # Cập nhật các biến toàn cục với giá trị từ config
    global USERNAME_API, PASSWORD_API, ALLOWED_IPS, UNWANTED_KEYWORDS, ALLOWED_KEYWORDS, ORIGINS, USE_NEW_SETTING

    USERNAME_API = config.get("username", "admin")
    PASSWORD_API = config.get("password", "admin")
    ALLOWED_IPS = config.get("ips", [])
    UNWANTED_KEYWORDS = config.get("disallowed_actions", [])
    ALLOWED_KEYWORDS = config.get("allowed_actions", [])
    ORIGINS = config.get("websites", [])
    USE_NEW_SETTING = config.get("useNewSetting", False)

    # Kiểm tra nếu tất cả các giá trị trong mảng là rỗng
    if all(value == "" for value in ALLOWED_IPS):
        ALLOWED_IPS = []

    if all(value == "" for value in ALLOWED_KEYWORDS):
        ALLOWED_KEYWORDS = []

    if all(value == "" for value in UNWANTED_KEYWORDS):
        UNWANTED_KEYWORDS = []

    if all(value == "" for value in ORIGINS):
        ORIGINS = []


# Gọi hàm load_config để nạp cấu hình
load_config()

app = Flask(__name__)
auth = HTTPBasicAuth()


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
    load_config()
    # Lấy địa chỉ IP thực tế của máy khách từ header 'X-Real-IP'
    client_ip = request.headers.get("X-Real-IP")
    if client_ip is None:
        return jsonify({"error": 1, "message": "Forbidden none ip"}), 403
    # Kiểm tra xem danh sách ALLOWED_IPS có rỗng hay không
    if ALLOWED_IPS and client_ip not in ALLOWED_IPS:
        return jsonify({"error": 1, "message": "Forbidden ip: " + client_ip}), 403


CORS(app, resources={r"/*": {"origins": ORIGINS}})

ERROR_MESSAGE = {
    # English
    "en": {
        "10000": "Error 10000: The system %yourSystem% does not support",
        "10001": "Error 10001: No wallet",
        "10002": "Error 10002: Cann't find wallet %agentAddress%",
        "10003": "Error 10003: Code unsign wrong",
        "10004": "Error 10004: Code unsign contains unwanted keywords",
        "10005": "Error 10005: Code unsign not contains wanted keywords",
        "11000": "Error 11000: You need set <b>useNewSetting: true</b> in file config.json manual",
    },
    # Việt Nam
    "vi": {
        "10000": "Lỗi 10000: Hệ thống %yourSystem% không hỗ trợ",
        "10001": "Lỗi 10001: Ví trống",
        "10002": "Lỗi 10002: Không tìm thấy ví %agentAddress%",
        "10003": "Lỗi 10003: Mã unsign không đúng",
        "10004": "Lỗi 10004: Mã unsign chứa từ khóa không mong muốn",
        "10005": "Lỗi 10005: Mã unsign không chứa từ khóa mong muốn",
        "11000": "Lỗi 11000: Bạn cần đặt <b>useNewSetting: true</b> trong tệp config.json thủ công",
    },
}

LIST_COMMAND = {
    "windows": {
        "getKeyid": '"./planetWindows/planet" key --path "./UTC"',
        "getPublicKey": '"./planetWindows/planet" key export --passphrase %password% --public-key --path "./UTC" %keyId%',
        "getSignature": '"./planetWindows/planet" key sign --passphrase %password% --store-path "./UTC" %keyId% action',
        "importKey": '"./planetWindows/planet" key import --json %fileName% --path "./UTC"',
        "removeKey": '"./planetWindows/planet" key remove --passphrase %password% --path "./UTC" %keyId%',
    },
    "linux": {
        "getKeyid": '"./planetLinux/planet" key --path "./UTC"',
        "getPublicKey": '"./planetLinux/planet" key export --passphrase %password% --public-key --path "./UTC" %keyId%',
        "getSignature": '"./planetLinux/planet" key sign --passphrase %password% --store-path "./UTC" %keyId% action',
        "importKey": '"./planetLinux/planet" key import --json %fileName% --path "./UTC"',
        "removeKey": '"./planetLinux/planet" key remove --passphrase %password% --path "./UTC" %keyId%',
    },
}


def chmodPlanet():
    file_path = "./planetLinux/planet"
    if not os.access(file_path, os.X_OK):
        os.chmod(file_path, 0o775)


def haveWallet(agentAddress, osCommand, locale):
    command = LIST_COMMAND[osCommand]["getKeyid"]
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    error = 10001
    keyId = ERROR_MESSAGE[locale][str(error)]
    if len(result.stdout) == 0:
        return error, keyId
    error = 10002
    keyId = ERROR_MESSAGE[locale][str(error)].replace(
        "%agentAddress%", str(agentAddress)
    )
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


def is_contains_allowed_keywords(string):
    # Kiểm tra nếu ALLOWED_KEYWORDS rỗng
    if not ALLOWED_KEYWORDS:
        return True

    # Kiểm tra từng từ được phép trong danh sách
    for keyword in ALLOWED_KEYWORDS:
        hex_keyword = keyword.encode().hex()  # Chuyển từ khóa sang hex
        if hex_keyword in string:
            return True

    return False


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
        message = ERROR_MESSAGE["en"]["10000"].replace(
            "%yourSystem%", str(platform.system())
        )
        return jsonify({"error": 10000, "message": message})
    command = LIST_COMMAND[osCommand]["getKeyid"]
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    stderr = re.sub(r"\n", "<br>", result.stderr)
    stderr = re.sub(r"\t", "&nbsp;&nbsp;&nbsp;&nbsp;", stderr)

    stdout = re.sub(r"\n", "<br>", result.stdout)
    stdout = re.sub(r"\t", "&nbsp;&nbsp;&nbsp;&nbsp;", stdout)
    client_ip = request.headers.get("X-Real-IP")
    config_data = {
        "username": USERNAME_API,
        "ips": ALLOWED_IPS,
        "allowed_actions": ALLOWED_KEYWORDS,
        "disallowed_actions": UNWANTED_KEYWORDS,
        "websites": ORIGINS,
        "useNewSetting": USE_NEW_SETTING,
    }
    return render_template(
        "index.html",
        VERSION_NOW=VERSION_NOW,
        stderr=stderr,
        stdout=stdout,
        client_ip=client_ip,
        config_data=config_data,
    )


def check_password(old_password):
    # So sánh mật khẩu được cung cấp với mật khẩu trong dữ liệu
    if old_password == PASSWORD_API:
        return True
    return False


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
        message = ERROR_MESSAGE[locale]["10000"].replace(
            "%yourSystem%", str(platform.system())
        )
        return jsonify({"error": 10000, "message": message}), 400
    error, keyId = haveWallet(agentAddress, osCommand, locale)
    if error != 0:
        return jsonify({"error": error, "message": keyId}), 400
    command = (
        LIST_COMMAND[osCommand]["getPublicKey"]
        .replace("%password%", str(password))
        .replace("%keyId%", str(keyId))
    )
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    publicKey = result.stdout
    err = result.stderr
    if len(err) > 0:
        message = err.replace("\n", "")
        error = 1
        return jsonify({"error": error, "message": message}), 400
    else:
        message = publicKey.replace("\n", "")
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
        message = ERROR_MESSAGE[locale]["10000"].replace(
            "%yourSystem%", str(platform.system())
        )
        return jsonify({"error": 10000, "message": message}), 400
    if is_not_valid_hex(unsignedTransaction):
        message = ERROR_MESSAGE[locale]["10003"]
        return jsonify({"error": 10003, "message": message}), 400
    if is_contains_unwanted_keywords(unsignedTransaction):
        message = ERROR_MESSAGE[locale]["10004"]
        return jsonify({"error": 10004, "message": message}), 400
    if not is_contains_allowed_keywords(unsignedTransaction):
        message = ERROR_MESSAGE[locale]["10005"]
        return jsonify({"error": 10005, "message": message}), 400
    error, keyId = haveWallet(agentAddress, osCommand, locale)
    if error != 0:
        return jsonify({"error": error, "message": keyId}), 400
    with open("action", "wb") as f:
        f.write(bytes.fromhex(unsignedTransaction))
    command = (
        LIST_COMMAND[osCommand]["getSignature"]
        .replace("%password%", str(password))
        .replace("%keyId%", str(keyId))
    )
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    signature = result.stdout
    err = result.stderr
    if len(err) > 0:
        message = err.replace("\n", "")
        error = 1
        return jsonify({"error": error, "message": message}), 400
    else:
        message = signature.replace("\n", "")
        error = 0
        return jsonify({"error": error, "message": message})


@app.route("/save_config", methods=["POST"])
@auth.login_required
def save_config():
    if not USE_NEW_SETTING:
        message = ERROR_MESSAGE["en"]["11000"]
        return jsonify({"error": 11000, "message": message})
    # Lấy dữ liệu từ form
    username = request.form["username"]
    old_password = request.form["password"]
    new_password = request.form.get("newPassword")
    confirm_password = request.form.get("confirmPassword")

    # Kiểm tra xem mật khẩu cũ có khớp với mật khẩu trong hệ thống không
    if not check_password(old_password):
        return jsonify({"message": "Incorrect old password"}), 400

    # Kiểm tra xem mật khẩu mới và xác nhận mật khẩu có giống nhau không
    if new_password and new_password != confirm_password:
        return jsonify({"message": "New passwords do not match"}), 400

    # Lấy dữ liệu khác từ form
    ips = list(set(request.form.getlist("ips[]")))
    allowed_actions = list(set(request.form.getlist("allowedActions[]")))
    disallowed_actions = list(set(request.form.getlist("disallowedActions[]")))
    websites = list(set(request.form.getlist("websites[]")))

    # Tạo dữ liệu để lưu vào tệp JSON

    data = {
        "username": username,
        "password": (
            new_password if new_password else old_password
        ),  # Sử dụng mật khẩu mới nếu có, nếu không thì giữ nguyên mật khẩu cũ
        "ips": ips,
        "allowed_actions": allowed_actions,
        "disallowed_actions": disallowed_actions,
        "websites": websites,
        "useNewSetting": True,  # Chỉ có thể tắt khi người dùng tự tắt ở file config.json
    }

    # Lưu dữ liệu vào tệp JSON
    with open("config.json", "w") as file:
        json.dump(data, file, indent=2)

    return jsonify({"message": "Data saved successfully - default data"}), 200


@app.route("/get_file_list")
@auth.login_required
def get_file_list():
    if not USE_NEW_SETTING:
        message = ERROR_MESSAGE["en"]["11000"]
        return jsonify({"error": 11000, "message": message})
    if platform.system() == "Windows":
        osCommand = "windows"
    elif platform.system() == "Linux":
        osCommand = "linux"
        chmodPlanet()
    else:
        message = ERROR_MESSAGE["en"]["10000"].replace(
            "%yourSystem%", str(platform.system())
        )
        return jsonify({"error": 10000, "message": message}), 400
    command = LIST_COMMAND[osCommand]["getKeyid"]
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    # stderr = re.sub(r"\n", "<br>", result.stderr)
    # stderr = re.sub(r"\t", "&nbsp;&nbsp;&nbsp;&nbsp;", stderr)

    stdout = result.stdout.strip()  # Remove any leading/trailing whitespaces
    lines = stdout.split("\n")  # Split stdout by newline

    files = []
    for line in lines:
        parts = line.split(" ")  # Split each line by tab
        if len(parts) >= 2:  # Ensure there's at least a label and value
            label = parts[
                1
            ].strip()  # Get label and remove leading/trailing whitespaces
            value = parts[
                0
            ].strip()  # Get value and remove leading/trailing whitespaces
            files.append(
                {"label": label, "value": value}
            )  # Add to list as a dictionary

    return jsonify(files)


@app.route("/upload_delete_files", methods=["POST"])
@auth.login_required
def upload_delete_files():
    if not USE_NEW_SETTING:
        message = ERROR_MESSAGE["en"]["11000"]
        return jsonify({"error": 11000, "message": message})
    if platform.system() == "Windows":
        osCommand = "windows"
    elif platform.system() == "Linux":
        osCommand = "linux"
        chmodPlanet()
    else:
        message = ERROR_MESSAGE["en"]["10000"].replace(
            "%yourSystem%", str(platform.system())
        )
        return jsonify({"error": 10000, "message": message}), 400

    files_to_delete_str = request.form.get("filesToDelete", "")
    files_to_delete = json.loads(files_to_delete_str) if files_to_delete_str else []
    delete_password = request.form.get("deletePassword", "admin")

    uploaded_file = request.files.get("file")
    if uploaded_file:
        buffer = uploaded_file.getbuffer()
        size = len(buffer)
        if size > MAX_SIZE_FILE_UTC:
            return (
                jsonify(
                    {
                        "error": 1,
                        "message": "File size exceeds the limit.",
                    }
                ),
                400,
            )

        file_path = os.path.join(uploaded_file.filename)
        try:
            uploaded_file.save(file_path)
        except Exception as e:
            return jsonify({"error": 1, "message": str(e)}), 400

        if not os.path.exists(file_path):
            return jsonify({"error": 1, "message": "Failed to save file"}), 400

        command = LIST_COMMAND[osCommand]["importKey"].replace(
            "%fileName%", str(file_path)
        )
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        os.remove(file_path)
        out = result.stdout
        err = result.stderr
        if len(out) == 0:
            message = err.replace("\n", "")
            return jsonify({"error": 1, "message": message}), 400

    for file_name in files_to_delete:
        command = (
            LIST_COMMAND[osCommand]["removeKey"]
            .replace("%password%", str(delete_password))
            .replace("%keyId%", str(file_name))
        )
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        err = result.stderr
        if len(err) > 0:
            message = err.replace("\n", "")
            return jsonify({"error": 1, "message": message}), 400

    return jsonify({"error": 0, "message": "Ok"})


if __name__ == "__main__":
    app.run()
