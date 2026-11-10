# Thu file "Cai dat dong bo CapCut.bat" tren Windows that (may GitHub): gia lap Google Drive o o X:, cai, kiem tra o M + loi tat CapCut
$ErrorActionPreference = 'Stop'
$base = 'C:\gd'; $root = Join-Path $base 'Drive của tôi\PHÒNG TRUYỀN THÔNG MICC'
$sys = Join-Path $root 'MICC media · Hệ thống (không xóa)\AI dựng CapCut'
$rel = 'CÔNG VIỆC/Dự án A/SOURCE/Kịch bản 1/Khám phá dự án'
$proj = Join-Path $root ($rel -replace '/', '\')
New-Item -ItemType Directory -Force -Path (Join-Path $root 'SETUP'), $sys, (Join-Path $proj 'AI tải về') | Out-Null
$vid = Join-Path $root 'CÔNG VIỆC\Dự án A\SOURCE\Kịch bản 1\DJI_0001.MP4'; Set-Content -LiteralPath $vid -Value 'x'
Set-Content -LiteralPath (Join-Path $proj 'AI tải về\Nhac nen.mp3') -Value 'x'
$dc = '{"materials":{"videos":[{"path":"M:/CÔNG VIỆC/Dự án A/SOURCE/Kịch bản 1/DJI_0001.MP4"}],"audios":[{"path":"M:/CÔNG VIỆC/Dự án A/SOURCE/Kịch bản 1/Khám phá dự án/AI tải về/Nhac nen.mp3"}]}}'
foreach ($n in 'draft_content.json', 'draft_info.json', 'draft_meta_info.json') { [IO.File]::WriteAllText((Join-Path $proj $n), $dc, (New-Object Text.UTF8Encoding($false))) }
[IO.File]::WriteAllText((Join-Path $sys 'Danh sách project CapCut.txt'), "$rel`r`n", (New-Object Text.UTF8Encoding($false)))
& subst.exe X: $base
$bat = 'X:\Drive của tôi\PHÒNG TRUYỀN THÔNG MICC\SETUP\Cài đặt đồng bộ CapCut.bat'
Copy-Item -LiteralPath (Join-Path $env:GITHUB_WORKSPACE 'capcut\thu\cai-dat-dong-bo.bat') -Destination $bat
Write-Host '=== CHAY FILE CAI ==='
cmd.exe /c "`"$bat`" < NUL"
Write-Host "ma thoat: $LASTEXITCODE"
$log = Join-Path $env:LOCALAPPDATA 'MICC\capcut-sync.log'; Write-Host '=== NHAT KY ==='; if (Test-Path $log) { Get-Content $log }
$bad = @()
if (-not (Test-Path -LiteralPath 'M:\SETUP')) { $bad += 'khong co o M:' }
foreach ($p in ([regex]::Matches($dc, '"path":"([^"]+)"') | ForEach-Object { $_.Groups[1].Value })) { if (-not (Test-Path -LiteralPath $p)) { $bad += "khong thay file $p" } }
$lnk = Join-Path $env:LOCALAPPDATA 'CapCut\User Data\Projects\com.lveditor.draft\Khám phá dự án'
if (-not (Test-Path -LiteralPath (Join-Path $lnk 'draft_content.json'))) { $bad += 'chua co loi tat project trong CapCut' }
elseif (-not ((Get-Item -LiteralPath $lnk).Attributes -band [IO.FileAttributes]::ReparsePoint)) { $bad += 'project bi chep ve may thay vi loi tat' }
if (-not (Get-ScheduledTask -TaskName 'MICC CapCut Sync' -ErrorAction SilentlyContinue)) { $bad += 'chua dat lich chay ngam' }
$run = (Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -ErrorAction SilentlyContinue).'MICC o M'
if (-not $run) { $bad += 'chua dat tu gan o M khi dang nhap' }
Write-Host '=== KET QUA ==='
if ($bad) { $bad | ForEach-Object { Write-Host "LOI: $_" }; exit 1 } else { Write-Host 'DAT: o M, file trong project, loi tat CapCut, lich chay ngam deu dung' }
