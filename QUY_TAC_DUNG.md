# Quy tắc dựng AI (chủ dặn – AI đọc file này mỗi lần lên kịch bản)

## Bộ não
- Chỉ dùng Claude (gói Claude Max của chủ). Không dùng Gemini, không dựng theo luật khi thiếu AI.
- Claude hết hạn mức → dừng, đợi có hạn mức rồi làm tiếp.
- Tiết kiệm token tối đa: Sonnet xem hình, Opus lên kịch bản và kiểm duyệt; video đã đọc / đã xem thì không đọc lại.

## Đọc source
- Đọc HẾT thư mục SOURCE, kể cả mọi thư mục con; file mới tải lên phải được đọc ngay ở lượt sau.
- Trong lúc dựng project này thì vẫn đọc tiếp các thư mục source khác.
- Xem mọi khung hình chính, lời thoại có mốc từng chữ, nhãn âm thanh (gió, ồn, im lặng, nhạc), mặt người.
- Hiểu tổng source có những kịch bản gì; mỗi kịch bản 1 video DƯỚI 2 PHÚT.

## Dựng
- A-roll: đúng lời, nói trôi chảy, chọn bản nói hay nhất; không cắt giữa câu, không cắt mất chữ; bỏ ngập ngừng.
- B-roll khớp lời đang nói, đẹp (không rung / mờ / lóa), không lặp cảnh.
- Cắt cảnh, chuyển cảnh, giật zoom theo nhịp nhạc (kick, snare, điểm dồn).
- Máy quay bám mặt người nói; nhảy cỡ khung rộng / cận để che vết cắt.
- Chữ: cứ 1–3 giây có 1 cụm chữ nhấn, hiện đúng lúc người nói nói chữ đó; chữ 2 tầng (dòng viết tay dẫn ý + chữ đậm chính); trọn nghĩa, đúng chính tả; KHÔNG đè mặt người.
- Hiệu ứng chữ đa dạng, không lặp lại; luôn có nhấn nhá (zoom, chuyển cảnh, âm thanh "tít" khi hiện số liệu).
- Màu điện ảnh: lớp điều chỉnh màu riêng cho từng cảnh (theo màu gốc của cảnh).
- Nhạc nền: mỗi project 1 bài khác nhau, không đụng hàng.

## Giao project
- Tự kiểm tra trước khi giao (chữ sai / đè mặt / thiếu / thừa / đơn điệu / cảnh không khớp). Chưa đạt thì sửa, không giao bản lỗi.
- Đã đẩy lên Drive thì không tự rút lại hay ghi đè (trừ khi chủ bảo).
- Tên project ngắn gọn, chỉ ghi nội dung.
- Mỗi project mới: báo chủ kèm tổng số project đã hoàn thành. Không gửi tổng kết. Hết thư mục source thì báo xong.
- Mọi dữ liệu AI tự tạo để trong "MICC media · Hệ thống (không xóa)"; thư mục SETUP chỉ cho người dùng.

## Kỹ thuật (đúc kết từ các bản dựng trước)
- Cắt ở ranh giới từ (theo mốc từng chữ), chừa 0,06–0,15 s; bỏ "ừm/à", câu hỏng, tiếng ê-kíp ("3-2-1", "đó đúng rồi", "chưa được").
- Không bao giờ 2 giọng cùng lúc; cảnh phụ tắt tiếng. Cảnh không lời ≤ 1,2 s.
- Nhịp cắt trung bình ~2,5 s/cảnh; > 80 % là cắt thẳng trúng phách; chuyển cảnh có hiệu ứng chỉ 4–8 lần/video ở chỗ đổi ý / lộ cảnh lớn.
- Giật zoom 1,0 → 1,15–1,35 trên từ nhấn mạnh, trúng phách; khi người nói, khung từ từ tiến vào.
- Chữ: 1 cụm = từ khóa TO + 1 dòng nhỏ viết tay; không tách từ ghép ("HỘ KINH DOANH" 1 dòng); vùng an toàn x 6–86 %, y 14–76 %; hộp chữ cách mặt ≥ 4 % khung.
- Chữ sáng trên nền sáng → đổi màu đậm; không dùng nền ô chữ, viền đen dày, bóng loá.
- SFX theo nghĩa: "tít"/tiền xu khi nói giá – số liệu, whoosh đúng điểm cắt (2 whoosh cách nhau ≥ 2 s), SFX nhỏ hơn giọng.
- Nhạc thấp dưới giọng khi đang nói, lên ở chỗ nghỉ, mở đầu, kết.
