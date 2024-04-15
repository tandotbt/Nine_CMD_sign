from flask import Flask, request, render_template, jsonify
from flask_httpauth import HTTPBasicAuth
from flask_cors import CORS
import platform
import subprocess
import os
import re
import json
from urllib.parse import quote, unquote
import random
import string

VERSION_NOW = "2.0"
MAX_SIZE_FILE_UTC = 500
# Gọi hàm và thiết lập dung lượng tối đa là 10MB (10 * 1024 * 1024 bytes)
AUTO_CLEAN_TMP_FILE = 10 * 1024 * 1024


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
    ORIGINS = config.get("websites", ["*"])
    USE_NEW_SETTING = config.get("useNewSetting", False)

    # Kiểm tra nếu tất cả các giá trị trong mảng là rỗng
    if all(value == "" for value in ALLOWED_IPS):
        ALLOWED_IPS = []

    if all(value == "" for value in ALLOWED_KEYWORDS):
        ALLOWED_KEYWORDS = []

    if all(value == "" for value in UNWANTED_KEYWORDS):
        UNWANTED_KEYWORDS = []

    if all(value == "" for value in ORIGINS):
        ORIGINS = ["*"]


app = Flask(__name__)
auth = HTTPBasicAuth()

# Gọi hàm load_config để nạp cấu hình
load_config()


