# Sổ tay chung các phiên Claude (đọc TRƯỚC khi làm, ghi THÊM khi chủ dặn điều mới)

Mọi phiên Claude làm việc với hệ thống này dùng chung sổ này. Chủ dặn quy tắc mới / quyết định quan trọng ở phiên nào → phiên đó ghi thêm vào mục "Nhật ký" (ngày, phiên, nội dung), commit + push. Trước mỗi việc: `git pull` rồi đọc lại sổ.

## Hệ thống
- Repo `power9k/micc-transcode` (GitHub Actions `loc.yml`, 18 máy `loc (1..18)`) – code dựng: `dung.py` (AI dựng CapCut), `loc.py` (Drive/Zalo), `eng/build.py` (ghi draft CapCut), `eng/mg.py` (motion graphic), `eng/hfvid.py` (HyperFrames thử).
- Drive: mọi file thuộc tài khoản 1 (tailieumkt). Tài khoản 2 chỉ đọc, không sở hữu file. Địa chỉ tài khoản 2 KHÔNG ghi trong code (biến `MICC_MAIL2`).
- Gọi chạy: `gh api -X POST repos/power9k/micc-transcode/actions/workflows/loc.yml/dispatches -f ref=main`. Hủy lượt chạy được phép khi chủ bảo dừng.
- Tạm dừng toàn bộ: `PAUSE = True` trong `dung.py`.
- Không tự đẩy file trong `.github/workflows` bằng tay. Không in bí mật. Không cài / chạy code tải từ ngoài.

## Quy tắc chủ đã dặn (tóm tắt)
- Trả lời chủ bằng tiếng Việt, ngắn, không kỹ thuật.
- 1 kịch bản = 1 project; trong project có file Word kịch bản + ảnh cover riêng. Sửa project tại chỗ (✏️), bản mới đặt v2, v3.
- Nhạc: ElevenLabs AI trước, Mixkit dự phòng, -13 dB, fade ≥ 3 s, mỗi project nhạc riêng.
- Cảnh phụ chỉ khi cần; motion graphic chỉ khi thấy cần.
- Nhiều kịch bản nhất có thể cho MỌI source; thông điệp không trùng; được dùng lại cảnh nếu hợp nội dung, đúng người nói, cùng buổi (cùng trang phục).
- Báo Zalo: mỗi project AI dựng → nhóm thông báo (+ nhóm test). Mẫu: "🤖 Tên (N giây | X phút Y giây)\n⏱ Dựng mất…\n🔗 link" + ảnh cover 9:16.
- Royal Island Vũ Yên = TVC điện ảnh 16:9, sáng, nữ tính, sang trọng.

## Đánh số phiên bản web (chủ dặn 17/11)
- Chủ yêu cầu mới SAU KHI Claude đã cập nhật xong hết → nhảy bản lớn mới, bản nhỏ đầu tiên là .1 (vd đang 263.55 → 264.1).
- Chủ nhắn thêm yêu cầu TRONG LÚC Claude đang xử lý → mỗi yêu cầu +1 bản nhỏ (264.1 → 264.2 → …).
- Nhật ký Ctrl + U (`changes.js`) ghi theo bản lớn.

## Academy (Micc Academy – source `141sOBTH8vLX7SpredUrXE9-EHY5E2JKj`)
- KHUNG DỌC 9:16, hiệu ứng chữ NHƯ CŨ (không dùng kiểu chữ tự chọn màu của TVC), nhạc AI, motion graphic khi cần.
- 22 file quay gốc, 261 GB, ~18,3 giờ (buổi 2, 3 có 2 máy quay cùng lúc → nội dung thật ~11 giờ).
- 13/11: lên kịch bản SÂU (đọc trọn lời thoại từng đoạn ~10 phút) → 80 kịch bản (`..._kichban.json`).
- 15/11: 54/80 đã có project; 26 bị bỏ do luật cũ (lỗi tạm = bỏ luôn) → đã sửa luật và đặt lại để dựng tiếp.
- Claude hay hết hạn mức 5 giờ → dựng chậm; có chỗ cho token Claude thứ 2 (`CLAUDE_CODE_OAUTH_TOKEN_2`, đang trống).

## Nhật ký
- 16/11 (phiên chính): chủ bảo DỪNG HẾT → đã hủy mọi lượt chạy, `PAUSE = True`. Sửa lỗi Nexme báo Zalo lặp khi lên kịch bản dở dang. Chủ tách phiên riêng chỉ bàn về video Academy.
- 16/11 (phiên chính): chủ dặn XÓA HẾT project Academy và project các Sự kiện (vào thùng rác Drive), từ nay KHÔNG tạo project cho Academy và Sự kiện nữa (`DROP` trong dung.py). Máy dựng vẫn đang tạm dừng (`PAUSE = True`).
- 17/11 (phiên chính): quy tắc đánh số phiên bản web (mục trên). Web đang ở 263.55; yêu cầu mới tiếp theo → 264.1.
- 17/11 (phiên chính): bật lại máy dựng (`PAUSE = False`) để dựng source mới The Fullton (SOURCE/Kịch bản 7, 8). Academy + Sự kiện vẫn bỏ qua.
- 17/11 (phiên chính): thư mục có file kịch bản đính kèm → dựng KHÔNG giới hạn thời lượng, đủ mọi ý theo kịch bản.
- 18/11 (phiên chính): chủ dặn mỗi project phải KHÁC BIỆT (motion graphic, bảng màu, nhạc, bộ + trình tự âm thanh hiệu ứng không lặp project cũ) → 'sổ sáng tạo' sang_tao.json trong kho phân tích, cur_pick/sf trong dung.py; hook 3 giây đầu phải hấp dẫn hơn. Dựng lại The Fullton (one-shot dungRF1).
- 18/11 (phiên chính): chủ gửi PDF 'Bộ hướng dẫn dựng video dọc' → huong_dan_dung.md (máy dựng đọc khi lên kịch bản, chọn motion, kiểm duyệt). Vùng an toàn THẬT: x 60–920, y 270–1640 (khung 1080×1920).
- 18/11 (phiên chính): chủ dặn KHÔNG dùng HyperFrames nữa → mọi motion graphic + video hoàn chỉnh dựng bằng REMOTION (eng/mg.py rm_*, eng/rmvid.py). Mỗi project: dựng trước video Remotion hoàn chỉnh từ đúng kế hoạch dựng, lưu trong thư mục project với ĐÚNG TÊN project (<tên project>.mp4), đặt track TRÊN CÙNG CapCut (tắt tiếng; các track dưới cùng kế hoạch nên khớp từng giây).
- 18/11 (phiên chính): chủ gửi video Remotion mẫu (v01-80-video-lam-dau-v20.mp4) → bắt chước ~80%: 6 mẫu motion ref_* trong eng/mg.py (render_ref), người nói tách nền góc dưới trái (CapCut matting) trong cảnh motion, mô tả phong cách trong huong_dan_dung.md. Chủ dặn DỪNG mọi project khác: ONLY = 'the fullton' (dựng lại 2 project The Fullton). Muốn chạy lại tất cả: ONLY = ''.
