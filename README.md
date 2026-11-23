# nghe-van-ban

Công cụ chuyển văn bản thành giọng nói, tạo tệp MP3 có thể nghe trên Safari của iPhone.

## Sử dụng trên GitHub Pages

1. Mở trang GitHub Pages của repository trên Safari.
2. Nhập văn bản hoặc chọn tệp `.txt`/`.doc`/`.docx`/`.pdf`, rồi chọn giọng và tốc độ. `.doc` hỗ trợ định dạng Word 97–2003 không bị mã hóa; nếu không đọc được, hãy lưu tệp thành `.docx`. PDF cần có lớp văn bản; PDF chỉ chứa ảnh quét không được OCR. **Đọc ngay (Máy)** dùng giọng đã chọn trên thiết bị; nếu chọn giọng Cloud, trang tự chọn giọng phù hợp trên thiết bị. Nút **Chọn toàn bộ văn bản** chọn nội dung trong ô.
3. Để tạo MP3 hoặc xóa file, nhấn biểu tượng **⚙️** cạnh tiêu đề để mở cài đặt Token, nhập và lưu GitHub Personal Access Token (PAT). Với fine-grained PAT, cấp quyền truy cập repository này và quyền **Actions: Read and write** cùng **Contents: Read and write**. Token classic cần quyền `repo`.
4. Nhấn **Tạo MP3 (Cloud)** và chờ **Đã xong!**. Các MP3 được lưu thành file riêng trong danh sách phát; nhấn **Phát** để nghe hoặc **Xóa** để xóa file khỏi nhánh `main`. Xóa khỏi nhánh hiện tại không xóa file khỏi lịch sử Git. Nếu chọn giọng trên thiết bị, MP3 sử dụng giọng Hoài Mỹ. Safari có thể yêu cầu thao tác nhấn phát của người dùng.

Token được lưu trong `localStorage` của trình duyệt, không được mã hóa và có thể bị mã chạy trên trang truy cập. Chỉ sử dụng trên thiết bị tin cậy; có thể xóa token trong phần cài đặt. Văn bản, MP3 và đoạn trích trong `audio/meta.json` được lưu trên nhánh `main` và công khai nếu repository công khai; không gửi nội dung nhạy cảm.

Trang kiểm tra kết quả qua GitHub API và tải MP3 từ cùng một commit, không phụ thuộc vào thời điểm GitHub Pages triển khai lại. Mỗi lần tạo có một file riêng; nếu quá 10 phút chưa có kết quả, kiểm tra tab **Actions**.

## Thư viện Pháp luật

Trang không gọi trực tiếp Thư viện Pháp luật. Đặt hằng số `TVPL_API_BASE` trong `index.html` thành URL gốc của một proxy tin cậy, ví dụ `https://proxy.example.com/tvpl`, rồi triển khai lại GitHub Pages. URL phải dùng HTTPS (HTTP chỉ cho phép trên localhost). Proxy cần hỗ trợ CORS cho origin GitHub Pages và các header `Content-Type`, `Authorization`; không chuyển hướng các yêu cầu. Repository này **không cung cấp proxy**: cần tự triển khai dịch vụ có quyền truy cập phù hợp và tuân thủ điều khoản của Thư viện Pháp luật.

Hợp đồng JSON giữa trang và proxy:

- `POST /login`: nhận `{"username":"...","password":"..."}`, trả `{"token":"..."}` khi đăng nhập thành công; trả HTTP 401/403 nếu không hợp lệ.
- `GET /documents?q=...`: nhận token phiên trong header `Authorization` theo scheme Bearer, trả `{"results":[{"id":"...","title":"...","number":"...","summary":"..."}]}`. `id` và `title` là chuỗi bắt buộc; `number`, `summary` là tùy chọn.
- `GET /documents/{id}`: nhận cùng header, trả `{"text":"..."}` với nội dung văn bản đã làm sạch; hoặc `{"html":"..."}` để trang loại bỏ các thành phần HTML thông dụng. Proxy nên trích xuất đúng nội dung chính và loại quảng cáo, header, footer trước khi trả về vì cấu trúc trang nguồn có thể thay đổi. `id` là định danh, không phải URL.

Proxy phải bảo vệ thông tin đăng nhập và phiên, chỉ truy cập các nguồn được phép, không ghi log mật khẩu và trả lỗi HTTP phù hợp. Mật khẩu chỉ gửi đến proxy đã cấu hình và được xóa khỏi ô sau khi đăng nhập thành công. Token TVPL chỉ giữ trong bộ nhớ của trang, mất khi tải lại hoặc đăng xuất; đăng xuất trên trang không thu hồi phiên phía máy chủ. Mã chạy trên trang vẫn có thể truy cập phiên này, nên chỉ sử dụng trên thiết bị tin cậy.

Để trống `TVPL_API_BASE` sẽ bật **chế độ mẫu**, không kết nối hoặc xác thực tài khoản thật. Chế độ này chấp nhận bất kỳ user/pass không rỗng và chỉ trả dữ liệu minh họa, không phải văn bản pháp luật. Kiểm thử nhanh:

1. Mở **Cài đặt Thư viện Pháp luật**, nhập user/pass và nhấn **Đăng nhập**; cài đặt đóng sau khi thành công.
2. Tìm `88/2021/TT-BTC`, chọn kết quả rồi nhấn **Tải văn bản**. Với chế độ mẫu, nội dung chỉ mang tính minh họa.
3. Kiểm tra nội dung xuất hiện trong ô **Văn bản**, sau đó nhấn **Đọc ngay (Máy)** hoặc **Tạo MP3 (Cloud)**. Tạo MP3 vẫn cần GitHub PAT như hướng dẫn ở trên.

## Chạy workflow thủ công

1. Mở repository này trên GitHub và chọn tab **Actions**.
2. Chọn workflow **Chuyển văn bản thành giọng nói**, nhấn **Run workflow**.
3. Nhập văn bản, chọn giọng đọc và nhập tốc độ theo phần trăm thay đổi (ví dụ `-50%`, `+0%`, `+100%`), rồi nhấn **Run workflow** để bắt đầu.
4. Mở lần chạy vừa hoàn tất, kéo xuống mục **Artifacts** và tải `audio-ket-qua`.
5. Mở tệp `doc-van-ban.mp3` đã tải về để nghe trên iPhone.

Workflow chạy bằng Python 3.11 và `edge-tts`. Các tệp MP3 riêng và metadata mới nhất được commit vào `audio/` trên `main`; artifact `audio-ket-qua` được giữ trong 3 ngày.
