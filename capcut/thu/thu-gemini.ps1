# Thu file "Ket noi Gemini Pro.bat": gia lap da dang nhap (chia khoa gia), kiem tra file khoa hoa duoc tao dung cho tren Drive gia
$ErrorActionPreference = 'Stop'
$base = 'C:\gd2'; $root = Join-Path $base 'Drive của tôi\PHÒNG TRUYỀN THÔNG MICC'
New-Item -ItemType Directory -Force -Path (Join-Path $root 'SETUP') | Out-Null
& subst.exe Y: $base
$gd = Join-Path $env:USERPROFILE '.gemini'; New-Item -ItemType Directory -Force -Path $gd | Out-Null
Set-Content -Path (Join-Path $gd 'oauth_creds.json') -Value '{"access_token":"THU-GIA","refresh_token":"THU-GIA-2","token_type":"Bearer"}' -Encoding ASCII
$bat = 'Y:\Drive của tôi\PHÒNG TRUYỀN THÔNG MICC\SETUP\Kết nối Gemini Pro.bat'
Copy-Item -LiteralPath (Join-Path $env:GITHUB_WORKSPACE 'capcut\thu\ket-noi-gemini.bat') -Destination $bat
cmd.exe /c "`"$bat`" < NUL"
$f = Get-ChildItem -Recurse -Filter 'Khoa Gemini.bin' 'C:\gd', 'C:\gd2' -ErrorAction SilentlyContinue | Select-Object -First 1   # bước trước cũng gắn một Drive giả (X:), file có thể nằm ở đó
if (-not $f) { Write-Host 'LOI: khong tao duoc Khoa Gemini.bin'; exit 1 }
Write-Host ('DAT: tao ' + $f.FullName + ' (' + $f.Length + ' byte)')
Write-Host ('MAU=' + [Convert]::ToBase64String([IO.File]::ReadAllBytes($f.FullName)))
