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

## 11/11 – chủ dặn thêm
- Motion graphic dựng bằng HyperFrames (eng/mg.py): đồ họa KHÔNG CHỮ (chữ làm trên CapCut), ghép cảnh quay gốc trong thẻ / điện thoại; màu theo tông web (nền xanh than --k0..k4, vàng --g1..g6).
- Thứ chỉ dùng cho 1 project (clip motion graphic, cover) lưu TRONG thư mục project; kho "AI tải về" chỉ giữ thứ dùng chung (nhạc, SFX, font).
- Mỗi thư mục project có file Word "Kịch bản - <tên>.docx".
- Mỗi project có ảnh cover riêng (draft_cover.jpg), khác hẳn cover mọi project khác (so dấu vân ảnh dungCH).
- Dựng lại: tên thêm v2, v3… ở cuối (không ghi "AI dựng lại"); mỗi kịch bản chỉ còn 1 project mới nhất.
- Máy dựng làm liên tục; bị chặn hạn mức thì tự ngưng chờ rồi chạy tiếp.

## 12/11 (đêm) – chủ dặn dựng lại TẤT CẢ từ đầu
- Xóa hết project AI kiểu cũ (purge_old, vào thùng rác Drive); dựng MỚI hoàn toàn, không ghi đè bản cũ.
- Thứ tự: source MỚI NHẤT trước → cũ dần; 16 máy: máy 1–12 dựng, máy 13–16 ưu tiên đọc source mới + ra kịch bản; xong project nào báo Zalo project đó.
- Khung người nói: đo mặt bằng số – mất đầu / chỉ thấy cằm, cổ → phủ cảnh phụ; zoom làm mất đỉnh đầu → bỏ zoom.
- Màu chữ: đo độ sáng nền đúng chỗ đặt chữ; nền sáng → chữ xanh than đậm (#0E2F6B), không để chữ sáng trên nền sáng.
- Motion graphic: nhiều đoạn nếu kịch bản cần (~1 đoạn / 8 s), mỗi đoạn một loại khác nhau; mỗi clip phối ngẫu nhiên nền × mặt nạ cắt cảnh quay (tròn, lục giác, vòm, chéo, khối, dải phim…) × bố cục × kiểu xuất hiện × chi tiết trang trí; giữ tông màu web.
- Zalo: gửi clip GỘP các motion graphic của project (mg - tổng hợp.mp4), không chèn link.
- Claude kiểm tra tối đa 6 vòng; các bước chọn nhạc / màu / phong cách dùng model mạnh nhất (opus).
- 12/11 sáng: nhạc nền LUÔN -13 dB; nhạc nền mỗi project KHÔNG trùng project nào đang có (dungMu trên thư mục project + giữ chỗ dungRes); kho hết bài → tự tải thêm nhạc Mixkit (miễn phí bản quyền) vào Kho chung / Nhạc nền.
- Motion graphic phải nằm ở LỚP CẢNH PHỤ (bshots) – bộ dựng chỉ đọc ashots/bshots; video có motion graphic → cover CapCut = khung đẹp của motion graphic.
- Chỉ phủ cảnh phụ lên đoạn người nói khi CHẮC khung xấu (mặt bị cắt ở khung gốc, hoặc ≥ 2 khung đã soi không thấy mặt) – thiếu dữ liệu không phải là xấu.
- 12/11 trưa: quy trình chốt – đọc source 1 lần (GitHub + Claude tải về), tự lên kịch bản, phân tích, motion graphic HyperFrames, tự dựng project, XONG mới đưa lên Drive. Dữ liệu làm việc giữ ở bộ nhớ đệm GitHub (tự xóa sau 7 ngày / khi đầy, xóa cũ nhất). Lúc dựng không tải video từ Drive. Tải có đăng nhập tài khoản MICC (không tải kiểu khách).
- Zalo: gửi thumbnail (Zalo bot không gửi được video). Giãn tải: 8 máy (6 dựng + 2 đọc), các máy vào lệch nhau, vẫn ≥ 1 project / 15 phút.
- 12/11 trưa: thời lượng KHÔNG cứng nhắc – nội dung đầy đủ là chính (thường > 1 phút, vượt 2 phút vẫn được nếu ý cần). Chỉ cắt câu vô nghĩa / ầm ừ / lặp / nói hỏng, không cắt kiến thức bổ trợ ở giữa.
- 12/11 chiều: chữ + motion graphic PHỐI HỢP – đoạn có chữ thì motion graphic thu gọn xuống dưới, chừa vùng chữ phía trên (dải nền tối), chữ CapCut đặt đúng vùng đó (y ≈ 11,5 %), màu vàng / trắng hợp nền xanh than.
- Cảnh phụ chỉ khi cần: tối đa ~35 % thời lượng, mỗi cảnh ≤ 3–4 s (trừ cảnh phủ bắt buộc và motion graphic).
- SỬA TRỰC TIẾP project: khoá ✏️ trước (đổi tên), chỉ thay đúng file cần sửa (draft_content/info, Motion graphic, cover, Word, Timelines), không xóa project.
- 12/11 chiều: nhạc nền AI ElevenLabs Music (khoá ELEVENLABS_API_KEY trong GitHub Secrets): Claude chia 1–4 đoạn theo cảm xúc kịch bản, mỗi đoạn prompt tiếng Anh 3200–4000 ký tự, force_instrumental (không lời), ghép lại; lưu trong thư mục project 'Nhạc nền AI'. Lỗi / hết credit → dùng kho Mixkit miễn phí.
