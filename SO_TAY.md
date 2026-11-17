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

## Academy (Micc Academy – source `141sOBTH8vLX7SpredUrXE9-EHY5E2JKj`)
- KHUNG DỌC 9:16, hiệu ứng chữ NHƯ CŨ (không dùng kiểu chữ tự chọn màu của TVC), nhạc AI, motion graphic khi cần.
- 22 file quay gốc, 261 GB, ~18,3 giờ (buổi 2, 3 có 2 máy quay cùng lúc → nội dung thật ~11 giờ).
- 13/11: lên kịch bản SÂU (đọc trọn lời thoại từng đoạn ~10 phút) → 80 kịch bản (`..._kichban.json`).
- 15/11: 54/80 đã có project; 26 bị bỏ do luật cũ (lỗi tạm = bỏ luôn) → đã sửa luật và đặt lại để dựng tiếp.
- Claude hay hết hạn mức 5 giờ → dựng chậm; có chỗ cho token Claude thứ 2 (`CLAUDE_CODE_OAUTH_TOKEN_2`, đang trống).

## Nhật ký
- 16/11 (phiên chính): chủ bảo DỪNG HẾT → đã hủy mọi lượt chạy, `PAUSE = True`. Sửa lỗi Nexme báo Zalo lặp khi lên kịch bản dở dang. Chủ tách phiên riêng chỉ bàn về video Academy.
- 17/11 (phiên Academy, Remotion): chủ chốt quy trình video Academy mới:
  - Mỗi video 1:30–2:00, lời diễn giải chi tiết, có ví dụ cụ thể; vẫn lên nhiều kịch bản nhất có thể (đã có 54 kịch bản từ 5 file buổi 13/10).
  - Cắt kỹ khoảng nghỉ, hơi thở, ậm ừ; câu nói lặp hay nói hỏng thì cắt còn một lần cho mượt.
  - Không làm nét: dùng thẳng file MP4 gốc chất lượng tốt nhất trên Drive (không dùng .LRF/720p/480p). Âm thanh chỉ lọc tạp âm.
  - Motion graphic phải vui mắt, nhiều hiệu ứng, tràn ngập vùng an toàn. Ví dụ nào được nhắc tới (kênh, người, dự án) phải có hình thật: avatar + tên kênh, ảnh chụp TikTok, video đang chạy, chỉ số like…, không chỉ có chữ.
  - Dựng bằng Remotion. Mốc thời gian từng chữ lấy bằng Whisper chạy trên máy GitHub (workflow riêng `asr-words.yml` trên nhánh claude/…, không đụng main).
