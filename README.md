# MICC media · Máy làm bản xem nhẹ 480p / 720p

Kho này chỉ chứa **chương trình chuyển video** (không có video hay dữ liệu nào của công ty).
Máy ảo GitHub tải video gốc từ Google Drive → làm bản 480p rồi 720p → đẩy lại lên Google Drive
(thư mục "MICC media · Bản xem nhẹ (không xóa)" trong kho) → xóa sạch bản tạm.

- Chạy khi web báo có video mới, và tự kiểm tra mỗi 30 phút.
- Cần 2 Secrets: `MICC_API` (link Web App Apps Script) và `MICC_SECRET` (khóa bí mật).
