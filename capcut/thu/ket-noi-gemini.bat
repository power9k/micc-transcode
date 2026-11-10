<# : phan chay cua Windows
@echo off
chcp 65001 >nul
set "MICC_F=%~f0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$t=[IO.File]::ReadAllText($env:MICC_F,[Text.Encoding]::UTF8); iex $t"
pause
exit /b
#>
# KET NOI GEMINI PRO CHO MAY DUNG AI - bam dup, dang nhap Google 1 lan. Chia khoa dang nhap duoc KHOA HOA roi de tren Drive (chi may dung giai duoc).
$ErrorActionPreference = 'Continue'
Write-Host '=== KET NOI GEMINI PRO CHO MAY DUNG AI ===' -ForegroundColor Yellow
# 1) Node.js (Gemini CLI can Node 20+)
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  Write-Host 'Dang cai Node.js (1-3 phut)...' -ForegroundColor Yellow
  winget install -e --id OpenJS.NodeJS.LTS --silent --accept-package-agreements --accept-source-agreements | Out-Null
  $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { Write-Host 'Khong cai duoc Node.js. Hay cai tu nodejs.org roi bam lai file nay.' -ForegroundColor Red; return }
# 2) Dang nhap Google qua Gemini CLI
$gd = Join-Path $env:USERPROFILE '.gemini'; New-Item -ItemType Directory -Force -Path $gd | Out-Null
$set = Join-Path $gd 'settings.json'
Set-Content -Path $set -Encoding ASCII -Value '{"security":{"auth":{"selectedType":"oauth-personal"},"folderTrust":{"enabled":false}},"selectedAuthType":"oauth-personal"}'   # chon san dang nhap Google, khong hoi tin thu muc
Set-Location $gd
$cred = Join-Path $gd 'oauth_creds.json'
# luon dang nhap LAI tu dau (tranh dung nham tai khoan cu)
Remove-Item -Force -ErrorAction SilentlyContinue $cred, (Join-Path $gd 'google_accounts.json')
Write-Host ''
Write-Host 'BUOC 1: trinh duyet se mo trang dang nhap Google (neu khong tu mo, chep duong link hien ra dan vao trinh duyet):' -ForegroundColor Green
Write-Host '  - chon DUNG tai khoan co goi Gemini Pro / Ultra, bam Cho phep' -ForegroundColor Green
Write-Host '  - neu cua so hoi cach dang nhap: chon "Sign in with Google" roi Enter' -ForegroundColor Green
Write-Host '  - dang nhap xong (hoac thay dong chu do), go  /quit  roi Enter' -ForegroundColor Green
Write-Host ''
& npx -y @google/gemini-cli
if (-not (Test-Path $cred)) { Write-Host 'Chua dang nhap duoc. Bam lai file nay de thu lai.' -ForegroundColor Red; return }
# BUOC 2: thu goi Gemini that bang tai khoan vua dang nhap
Write-Host 'BUOC 2: dang thu goi Gemini bang tai khoan vua dang nhap...' -ForegroundColor Yellow
$o = (& npx -y @google/gemini-cli -p 'Chi tra loi dung 2 chu cai: OK' 2>&1 | Out-String)
if ($o -notmatch '\bOK\b' -or $o -match 'no longer supported|Failed|Error|error') {
  Write-Host ''
  Write-Host 'Google KHONG cho tai khoan nay dung Gemini qua dong lenh:' -ForegroundColor Red
  Write-Host ($o.Trim() -split "`n" | Select-Object -Last 4 | Out-String) -ForegroundColor Red
  Write-Host 'Hay bam lai file va dang nhap tai khoan khac (vd tai khoan Gemini Ultra ca nhan).' -ForegroundColor Red
  Remove-Item -Force -ErrorAction SilentlyContinue $cred
  return
}
Write-Host 'Goi thu thanh cong.' -ForegroundColor Green
# 3) Khoa hoa chia khoa dang nhap (AES-256 + RSA khoa cong khai cua may dung)
$pub = '<RSAKeyValue><Modulus>wKtpNjcKGotPKcuzJ/JhJfCzhFmRetIKi8/K3XASzNKQcOt/KsjijHBPfWaYb/ywNjOTARdwjUSbYJ+ICQD8CEG650+0b3rrZKH5jlT4H/jFISRIJnGD0umFlEgi/gS34qGmixUbpo2d/2mC7dTQwE3ePKZ5cTq4+8gHDyk9z20jegUo7QxuL7yJAsNU5pLVhpD6P9Ysvkg+lXIEnLZuzx34adrUkSYSTzOLmk22SBBgpe/kPNtoLS6+HcBEQz9Hb8+vX8vd1vWMvHA2jjZBeytu6ebXrzELwqrdEI0TXLKhWQDiXZJjwpNLyOlyCaV537jp+4C4CM7og4jUH+YG2w==</Modulus><Exponent>AQAB</Exponent></RSAKeyValue>'
$plain = [IO.File]::ReadAllBytes($cred)
$aes = [Security.Cryptography.Aes]::Create(); $aes.KeySize = 256; $aes.GenerateKey(); $aes.GenerateIV()
$ct = $aes.CreateEncryptor().TransformFinalBlock($plain, 0, $plain.Length)
$rsa = New-Object Security.Cryptography.RSACryptoServiceProvider; $rsa.FromXmlString($pub)
$ek = $rsa.Encrypt($aes.Key, $true)
$ms = New-Object IO.MemoryStream
$hd = [Text.Encoding]::ASCII.GetBytes('MGC1'); $ms.Write($hd, 0, 4)
$ms.WriteByte([byte]($ek.Length -shr 8)); $ms.WriteByte([byte]($ek.Length -band 255))
$ms.Write($ek, 0, $ek.Length); $ms.Write($aes.IV, 0, 16); $ms.Write($ct, 0, $ct.Length)
# 4) De len Drive: PHONG TRUYEN THONG MICC\MICC media · He thong (khong xoa)\AI dung CapCut\Khoa Gemini.bin
$root = $null
foreach ($d in (Get-PSDrive -PSProvider FileSystem)) {
  foreach ($md in @('Drive của tôi', 'My Drive')) {
    $p = Join-Path $d.Root (Join-Path $md 'PHÒNG TRUYỀN THÔNG MICC')
    if (Test-Path -LiteralPath (Join-Path $p 'SETUP')) { $root = $p; break }
  }
  if ($root) { break }
}
if (-not $root -and (Test-Path -LiteralPath 'M:\SETUP')) { $root = 'M:\' }
if (-not $root) { Write-Host 'Khong thay Google Drive (PHONG TRUYEN THONG MICC) tren may nay.' -ForegroundColor Red; return }
$dst = Join-Path $root 'MICC media · Hệ thống (không xóa)\AI dựng CapCut'
New-Item -ItemType Directory -Force -Path $dst | Out-Null
[IO.File]::WriteAllBytes((Join-Path $dst 'Khoa Gemini.bin'), $ms.ToArray())
Write-Host ''
Write-Host 'XONG. May dung AI se tu dung Gemini Pro tu luot sau (vai phut nua Drive dong bo len).' -ForegroundColor Green
