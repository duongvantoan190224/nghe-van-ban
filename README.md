# nghe-van-ban

Công cụ chuyển văn bản thành giọng nói, tạo tệp MP3 có thể nghe trên Safari của iPhone.

## Cách sử dụng trên điện thoại

1. Mở repository này trên GitHub và chọn tab **Actions**.
2. Chọn workflow **Chuyển văn bản thành giọng nói**, nhấn **Run workflow**.
3. Nhập văn bản, chọn giọng đọc và tốc độ, rồi nhấn **Run workflow** để bắt đầu.
4. Mở lần chạy vừa hoàn tất, kéo xuống mục **Artifacts** và tải `audio-ket-qua`.
5. Mở tệp `doc-van-ban.mp3` đã tải về để nghe trên iPhone.

Workflow chạy bằng Python 3.11 và `edge-tts`. Tệp MP3 được lưu dưới dạng artifact trong 3 ngày.