@auth.verify_password
def verify_password(username, password):
    # Kiểm tra thông tin đăng nhập từ người dùng và trả về True hoặc False
    # dựa vào kết quả xác thực
    if quote(username) == USERNAME_API and quote(password) == PASSWORD_API:
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
        return jsonify({"error": 1, "message": f"Forbidden ip: {client_ip}"}), 403


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
        "getPublicKey": '"./planetWindows/planet" key export --passphrase-file %passwordPath% --public-key --path "./UTC" %keyId%',
        "getSignature": '"./planetWindows/planet" key sign --passphrase-file %passwordPath% --store-path "./UTC" %keyId% %filePathUnsignedTransaction%',
        "importKey": '"./planetWindows/planet" key import --json %fileName% --path "./UTC"',
        "removeKey": '"./planetWindows/planet" key remove --passphrase-file %passwordPath% --path "./UTC" %keyId%',
    },
    "linux": {
        "getKeyid": '"./planetLinux/planet" key --path "./UTC"',
        "getPublicKey": '"./planetLinux/planet" key export --passphrase-file %passwordPath% --public-key --path "./UTC" %keyId%',
        "getSignature": '"./planetLinux/planet" key sign --passphrase-file %passwordPath% --store-path "./UTC" %keyId% %filePathUnsignedTransaction%',
        "importKey": '"./planetLinux/planet" key import --json %fileName% --path "./UTC"',
        "removeKey": '"./planetLinux/planet" key remove --passphrase-file %passwordPath% --path "./UTC" %keyId%',
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


def try_reload_pythonanywhere(current_url):
    try:
        # Sử dụng phép chia chuỗi để trích xuất username từ URL
        parts = current_url.split(".")

        if len(parts) >= 2:
            username = parts[0].split("//")[-1]

            # Mẹo chạy mã bash để reload web pythonanywhere
            subprocess.run(
                ["touch", f"/var/www/{username}_pythonanywhere_com_wsgi.py"], check=True
            )

            return f"tried reload {username}.pythonanywhere.com web"
        else:
            return "you need manual reload"
    except Exception as e:
        return "you need manual reload"


def extract_column(text):
    # Tách chuỗi dựa trên dấu cách và ký tự xuống dòng
    lines = text.split("\n")

    # Tạo một danh sách để chứa giá trị cột số 2
    column_values = []

    for line in lines:
        # Tách các giá trị trong mỗi dòng dựa trên dấu cách và dấu tab
        values = re.split(r"\s+|\t", line)

        # Lấy giá trị cột số 2 nếu có
        if len(values) == 2:
            column_values.append(values[1].strip())
        if len(values) > 2:
            column_values.append(values[2].strip())
    return column_values


def save_file_or_default(data_save, type="tmp"):
    random_string = "".join(random.choice(string.ascii_lowercase) for _ in range(8))
    try:
        name = f"{type}_{random_string}.txt"
        file_path = os.path.join("tmp", name)
        with open(file_path, "w") as file:
            file.write(data_save)
        return name
    except Exception as e:
        print(f"Lỗi khi lưu file: {e}")
        return "tmp_error.txt"


def read_file_or_default(random_name):
    try:
        file_path = os.path.join("tmp", random_name)
        with open(file_path, "r") as file:
            return file.read()
    except Exception as e:
        print(f"Lỗi khi đọc file: {e}")
        return "data-error"


def clean_tmp_folder(max_size):
    folder_path = "tmp"

    # Kiểm tra xem thư mục tmp đã tồn tại hay chưa
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        return  # Thoát khỏi hàm nếu thư mục mới được tạo

    # Lấy danh sách các file trong thư mục
    files = os.listdir(folder_path)

    # Tính tổng dung lượng của các file
    total_size = sum(
        os.path.getsize(os.path.join(folder_path, file_name)) for file_name in files
    )

    # Kiểm tra dung lượng và xóa các file cũ nếu cần
    if total_size > max_size:
        # Sắp xếp các file theo thời gian chỉnh sửa (mới nhất đến cũ nhất)
        files.sort(
            key=lambda x: os.path.getmtime(os.path.join(folder_path, x)), reverse=True
        )

        # Xóa các file cũ cho đến khi tổng dung lượng dưới ngưỡng
        current_size = total_size
        for file_name in files:
            if current_size <= max_size:
                break
            file_path = os.path.join(folder_path, file_name)
            current_size -= os.path.getsize(file_path)
            os.remove(file_path)


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
        return jsonify({"error": 10000, "message": message}), 400
    command = LIST_COMMAND[osCommand]["getKeyid"]
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    # Xử lý stderr
    stderr_values = extract_column(result.stderr)

    # Xử lý stdout
    stdout_values = extract_column(result.stdout)

    client_ip = request.headers.get("X-Real-IP")
    config_data = {
        "username": unquote(USERNAME_API),
        "ips": ALLOWED_IPS,
        "allowed_actions": ALLOWED_KEYWORDS,
        "disallowed_actions": UNWANTED_KEYWORDS,
        "websites": ORIGINS,
        "useNewSetting": USE_NEW_SETTING,
    }
    # Dọn rác thư mục tmp
    clean_tmp_folder(AUTO_CLEAN_TMP_FILE)
    return render_template(
        "index.html",
        VERSION_NOW=VERSION_NOW,
        stderr_values=stderr_values,
        stdout_values=stdout_values,
        client_ip=client_ip,
        config_data=config_data,
    )


def check_password(old_password):
    # So sánh mật khẩu được cung cấp với mật khẩu trong dữ liệu
    if old_password == PASSWORD_API:
        return True
    return False


def clean_and_replace(input_list):
    cleaned_list = []
    for item in input_list:
        # Loại bỏ mã HTML và JS
        cleaned_item = re.sub(r"<.*?>|&.*?;", "", item)
        # Đổi dấu nháy " thành dấu '
        cleaned_item = cleaned_item.replace('"', "'")
        cleaned_list.append(cleaned_item)
    return cleaned_list


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
    file_name_password = save_file_or_default(str(password), "password")
    file_path_password = os.path.join("tmp", file_name_password)
    command = (
        LIST_COMMAND[osCommand]["getPublicKey"]
        .replace("%passwordPath%", str(file_path_password))
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

    random_string = "".join(random.choice(string.ascii_lowercase) for _ in range(8))
    try:
        name = f"action_{random_string}.txt"
        file_path = os.path.join("tmp", name)
        with open(file_path, "wb") as file:
            file.write(bytes.fromhex(unsignedTransaction))
        file_name_unsignedTransaction = name
    except Exception as e:
        print(f"Lỗi khi lưu file: {e}")
        file_name_unsignedTransaction = "tmp_error.txt"
    file_path_unsignedTransaction = os.path.join("tmp", file_name_unsignedTransaction)
    file_name_password = save_file_or_default(str(password), "password")
    file_path_password = os.path.join("tmp", file_name_password)

    command = (
        LIST_COMMAND[osCommand]["getSignature"]
        .replace("%passwordPath%", str(file_path_password))
        .replace("%keyId%", str(keyId))
        .replace("%filePathUnsignedTransaction%", str(file_path_unsignedTransaction))
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
        return jsonify({"error": error, "message": message}), 200


@app.route("/save_config", methods=["POST"])
@auth.login_required
def save_config():
    if not USE_NEW_SETTING:
        message = ERROR_MESSAGE["en"]["11000"]
        return jsonify({"error": 11000, "message": message}), 400

    # Lấy URL hiện tại từ request
    current_url = request.url

    # Lấy dữ liệu từ form và mã hóa
    username = quote(request.form["username"])
    old_password = quote(request.form["password"])
    new_password = quote(request.form.get("newPassword", ""))
    confirm_password = quote(request.form.get("confirmPassword", ""))

    # Kiểm tra xem mật khẩu cũ có khớp với mật khẩu trong hệ thống không
    if not check_password(old_password):
        return jsonify({"message": "Incorrect old password"}), 400

    # Kiểm tra xem mật khẩu mới và xác nhận mật khẩu có giống nhau không
    if new_password and new_password != confirm_password:
        return jsonify({"message": "New passwords do not match"}), 400

    # Loại bỏ các giá trị rỗng và mã HTML, JS từ dữ liệu
    ips = clean_and_replace(list(filter(None, set(request.form.getlist("ips[]")))))
    allowed_actions = list(filter(None, set(request.form.getlist("allowedActions[]"))))
    disallowed_actions = list(
        filter(None, set(request.form.getlist("disallowedActions[]")))
    )
    websites = clean_and_replace(
        list(filter(None, set(request.form.getlist("websites[]"))))
    )

    # Tạo dữ liệu để lưu vào tệp JSON
    data = {
        "username": username,
        "password": new_password if new_password else old_password,
        "ips": ips,
        "allowed_actions": allowed_actions,
        "disallowed_actions": disallowed_actions,
        "websites": websites,
        "useNewSetting": True,
    }

    # Lưu dữ liệu vào tệp JSON
    with open("config.json", "w") as file:
        json.dump(data, file, indent=2)

    # Chỉ gọi try_reload_pythonanywhere(current_url) khi giá trị websites khác với ORIGINS
    if set(websites) != set(ORIGINS):
        return (
            jsonify(
                {
                    "message": "Data saved successfully - "
                    + try_reload_pythonanywhere(current_url)
                }
            ),
            200,
        )
    else:
        return jsonify({"message": "Data saved successfully"}), 200


@app.route("/get_file_list")
@auth.login_required
def get_file_list():
    if not USE_NEW_SETTING:
        message = ERROR_MESSAGE["en"]["11000"]
        return jsonify({"error": 11000, "message": message}), 400
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
            file_name_key_id = save_file_or_default(value, "key_id")
            files.append(
                {"label": label, "value": file_name_key_id}
            )  # Add to list as a dictionary

    return jsonify(files), 200


@app.route("/upload_delete_files", methods=["POST"])
@auth.login_required
def upload_delete_files():
    if not USE_NEW_SETTING:
        message = ERROR_MESSAGE["en"]["11000"]
        return jsonify({"error": 11000, "message": message}), 400
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
        random_string = "".join(random.choice(string.ascii_lowercase) for _ in range(8))
        file_path = os.path.join("tmp", f"UTC_{random_string}.txt")
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

    for file_name_random_key_id in files_to_delete:
        key_id = read_file_or_default(str(file_name_random_key_id))
        file_name_delete_password = save_file_or_default(
            str(delete_password), "delete_password"
        )
        file_path_delete_password = os.path.join("tmp", file_name_delete_password)
        command = (
            LIST_COMMAND[osCommand]["removeKey"]
            .replace("%passwordPath%", str(file_path_delete_password))
            .replace("%keyId%", str(key_id))
        )
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        err = result.stderr
        if len(err) > 0:
            message = err.replace("\n", "")
            return jsonify({"error": 1, "message": message}), 400

    return jsonify({"error": 0, "message": "Ok"}), 200


if __name__ == "__main__":
    app.run()
