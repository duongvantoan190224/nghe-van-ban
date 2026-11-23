# nghe-van-ban

Công cụ chuyển văn bản thành giọng nói, tạo tệp MP3 có thể nghe trên Safari của iPhone.

## Sử dụng trên GitHub Pages

1. Mở trang GitHub Pages của repository trên Safari.
2. Nhập văn bản hoặc chọn tệp `.txt`/`.doc`/`.docx`/`.pdf`, rồi chọn giọng và tốc độ. `.doc` hỗ trợ định dạng Word 97–2003 không bị mã hóa; nếu không đọc được, hãy lưu tệp thành `.docx`. PDF cần có lớp văn bản; PDF chỉ chứa ảnh quét không được OCR. **Đọc ngay (Máy)** dùng giọng đã chọn trên thiết bị; nếu chọn giọng Cloud, trang tự chọn giọng phù hợp trên thiết bị. Nút **Chọn toàn bộ văn bản** chọn nội dung trong ô.
3. Để tạo MP3 hoặc xóa file, nhấn biểu tượng **⚙️** cạnh tiêu đề để mở cài đặt Token, nhập và lưu GitHub Personal Access Token (PAT). Với fine-grained PAT, cấp quyền truy cập repository này và quyền **Actions: Read and write** cùng **Contents: Read and write**. Token classic cần quyền `repo`.
4. Nhấn **Tạo MP3 (Cloud)** và chờ **Đã xong!**. Các MP3 được lưu thành file riêng trong danh sách phát; nhấn **Phát** để nghe hoặc **Xóa** để xóa file khỏi nhánh `main`. Xóa khỏi nhánh hiện tại không xóa file khỏi lịch sử Git. Nếu chọn giọng trên thiết bị, MP3 sử dụng giọng Hoài Mỹ. Safari có thể yêu cầu thao tác nhấn phát của người dùng.

Token được lưu trong `localStorage` của trình duyệt, không được mã hóa và có thể bị mã chạy trên trang truy cập. Chỉ sử dụng trên thiết bị tin cậy; có thể xóa token trong phần cài đặt. Văn bản, MP3 và đoạn trích trong `audio/meta.json` được lưu trên nhánh `main` và công khai nếu repository công khai; không gửi nội dung nhạy cảm.

Trang kiểm tra kết quả qua GitHub API và tải MP3 từ cùng một commit, không phụ thuộc vào thời điểm GitHub Pages triển khai lại. Mỗi lần tạo có một file riêng; nếu quá 10 phút chưa có kết quả, kiểm tra tab **Actions**.

## Tài liệu Google Drive

