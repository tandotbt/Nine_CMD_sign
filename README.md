# Nine CMD Your Server

![](https://i.imgur.com/pT003IC.png)

> [!WARNING]
> Hãy nâng cấp lên phiên bản v2, những phiên bản trước đó tiềm ẩn nguy cơ bảo mật

> [!NOTE]
> Khuyến nghị đặt "useNewSetting": false trong tệp config,json và chỉnh sửa tệp config.json thủ công. Đặt true thì tiện chỉnh sửa tệp config.json ở web nhưng không an toàn bằng vì có thể có lỗ hổng bảo mật mà chưa lường trước được.

## Giới thiệu

### Server ký các giao dịch của game Nine Chronicles bằng api python

###### Tìm hiểu thêm tại [Gitbook (hiện tại thì chưa có gì)](https://tan-dot-bt.gitbook.io/9cmd/)

## Giới thiệu

- Giúp chơi được Nine Chronicles qua web
- Vấn đề bảo mật thì tương đối do người code không có chuyên môn cái này :v
- Sử dụng planet để ký, cơ sở lý thuyết [ở đây](https://devforum.nine-chronicles.com/t/transfer-asset-with-graphql-queries/59#sign-the-unsigned-message-with-planet-command-4)
- Đang sử dụng phiên bản [planet 3.9.4](https://github.com/planetarium/libplanet/releases/tag/3.9.4)
- Hỗ trợ chạy trên cả linux và windows, cả 2 đều cần là 64bit do planet yêu cầu vậy :D

## Tính năng

- Truy vấn public key của ví đang có UTC file
- Ký các giao dịch của game Nine Chronicles
- Bảo mật 3 lớp: User/pass, chặn các ip lạ và chặn/chỉ cho phép ký các giao dịch chứa ký tự mong muốn

## Yêu cầu

### Cài đặt các gói pip

Trước khi chạy ứng dụng Flask, bạn cần cài đặt các gói pip sau vào môi trường ảo:

```bash
pip install flask
pip install flask-cors
pip install Flask-HTTPAuth
```

Chạy main.py

```
(.venv) D:\Nine_CMD_sign>python main.py
 * Serving Flask app 'main'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

### Yêu cầu GET

#### Mô tả

Yêu cầu GET được sử dụng để truy cập vào trang chủ của ứng dụng.

#### Cú pháp

```
GET /
```

#### Phản hồi

Trả về thông báo, ip và các địa chỉ ví theo file UTC đang có

### Yêu cầu POST - Lấy khóa công khai (publicKey)

#### Mô tả

Yêu cầu POST được sử dụng để lấy khóa công khai (public key)

#### Cú pháp

```
POST /publicKey
Content-Type: application/json
Authorization: Basic <credentials>

{
  "agentAddress": "địa chỉ ví",
  "password": "mật khẩu",
  "locale": "en"
}
```

#### Phản hồi

Nếu thành công:

```json
{
  "error": 0,
  "message": "khóa công khai"
}
```

Nếu không thành công:

```json
{
  "error": "mã lỗi",
  "message": "thông báo lỗi"
}
```

Hoặc các trường hợp lỗi khác sẽ không theo dạng trên

### Yêu cầu POST - Lấy chữ ký (signature)

#### Mô tả

Yêu cầu POST được sử dụng để lấy chữ ký (signature) từ ví.

#### Cú pháp

```
POST /signature
Content-Type: application/json
Authorization: Basic <credentials>

{
  "agentAddress": "địa chỉ ví",
  "password": "mật khẩu",
  "unsignedTransaction": "giao dịch chưa ký",
  "locale": "en"
}
```

#### Phản hồi

Nếu thành công:

```json
{
  "error": 0,
  "message": "chữ ký"
}
```

Nếu không thành công:

```json
{
  "error": "mã lỗi",
  "message": "thông báo lỗi"
}
```

Hoặc các trường hợp lỗi khác sẽ không theo dạng trên

### Một số yêu cầu khác phục vụ cho config.json chưa được đề cập tới, ae tự khám phá xD

## Hướng dẫn triển khai lên [pythonanywhere](https://www.pythonanywhere.com)

### Giới thiệu

Ưu điểm:

- Web sử dụng free
- Hỗ trợ thao tác với file trực quan
- Có log cũng hay hay
- Tạo tài khoản dễ dàng
- Dùng thoải mái có vẻ là vô hạn

Nhược điểm:

- Cần truy cập lại trang sau 3 tháng
- Khó khăn trong bước cài đặt đầu do có giới hạn
- Khi tới giới hạn là đợi sang hôm sau :D
- Muốn thay đổi tệp main.py thì cần <b>reload web</b> để áp dụng

### Tổng quan

- Tải code lên pythonanywhere, nếu muốn cập nhật hãy giữ lại file config.json và thư mục UTC, sau đó xóa thư mục Nine_CMD_sign đang tồn tại trước khi chạy mã git clone

```bash
git clone https://github.com/tandotbt/Nine_CMD_sign.git
```

- Tạo môi trường ảo, cài thư viện cần thiết

```bash
mkvirtualenv envServer9cmd --python=/usr/bin/python3.10
workon envServer9cmd
pip install flask
pip install flask-cors
pip install Flask-HTTPAuth
```

Thao tác chuẩn thì sẽ tốn khoảng `CPU Usage: 56% used – 56.79s of 100s`, nếu vượt quá 100% thì bạn cần chờ tới ngày mai với tài khoản pythonanywhere miễn phí :v

- Tạo web theo kiểu Manual configuration (including virtualenvs), Python 3.10, chọn đường dẫn cho Source code, Working directory và Virtualenv, cài WSGI configuration đúng với tên username `tanbt` thì sẽ là:

```python
import sys
path = '/home/tanbt/Nine_CMD_sign'
if path not in sys.path:
    sys.path.append(path)
from main import app as application
```

- Cấu hình file config.json, chú ý mục ips là nơi các địa chỉ ip cho phép, nếu bạn không truy cập được do chưa thêm ip thì cần thêm thủ công hoặc để trống [] cho mục ips, và mục useNewSetting đặt false nếu bạn muốn an toàn hơn
- Upload tệp UTC vào thư mục UTC qua web hoặc upload thủ công thông qua trình quản lý file của pythonanywhere
- Thỉnh thoảng vào gia hạn cho tên miền của web sống thêm 3 tháng, Disable/Re-enable web khi muốn sài cho an toàn, cài bảo mật 2 lớp cho tài khoản pythonanywhere thì an toàn hơn nữa
- Có một thư mục .git không sử dụng tới, bạn có thể xóa đi

### Hướng dẫn cài đặt

- Bước 1: Tạo tài khoản https://www.pythonanywhere.com
- Bước 2: Tải mã nguồn lên tài khoản pythonanywhere (Cách mới, bỏ qua bước 2 này mà chuyển tới bước 3)

1. Đăng nhập vào tài khoản PythonAnywhere và truy cập vào Dashboard

2. Trong Dashboard có mục File, truy cập vào Browse files

3. Chọn nút Upload a file, chọn file mã nguồn đang được nén dưới dạng zip được tải [từ đây](https://github.com/tandotbt/Nine_CMD_sign/releases). Tên file zip đặt lại cho ngắn gọn ví dụ là <b>srcCode.zip</b>

- Bước 3: Tạo môi trường ảo

1. Trong Dashboard có mục File, truy cập vào Browse files. Sau đó tìm tới nút Open Bash console here và click để mở giao diện Console

2. Trong giao diện Console, bạn sẽ thấy một dòng lệnh sẵn sàng để nhập. Gõ lệnh sau để tạo môi trường ảo mới với phiên bản python 3.10 (ví dụ tên môi trường là <b>envServer9cmd</b>):

```
mkvirtualenv envServer9cmd --python=/usr/bin/python3.10
```

- Bước 4: Cài các pip vào môi trường ảo <b>envServer9cmd</b>, nếu console không có dạng `(envServer9cmd) $` thì nhập `workon envServer9cmd` rồi enter là sẽ ok, việc cài pip này sẽ cần chút thời gian

```bash
pip install flask
pip install flask-cors
pip install Flask-HTTPAuth
```

- Bước 5: Giải nén file mã nguồn zip

1. Sau khi cài pip xong, gõ thêm 1 dòng mã để giải nén file zip với tên <b>srcCode</b> như đã đặt bên trên

```bash
unzip srcCode.zip
```

(Sử dụng cách mới)

1. Dán mã sau và nhấn enter

```bash
git clone https://github.com/tandotbt/Nine_CMD_sign.git
```

2. Lưu ý đường dẫn của Working directory sẽ cần sửa thành <b>/home/tanbt/Nine_CMD_sign/</b> thay vì dùng đường dẫn mặc định đang cài, sau đó làm theo hướng dẫn

- Bước 6: Tạo web

1. Giờ quay lại Dashboard, chọn Open Web tab và chọn tiếp Add a new web app

2. Next --> Manual configuration --> Python 3.10 --> Next

3. Sau khi tạo xong bạn cuộn chuột tìm mục Source code, chỉnh thành đường dẫn <b>giống hệt Working directory</b> ngay bên dưới có dạng như <b>/home/tanbt/</b>

4. Mục Virtualenv bên dưới bạn nhập tên của môi trường ảo tạo ở bước 3 là <b>envServer9cmd</b> thì web tự nhận đường dẫn

5. Mục Force HTTPS bên dưới bạn gạt sang <b>Enabled</b>

6. Mục WSGI configuration file bạn nhấn vào sẽ được đưa tới cửa sổ chỉnh file, xóa hết và paste dòng sau. Thay <b>/home/tanbt/</b> thành đường dẫn <b>giống hệt Working directory</b> của bạn. Nhớ nhấn nút <b>Save</b> là ok

```python
import sys
path = '/home/tanbt/'
if path not in sys.path:
    sys.path.append(path)
from main import app as application
```

- Bước 7: Tùy chỉnh bảo mật

1. Ok vậy là xong bước cài đặt ban đầu, quay lại Dashboard, chọn Open Web tab

2. Dòng đầu tiên Configuration for <tên tài khoản>.pythonanywhere.com thì <tên tài khoản>.pythonanywhere.com chính là url của bạn, ví dụ như <i> tanbt.pythonanywhere.com</i>

3. Cạnh Source code có Go to directory, nhấn vào đó sẽ ra thư mục chứa file main.py và thư mục UTC.

Trong file main.py tìm tới các dòng sau và chỉnh sửa theo mong muốn của bạn để bảo mật hơn sau đó Save lại
Từ phiên bản v1 thì những dữ liệu này được chỉnh sửa trong tệp config.json, và vẫn cần reload lại để áp dụng cho chắc

```python
# Username và password xác thực
USERNAME_API = "admin"
PASSWORD_API = "admin"
# Danh sách IP cho phép ngăn truy cập lạ, với lần truy cập đầu bạn sẽ biết được ip của mình
# Để trống [] sẽ cho phép tất cả các ip truy cập
ALLOWED_IPS = []
# Danh sách các giao dịch không mong muốn ví dụ "transfer_asset" là chuyển NCG
UNWANTED_KEYWORDS = ["transfer_asset"]
```

Trong thư mục UTC thì bạn cần upload file UTC của ví muốn sử dụng, nếu có câu hỏi hãy tìm liên hệ của tôi phía dưới

4. Ở trang cài đặt web có 1 nút Disable webapp, nút này dùng để tạm ngưng hoạt động của web. Bạn có thể tạm dừng web để bảo mật hoàn toàn khi nào muốn dùng thì kích hoạt lại sau

5. Nút Run until 3 months from today sẽ được sử dụng để duy trì web được kích hoạt, để quá 3 tháng thì sẽ bị tạm dừng

6. <b>Và quan trọng nhất là nút Reload</b>, nút này sẽ làm mới trang để áp dụng các thay đổi, bạn thay đổi các tùy chọn bảo mật mà không nhấn nút này thì không được áp dụng

## Liên hệ

- Discord: https://discordapp.com/users/466271401796567071
- Telegram: https://t.me/tandotbt
- Group tele vnNineChronicles: https://t.me/viNineChronicles
