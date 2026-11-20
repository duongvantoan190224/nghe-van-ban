# nghe-van-ban

Công cụ chuyển văn bản thành giọng nói, tạo tệp MP3 có thể nghe trên Safari của iPhone.

## Sử dụng trên GitHub Pages

1. Mở trang GitHub Pages của repository trên Safari.
2. Nhập văn bản hoặc chọn tệp `.txt`/`.doc`/`.docx`/`.pdf`, rồi chọn giọng và tốc độ. `.doc` hỗ trợ định dạng Word 97–2003 không bị mã hóa; nếu không đọc được, hãy lưu tệp thành `.docx`. PDF cần có lớp văn bản; PDF chỉ chứa ảnh quét không được OCR. **Đọc ngay (Máy)** dùng giọng đã chọn trên thiết bị; nếu chọn giọng Cloud, trang tự chọn giọng phù hợp trên thiết bị. Nút **Chọn toàn bộ văn bản** chọn nội dung trong ô.
3. Để tạo MP3 hoặc xóa file, nhấn biểu tượng **⚙️** cạnh tiêu đề để mở cài đặt Token, nhập và lưu GitHub Personal Access Token (PAT). Với fine-grained PAT, cấp quyền truy cập repository này và quyền **Actions: Read and write** cùng **Contents: Read and write**. Token classic cần quyền `repo`.
4. Nhấn **Tạo MP3 (Cloud)** và chờ **Đã xong!**. Các MP3 được lưu thành file riêng trong danh sách phát; nhấn **Phát** để nghe hoặc **Xóa** để xóa file khỏi nhánh `main`. Xóa khỏi nhánh hiện tại không xóa file khỏi lịch sử Git. Nếu chọn giọng trên thiết bị, MP3 sử dụng giọng Hoài Mỹ. Safari có thể yêu cầu thao tác nhấn phát của người dùng.

Token được lưu trong `localStorage` của trình duyệt, không được mã hóa và có thể bị mã chạy trên trang truy cập. Chỉ sử dụng trên thiết bị tin cậy; có thể xóa token trong phần cài đặt. Văn bản, MP3 và đoạn trích trong `audio/meta.json` được lưu trên nhánh `main` và công khai nếu repository công khai; không gửi nội dung nhạy cảm.

Trang kiểm tra kết quả qua GitHub API và tải MP3 từ cùng một commit, không phụ thuộc vào thời điểm GitHub Pages triển khai lại. Mỗi lần tạo có một file riêng; nếu quá 10 phút chưa có kết quả, kiểm tra tab **Actions**.

## Chạy workflow thủ công

1. Mở repository này trên GitHub và chọn tab **Actions**.
2. Chọn workflow **Chuyển văn bản thành giọng nói**, nhấn **Run workflow**.
3. Nhập văn bản, chọn giọng đọc và nhập tốc độ theo phần trăm thay đổi (ví dụ `-50%`, `+0%`, `+100%`), rồi nhấn **Run workflow** để bắt đầu.
4. Mở lần chạy vừa hoàn tất, kéo xuống mục **Artifacts** và tải `audio-ket-qua`.
5. Mở tệp `doc-van-ban.mp3` đã tải về để nghe trên iPhone.

Workflow chạy bằng Python 3.11 và `edge-tts`. Các tệp MP3 riêng và metadata mới nhất được commit vào `audio/` trên `main`; artifact `audio-ket-qua` được giữ trong 3 ngày.