Proxy Python trong `proxy/` đọc các tệp `.docx` và `.pdf` trực tiếp trong [thư mục Drive công khai](https://drive.google.com/drive/folders/1G9hMq9r0g7KJoz09n61SqTTcXLiE1akl). Không cần đăng nhập trên trang. Chỉ tệp công khai, nằm trực tiếp trong thư mục và có đúng định dạng được hỗ trợ; thư mục con và Google Docs không được liệt kê. Tìm kiếm không phân biệt hoa thường theo tên tệp; để trống để liệt kê tất cả.

Proxy dùng Drive API v3 và cần một API key trên máy chủ. Bật Google Drive API trong Google Cloud, tạo key và giới hạn key cho Drive API và địa chỉ IP ngoài của VPS. Không đưa key vào Git, `index.html`, URL hoặc log. Quyền xem công khai của thư mục **và các tệp** phải cho phép Drive API đọc chúng.

### Triển khai trên VPS

1. Cài Python 3.11+, nginx và Certbot; trỏ DNS của tên miền proxy tới VPS và mở cổng 80/443. Tạo môi trường ảo và cài `python -m pip install -r proxy/requirements.txt`.
2. Tạo tệp cấu hình môi trường chỉ máy chủ đọc được, chẳng hạn `/etc/nghe-van-ban.env` với quyền `600`, chứa `GOOGLE_DRIVE_API_KEY=<key>`. Chạy `proxy/server.py` bằng Python trong môi trường ảo, dưới tài khoản hệ thống không đặc quyền; dùng systemd hoặc trình quản lý tiến trình để nạp tệp môi trường và tự khởi động lại. Server chỉ lắng nghe `127.0.0.1:8000`; không mở cổng này ra Internet.
3. Cấp chứng chỉ Let's Encrypt cho tên miền bằng Certbot. Đưa `proxy/nginx.conf` vào **http context** của nginx, thay toàn bộ `proxy.example.com` bằng tên miền thực và kiểm tra đường dẫn chứng chỉ. Kiểm tra `nginx -t`, reload nginx và cấu hình gia hạn chứng chỉ tự động. Mẫu bật TLS, giới hạn 20 yêu cầu/phút/IP (burst 10), tối đa 3 kết nối/IP và CORS chỉ cho `https://duongvantoan190224.github.io`. Nếu nginx ở sau proxy/load balancer khác, chỉ cấu hình real IP cho upstream đáng tin cậy.
4. Đặt `TVPL_API_BASE` trong `index.html` thành URL HTTPS gốc thực tế, ví dụ `https://proxy.example.com` (không có dấu `/` cuối), rồi triển khai lại GitHub Pages. URL hiện để trống vì chưa có tên miền/VPS được cung cấp; khi để trống giao diện báo chưa cấu hình, không dùng dữ liệu mẫu. HTTP chỉ chấp nhận cho localhost.

Hợp đồng proxy:

- `GET /documents?q=...` trả `{"results":[{"id":"...","title":"..."}]}`; `q` là tùy chọn.
- `GET /documents/{id}` trả `{"text":"..."}`. ID phải thuộc thư mục được cấu hình; proxy không nhận URL tùy ý. Lỗi trả JSON `{"error":"..."}` cùng HTTP status tương ứng.

DOCX lấy nội dung body (bao gồm bảng), không lấy header/footer. PDF dùng lớp văn bản, bỏ dòng đầu/cuối lặp lại trên ít nhất 2/3 số trang khi có ít nhất 3 trang; quy tắc này có thể bỏ sót hoặc nhầm nội dung, nên kiểm tra lại kết quả. PDF scan không được OCR, PDF mã hóa không được hỗ trợ; tệp tối đa 20 MB. Bố cục PDF và phông chữ có thể ảnh hưởng chất lượng trích xuất.

Sau khi triển khai, mở GitHub Pages, nhấn **Tìm / liệt kê tài liệu**, chọn tệp và nhấn **Tải văn bản**, rồi kiểm tra nội dung và nhấn **Đọc ngay (Máy)** hoặc **Tạo MP3 (Cloud)**. Tạo MP3 vẫn cần GitHub PAT và công khai dữ liệu như hướng dẫn phía trên. CORS chỉ hạn chế trình duyệt, không phải xác thực: bất kỳ ai vẫn có thể gọi API công khai trực tiếp và tiêu thụ quota, nên theo dõi quota và điều chỉnh rate limit khi cần.

## Chạy workflow thủ công

1. Mở repository này trên GitHub và chọn tab **Actions**.
2. Chọn workflow **Chuyển văn bản thành giọng nói**, nhấn **Run workflow**.
3. Nhập văn bản, chọn giọng đọc và nhập tốc độ theo phần trăm thay đổi (ví dụ `-50%`, `+0%`, `+100%`), rồi nhấn **Run workflow** để bắt đầu.
4. Mở lần chạy vừa hoàn tất, kéo xuống mục **Artifacts** và tải `audio-ket-qua`.
5. Mở tệp `doc-van-ban.mp3` đã tải về để nghe trên iPhone.

Workflow chạy bằng Python 3.11 và `edge-tts`. Các tệp MP3 riêng và metadata mới nhất được commit vào `audio/` trên `main`; artifact `audio-ket-qua` được giữ trong 3 ngày.
