<# : phan chay cua Windows
@echo off
chcp 65001 >nul
set "MICC_F=%~f0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$t=[IO.File]::ReadAllText($env:MICC_F,[Text.Encoding]::UTF8); iex $t.Substring(0,$t.IndexOf('#'+'==== DONG BO ===='))"
pause
exit /b
#>
# CAI DAT DONG BO CAPCUT VOI GOOGLE DRIVE - bam dup 1 lan tren moi may. Bam lai bat ky luc nao = tao loi tat ngay.
# Project CapCut do AI dung tren Drive tu hien trong CapCut (loi tat, khong chep video ve may); xoa trong CapCut chi xoa loi tat, Drive van giu.
$ErrorActionPreference = 'Continue'
$mk = '#' + '==== DONG BO ===='
$t = [IO.File]::ReadAllText($env:MICC_F, [Text.Encoding]::UTF8)
$dir = Join-Path $env:LOCALAPPDATA 'MICC'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$sync = Join-Path $dir 'micc-capcut-sync.ps1'
[IO.File]::WriteAllText($sync, $t.Substring($t.IndexOf($mk)), (New-Object Text.UTF8Encoding($true)))
$boot = Join-Path $dir 'khoi-dong.ps1'
$bootText = @'
$local = Join-Path $env:LOCALAPPDATA 'MICC\micc-capcut-sync.ps1'
$mk = '#' + '==== DONG BO ===='
foreach ($d in (Get-PSDrive -PSProvider FileSystem)) {
  foreach ($md in @('Drive của tôi', 'My Drive')) {
    $f = Join-Path $d.Root (Join-Path $md 'PHÒNG TRUYỀN THÔNG MICC\SETUP\Cài đặt đồng bộ CapCut.bat')
    if (Test-Path -LiteralPath $f) {
      try { $t = [IO.File]::ReadAllText($f, [Text.Encoding]::UTF8); $i = $t.IndexOf($mk); if ($i -ge 0) { [IO.File]::WriteAllText($local, $t.Substring($i), (New-Object Text.UTF8Encoding($true))) } } catch {}
      break
    }
  }
}
& $local
'@
Set-Content -Path $boot -Value $bootText -Encoding UTF8
$vbs = Join-Path $dir 'chay-an.vbs'
Set-Content -Path $vbs -Encoding ASCII -Value ('CreateObject("WScript.Shell").Run "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File ""' + $boot + '""", 0, False')
$act = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument ('"' + $vbs + '"')
$t1 = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$t2 = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 2)
$set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -Hidden
Register-ScheduledTask -TaskName 'MICC CapCut Sync' -Action $act -Trigger @($t1, $t2) -Settings $set -Force | Out-Null
Write-Host 'Dang tao loi tat project vao CapCut...' -ForegroundColor Yellow
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $sync
$log = Join-Path $dir 'capcut-sync.log'
Write-Host '--- Nhat ky ---' -ForegroundColor Yellow
if (Test-Path $log) { Get-Content $log -Tail 12 } else { Write-Host 'Chua co nhat ky' }
Write-Host '--- Project CapCut tren may ---' -ForegroundColor Yellow
Get-ChildItem (Join-Path $env:LOCALAPPDATA 'CapCut\User Data\Projects\com.lveditor.draft') -Force -ErrorAction SilentlyContinue | Select-Object Name, LinkType | Format-Table -AutoSize
Write-Host 'XONG. Tu nay cu 2 phut may tu cap nhat. Tat han CapCut roi mo lai la thay project.' -ForegroundColor Green
Write-Host 'Neu chua thay, chup man hinh cua so nay gui AI.' -ForegroundColor Green
#==== DONG BO ====
# MICC CapCut Sync - tao loi tat (thu muc) tu Google Drive vao CapCut, chay ngam 2 phut/lan
# Danh sach project do may chu ghi: <Drive>\PHÒNG TRUYỀN THÔNG MICC\MICC media · Hệ thống (không xóa)\AI dựng CapCut\Danh sách project CapCut.txt (moi dong 1 duong dan tuong doi tu "PHÒNG TRUYỀN THÔNG MICC")
$ErrorActionPreference = 'SilentlyContinue'
$log = Join-Path $env:LOCALAPPDATA 'MICC\capcut-sync.log'
trap { Log ("LOI: " + $_.Exception.Message + " @ dong " + $_.InvocationInfo.ScriptLineNumber); continue }
function Log($m) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m" | Out-File -Append -Encoding utf8 $log }
# 1) tim o Google Drive CUA TAI KHOAN tailieumkt (G, H, I... bat ky chu nao): o co file danh dau o goc "Drive cua toi" (may chu tao, chi tai khoan nay co)
$root = $null
$mark = 'MICC - nhận diện ổ Drive (không xóa).txt'
foreach ($d in (Get-PSDrive -PSProvider FileSystem)) {
  foreach ($md in @('Drive của tôi', 'My Drive')) {
    $p = Join-Path $d.Root (Join-Path $md 'PHÒNG TRUYỀN THÔNG MICC')
    if ((Test-Path -LiteralPath (Join-Path (Join-Path $d.Root $md) $mark)) -and (Test-Path -LiteralPath $p)) { $root = $p; break }
  }
  if ($root) { break }
}
if (-not $root) { foreach ($d in (Get-PSDrive -PSProvider FileSystem)) {   # du phong (file danh dau chua dong bo ve may)
  foreach ($md in @('Drive của tôi', 'My Drive')) {
    $p = Join-Path $d.Root (Join-Path $md 'PHÒNG TRUYỀN THÔNG MICC')
    if (Test-Path -LiteralPath (Join-Path $p 'SETUP')) { $root = $p; break }
  }
  if ($root) { break }
} }
if (-not $root) { Log 'Chua thay Google Drive cua tai khoan MICC (PHÒNG TRUYỀN THÔNG MICC)'; exit }
Log ("o Drive cua tai khoan MICC tren may nay: " + $root)
# 1b) O M: = thu muc PHÒNG TRUYỀN THÔNG MICC tren MOI may (Drive o chu nao, ten "Drive của tôi" hay "My Drive" cung vay)
#     Project CapCut luon tro M:/... nen mo o may nao cung thay file. Tao ngay + tu tao lai moi lan dang nhap (HKCU Run).
function Map-M {
  $want = (Get-Item -LiteralPath $root).FullName.TrimEnd('\')
  $cur = (& subst.exe) | Where-Object { $_ -match '^M:\\: => (.+)$' } | ForEach-Object { $Matches[1].TrimEnd('\') }
  if ($cur -and $cur -ne $want) { & subst.exe M: /D | Out-Null; $cur = $null }
  if (-not $cur) {
    if (Test-Path -LiteralPath 'M:\') { Log 'CHU Y: o M dang dung cho viec khac (o that / o mang) - project khong tim thay file. Hay doi chu o do sang chu khac.'; return }
    & subst.exe M: $want | Out-Null; Log "subst M: -> $want"
  }
  try {
    $rk = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
    if (-not (Test-Path $rk)) { New-Item -Path $rk -Force | Out-Null }
    New-ItemProperty -Path $rk -Name 'MICC o M' -Value ('subst.exe M: "' + $want + '"') -PropertyType String -Force -ErrorAction Stop | Out-Null
  } catch { Log ('khong dat duoc tu gan o M khi dang nhap: ' + $_.Exception.Message) }
}
# (bo o M theo y chu: KHONG bat may phai co o M) - go o M cu neu chinh cong cu nay da tao, va bo tu gan khi dang nhap
try {
  $want = (Get-Item -LiteralPath $root).FullName.TrimEnd('\')
  $cur = (& subst.exe) | Where-Object { $_ -match '^M:\\: => (.+)$' } | ForEach-Object { $Matches[1].TrimEnd('\') }
  if ($cur -and $cur -eq $want) { & subst.exe M: /D | Out-Null; Log 'da go o M cu (khong can nua)' }
  Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'MICC o M' -ErrorAction SilentlyContinue
} catch {}
# moi project tro thang ve o Drive cua tai khoan MICC tren MAY NAY
$real = (Get-Item -LiteralPath $root).FullName.TrimEnd('\\')
$li = Get-Item -LiteralPath 'C:\Users\Public\MICC Drive' -Force -ErrorAction SilentlyContinue
if ($li -and $li.Target) { cmd /c rmdir "C:\Users\Public\MICC Drive" | Out-Null }   # bo loi tat thu nghiem cu (neu co)
$rootF = $real -replace '\\', '/'
$rxRoot = '"(?:M:|C:[/\\]+Users[/\\]+Public[/\\]+MICC Drive|[A-Za-z]:[/\\]+(?:Drive của tôi|My Drive)[/\\]+PHÒNG TRUYỀN THÔNG MICC)(?=[/\\])'   # duong dan cu (o bat ky / o M) -> duong dan chung
# cai font cua team (Nexa Rush, Bebas, Dancing Script...) vao may nay cho rieng nguoi dung -> CapCut luon dung dung font, khong bao gio ra font he thong
$fontsDone = $false
function Install-TeamFonts($dir) {
  if (-not (Test-Path -LiteralPath $dir)) { return }
  $fd = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Fonts'; New-Item -ItemType Directory -Force -Path $fd | Out-Null
  $rk = 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Fonts'; if (-not (Test-Path $rk)) { New-Item -Path $rk -Force | Out-Null }
  foreach ($f in (Get-ChildItem -LiteralPath $dir -File -ErrorAction SilentlyContinue | Where-Object { $_.Extension -match '^\.(ttf|otf)$' })) {
    $dst = Join-Path $fd $f.Name
    if (-not (Test-Path -LiteralPath $dst)) {
      try { Copy-Item -LiteralPath $f.FullName -Destination $dst -Force; New-ItemProperty -Path $rk -Name ($f.BaseName + ' (TrueType)') -Value $dst -PropertyType String -Force | Out-Null; Log "cai font $($f.Name)" }
      catch { Log ("khong cai duoc font " + $f.Name + ": " + $_.Exception.Message) }
    }
  }
}
Install-TeamFonts (Join-Path $root 'SETUP\Kho AI tải về\Font chữ')   # kho chung: font của team
# CHI XU LY 1 LAN moi khi file project thay doi (khong doc / ghi lai lien tuc -> khong ton han muc tai xuong cua Drive)
$stF = Join-Path $env:LOCALAPPDATA 'MICC\da-noi.txt'; $St = @{}
if (Test-Path -LiteralPath $stF) { foreach ($l in (Get-Content -LiteralPath $stF -Encoding UTF8)) { $i = $l.LastIndexOf('|'); if ($i -gt 0) { $St[$l.Substring(0, $i)] = $l.Substring($i + 1) } } }
function Sig($f) { $it = Get-Item -LiteralPath $f -ErrorAction SilentlyContinue; if ($it) { return "$($it.Length)-$($it.LastWriteTimeUtc.Ticks)" } else { return '' } }
function Seen($f) {
  if (-not $St.ContainsKey($f)) { return $false }
  $v = $St[$f]; $sg = Sig $f
  if ($v -eq $sg) { return $true }
  if ($v -like ($sg + '~*')) { return ([DateTime]::UtcNow.Ticks - [int64]($v.Split('~')[1])) -lt 18000000000 }   # con thieu file -> 30 phut thu lai 1 lan
  return $false
}
function Mark($f) { $St[$f] = Sig $f }
function Fix-Paths($dir) {
  foreach ($fn in @('draft_content.json', 'draft_info.json')) {
    $f = Join-Path $dir $fn
    if (-not (Test-Path -LiteralPath $f) -or (Seen $f)) { continue }
    try {
      $t = [IO.File]::ReadAllText($f, [Text.Encoding]::UTF8)
      $n = [regex]::Replace($t, $rxRoot.Normalize([Text.NormalizationForm]::FormC), ('"' + $rootF.Replace('$', '$$')))
      $n = [regex]::Replace($n, $rxRoot.Normalize([Text.NormalizationForm]::FormD), ('"' + $rootF.Replace('$', '$$')))
      if ($n.Normalize([Text.NormalizationForm]::FormC) -cne $t.Normalize([Text.NormalizationForm]::FormC)) { [IO.File]::WriteAllText($f, $n, (New-Object Text.UTF8Encoding($false))); Log "sua duong dan theo o Drive cua may nay: $(Split-Path $dir -Leaf)" }
    } catch { Log ("khong sua duoc duong dan " + $f + ": " + $_.Exception.Message) }
  }
}
$cache = Join-Path $root 'MICC media · Hệ thống (không xóa)\AI dựng CapCut'   # moi thu web / AI tu tao; SETUP chi cho nguoi dung
$list = Join-Path $cache 'Danh sách project CapCut.txt'
if (-not (Test-Path -LiteralPath $list)) { $list = Join-Path $root 'SETUP\CapCut projects.txt' }   # cho chuyen tiep
# tu cap nhat bo khoi dong: moi lan chay lay ban moi trong SETUP\Cài đặt đồng bộ CapCut.bat
try {
  $bootF = Join-Path $env:LOCALAPPDATA 'MICC\khoi-dong.ps1'
  $bootT = @'
$local = Join-Path $env:LOCALAPPDATA 'MICC\micc-capcut-sync.ps1'
$mk = '#' + '==== DONG BO ===='
foreach ($d in (Get-PSDrive -PSProvider FileSystem)) {
  foreach ($md in @('Drive của tôi', 'My Drive')) {
    $f = Join-Path $d.Root (Join-Path $md 'PHÒNG TRUYỀN THÔNG MICC\SETUP\Cài đặt đồng bộ CapCut.bat')
    if (Test-Path -LiteralPath $f) {
      try { $t = [IO.File]::ReadAllText($f, [Text.Encoding]::UTF8); $i = $t.IndexOf($mk); if ($i -ge 0) { [IO.File]::WriteAllText($local, $t.Substring($i), (New-Object Text.UTF8Encoding($true))) } } catch {}
      break
    }
  }
}
& $local
'@
  if ((Test-Path -LiteralPath $bootF) -and -not ((Get-Content -LiteralPath $bootF -Raw) -match 'CapCut\.bat')) { Set-Content -LiteralPath $bootF -Value $bootT -Encoding UTF8; Log 'da chuyen bo khoi dong sang SETUP\Cài đặt đồng bộ CapCut.bat' }
} catch {}
if (-not (Test-Path -LiteralPath $list)) { Log "Chua co $list"; exit }
# 2) thu muc ban nhap CapCut
$drafts = Join-Path $env:LOCALAPPDATA 'CapCut\User Data\Projects\com.lveditor.draft'
if (-not (Test-Path -LiteralPath $drafts)) { New-Item -ItemType Directory -Force -Path $drafts | Out-Null }
# tim thu muc theo duong dan tuong doi, khong phan biet cach ma hoa dau tieng Viet / hoa thuong;
# thu muc cuoi neu Drive tren may doi ten (vd them " (1)") thi lay ban moi nhat co draft_content.json
# tim FILE that tren may theo duong dan tuong doi, khong phan biet kieu ma hoa dau tieng Viet (NFC / NFD) va hoa thuong
$LooseCache = @{}
function Resolve-LooseFile($base, $rel) {
  $segs = @($rel -split '[\\/]' | Where-Object { $_ })
  if ($segs.Count -lt 1) { return $null }
  $dir = if ($segs.Count -gt 1) { Resolve-Loose $base (($segs[0..($segs.Count - 2)]) -join '/') } else { $base }
  if (-not $dir) { return $null }
  $want = $segs[-1].Normalize([Text.NormalizationForm]::FormC).Trim().ToLower()
  $hit = Get-ChildItem -LiteralPath $dir -File -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name.Normalize([Text.NormalizationForm]::FormC).Trim().ToLower() -eq $want } | Select-Object -First 1
  if ($hit) { return $hit.FullName } else { return $null }
}
# sua tung duong dan video / nhac / font trong project cho trung TEN THAT tren may nay (Drive o nao, dau kieu nao cung tim ra)
function Fix-Media($dir) {
  foreach ($fn in @('draft_content.json', 'draft_info.json')) {
    $f = Join-Path $dir $fn
    if (-not (Test-Path -LiteralPath $f) -or (Seen $f)) { continue }
    try {
      $t = [IO.File]::ReadAllText($f, [Text.Encoding]::UTF8); $n = $t; $fix = 0; $miss = 0
      $ps = [regex]::Matches($t, '"(?:path|font_path)":"([A-Za-z]:/[^"]+)"') | ForEach-Object { $_.Groups[1].Value } | Select-Object -Unique
      foreach ($p in $ps) {
        if (Test-Path -LiteralPath ($p -replace '/', '\')) { continue }
        if (-not $LooseCache.ContainsKey($p)) {
          $pc = $p.Normalize([Text.NormalizationForm]::FormC); $rc = $rootF.Normalize([Text.NormalizationForm]::FormC); $hit = $null
          if ($pc.StartsWith($rc, [StringComparison]::OrdinalIgnoreCase)) { $hit = Resolve-LooseFile $root ($pc.Substring($rc.Length).TrimStart('/')) }
          $LooseCache[$p] = if ($hit) { $rootF + (($hit.Substring($real.Length)) -replace '\\', '/') } else { '' }   # giu duong dan chung, chi sua phan ten that
        }
        if ($LooseCache[$p]) { $n = $n.Replace('"' + $p + '"', '"' + $LooseCache[$p] + '"'); $fix++ } else { $miss++ }
      }
      if ($n -cne $t) { [IO.File]::WriteAllText($f, $n, (New-Object Text.UTF8Encoding($false))); Log "noi lai $fix file trong $(Split-Path $dir -Leaf)" }
      if ($miss) { Log "con $miss file chua thay tren may (Drive chua dong bo xong?) trong $(Split-Path $dir -Leaf)" } else { Mark $f }
      if ($miss) { $St[$f] = (Sig $f) + '~' + [DateTime]::UtcNow.Ticks }   # thieu file -> lan sau thu lai; du roi -> khong dong toi nua cho den khi file doi
    } catch { Log ("khong noi lai duoc file " + $f + ": " + $_.Exception.Message) }
  }
}
function Resolve-Loose($base, $rel) {
  $cur = $base
  $segs = $rel -split '[\\/]' | Where-Object { $_ }
  for ($i = 0; $i -lt $segs.Count; $i++) {
    $want = $segs[$i].Normalize([Text.NormalizationForm]::FormC).Trim().ToLower()
    $kids = Get-ChildItem -LiteralPath $cur -Directory -Force -ErrorAction SilentlyContinue
    $hit = $kids | Where-Object { $_.Name.Normalize([Text.NormalizationForm]::FormC).Trim().ToLower() -eq $want } | Select-Object -First 1
    if (-not $hit -and $i -eq $segs.Count - 1) {
      $hit = $kids | Where-Object { $_.Name.Normalize([Text.NormalizationForm]::FormC).Trim().ToLower().StartsWith($want) -and (Test-Path -LiteralPath (Join-Path $_.FullName 'draft_content.json')) } |
             Sort-Object LastWriteTime -Descending | Select-Object -First 1
    }
    if (-not $hit) { return $null }
    $cur = $hit.FullName
  }
  return $cur
}
# 3) moi project: tao LOI TAT thu muc (junction) vao CapCut - khong chep video gi vao may.
#    Loi tat hong -> tu tao lai. KHONG BAO GIO chep project vao may (chu dan: moi chinh sua phai luu thang ve Drive).
$made = @()
foreach ($line in (Get-Content -LiteralPath $list -Encoding UTF8)) {
  $rel = $line.Trim(); if (-not $rel -or $rel.StartsWith('#')) { continue }
  $src = Resolve-Loose $root $rel
  if (-not $src -or -not (Test-Path -LiteralPath (Join-Path $src 'draft_content.json'))) {
    $par = Resolve-Loose $root (Split-Path ($rel -replace '/', '\') -Parent)
    $ds = if ($par) { (Get-ChildItem -LiteralPath $par -Force -ErrorAction SilentlyContinue | ForEach-Object { $_.Name }) -join ' | ' } else { '(khong thay thu muc cha)' }
    Log "chua thay tren Drive: $rel"
    # Drive tren may bi ket (thu muc project co ma thieu draft_content.json): khi CapCut tat -> khoi dong lai Google Drive (toi da 1 lan / 20 phut)
    $pf = Resolve-Loose $root $rel; if (-not $pf) { $pf = Join-Path $root ($rel -replace '/', '\') }
    $kf = Join-Path $env:LOCALAPPDATA 'MICC\drive-restart.txt'
    $last = 0; if (Test-Path -LiteralPath $kf) { $last = [double](Get-Content -LiteralPath $kf -Raw) }
    $nowS = [double][DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    if ((Test-Path -LiteralPath $pf) -and -not (Get-Process -Name 'CapCut' -ErrorAction SilentlyContinue) -and ($nowS - $last) -gt 1200) {
      Set-Content -LiteralPath $kf -Value $nowS
      $exe = (Get-Process -Name 'GoogleDriveFS' -ErrorAction SilentlyContinue | Select-Object -First 1).Path
      if (-not $exe) { $exe = Get-ChildItem 'C:\Program Files\Google\Drive File Stream' -Recurse -Filter 'GoogleDriveFS.exe' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName }
      Get-Process -Name 'GoogleDriveFS' -ErrorAction SilentlyContinue | Stop-Process -Force
      Start-Sleep -Seconds 3
      if ($exe) { Start-Process -FilePath $exe }
      Log "Drive bi ket o project $(Split-Path $rel -Leaf) -> da khoi dong lai Google Drive"
    }
    continue }
  $name = Split-Path $rel -Leaf
  Fix-Paths $src
  Fix-Media $src
  if (-not $fontsDone) { Install-TeamFonts (Join-Path $src 'AI tải về'); $fontsDone = $true }
  $dst = Join-Path $drafts $name
  $item = Get-Item -LiteralPath $dst -Force -ErrorAction SilentlyContinue
  $ok = $false
  if ($item) {
    $isLink = [bool]($item.Attributes -band [IO.FileAttributes]::ReparsePoint)
    try { $null = [IO.File]::ReadAllBytes((Join-Path $dst 'draft_meta_info.json')); $ok = $true } catch {}
    if (-not $ok -and $isLink) { cmd /c rmdir "$dst" | Out-Null; $item = $null; Log "loi tat hong -> tao lai $name" }
  }
  if (-not $item) {
    try { New-Item -ItemType Junction -Path $dst -Target $src -ErrorAction Stop | Out-Null; Log "loi tat $name" } catch {}
    try { $null = [IO.File]::ReadAllBytes((Join-Path $dst 'draft_meta_info.json')); $ok = $true } catch {}
    if (-not $ok) { Log "LOI: tao loi tat $name nhung khong doc duoc qua no (khong chep file, chi dung loi tat)" }
  }
  if ($ok) { $made += $name }
}

try { ($St.GetEnumerator() | ForEach-Object { $_.Key + '|' + $_.Value }) | Set-Content -LiteralPath $stF -Encoding UTF8 } catch {}
# 3b) Loi tat cu (project da doi ten / bo khoi danh sach) -> chi go LOI TAT (khong dung toi file tren Drive) va bo khoi danh sach CapCut
$want = @((Get-Content -LiteralPath $list -Encoding UTF8) | ForEach-Object { $_.Trim() } | Where-Object { $_ -and -not $_.StartsWith('#') } | ForEach-Object { Split-Path $_ -Leaf })
$gone = @()
# Thung rac cua CapCut: project MICC bi xoa trong CapCut -> chi bo LOI TAT / ban chep o may (Drive da tu khoi phuc), khong de nang may
$rb = Join-Path $drafts '.recycle_bin'
foreach ($d in (Get-ChildItem -LiteralPath $rb -Directory -Force -ErrorAction SilentlyContinue)) {
  if (-not ($want | Where-Object { $d.Name -like "*$_*" })) { continue }
  if ($d.Attributes -band [IO.FileAttributes]::ReparsePoint) { cmd /c rmdir "$($d.FullName)" | Out-Null }   # loi tat: chi go loi tat
  elseif (Get-ChildItem -LiteralPath $d.FullName -Recurse -Force -Attributes ReparsePoint -ErrorAction SilentlyContinue) { Log "bo qua (co loi tat ben trong): $($d.Name)"; continue }  # an toan: khong bao gio xoa xuyen qua loi tat
  else { Remove-Item -LiteralPath $d.FullName -Recurse -Force -ErrorAction SilentlyContinue }                # ban chep tren o C
  Log "don thung rac CapCut: $($d.Name)"
}
foreach ($d in (Get-ChildItem -LiteralPath $drafts -Directory -Force -ErrorAction SilentlyContinue)) {
  if (-not ($d.Attributes -band [IO.FileAttributes]::ReparsePoint)) { continue }
  $tg = (($d | Select-Object -ExpandProperty Target) -join '')
  if ($tg -notlike '*PHÒNG TRUYỀN THÔNG MICC*' -or $want -contains $d.Name) { continue }
  cmd /c rmdir "$($d.FullName)" | Out-Null; $gone += $d.Name; Log "go loi tat cu: $($d.Name)"
}

# 4) Ghi project vao danh sach cua CapCut (root_meta_info.json) - CapCut chi hien project co trong danh sach nay.
#    Chi ghi khi CapCut dang tat (CapCut ghi de file nay luc thoat).
$oldGone = @(); $gf = Join-Path $env:LOCALAPPDATA 'MICC\cho-xoa.txt'; if (Test-Path -LiteralPath $gf) { $oldGone = @(Get-Content -LiteralPath $gf -Encoding UTF8 | Where-Object { $_ }) }
$gone = @($gone + $oldGone | Sort-Object -Unique); if ($gone.Count -gt 0) { Set-Content -LiteralPath $gf -Value $gone -Encoding UTF8 }
if (($made.Count -gt 0 -or $gone.Count -gt 0) -and -not (Get-Process -Name 'CapCut' -ErrorAction SilentlyContinue)) {
  $rootMeta = Join-Path $drafts 'root_meta_info.json'
  $fw = ($drafts -replace '\\', '/')
  $data = $null
  if (Test-Path -LiteralPath $rootMeta) { try { $data = [IO.File]::ReadAllText($rootMeta) | ConvertFrom-Json } catch { Log "root_meta_info.json loi doc" } }
  if (-not $data) { $data = [pscustomobject]@{ all_draft_store = @(); draft_ids = 0; root_path = $fw } }
  $store = @($data.all_draft_store)
  $added = 0
  $n0 = $store.Count; $store = @($store | Where-Object { $gone -notcontains $_.draft_name }); if ($store.Count -ne $n0) { $added++; Log "bo $($n0 - $store.Count) project cu khoi danh sach CapCut" }
  Remove-Item -LiteralPath $gf -ErrorAction SilentlyContinue
  foreach ($name in $made) {
    $fold = "$fw/$name"
    if ($store | Where-Object { $_.draft_fold_path -eq $fold }) { continue }
    $mi = $null; try { $mi = [IO.File]::ReadAllText((Join-Path (Join-Path $drafts $name) 'draft_meta_info.json')) | ConvertFrom-Json } catch {}
    $now = [long](([DateTimeOffset]::UtcNow).ToUnixTimeMilliseconds() * 1000)
    $e = [ordered]@{
      draft_cloud_last_action_download = $false; draft_cloud_purchase_info = ''; draft_cloud_template_id = ''; draft_cloud_tutorial_info = ''
      draft_cloud_videocut_purchase_info = ''; draft_cover = "$fold/draft_cover.jpg"; draft_fold_path = $fold
      draft_id = $(if ($mi -and $mi.draft_id) { $mi.draft_id } else { [guid]::NewGuid().ToString().ToUpper() })
      draft_is_ai_shorts = $false; draft_is_invisible = $false; draft_json_file = "$fold/draft_content.json"; draft_name = $name
      draft_new_version = ''; draft_root_path = $fw; draft_timeline_materials_size = 0; draft_type = ''; tm_draft_cloud_completed = ''
      tm_draft_cloud_modified = 0; tm_draft_create = $now; tm_draft_modified = $now; tm_draft_removed = 0
      tm_duration = $(if ($mi -and $mi.tm_duration) { $mi.tm_duration } else { 0 })
    }
    $store = @([pscustomobject]$e) + $store; $added++
  }
  if ($added -gt 0) {
    if (Test-Path -LiteralPath $rootMeta) { Copy-Item -LiteralPath $rootMeta -Destination ($rootMeta + '.micc-backup') -Force }
    $data.all_draft_store = $store
    if ($data.PSObject.Properties.Name -contains 'draft_ids') { $data.draft_ids = $store.Count }
    [IO.File]::WriteAllText($rootMeta, ($data | ConvertTo-Json -Depth 20 -Compress), (New-Object Text.UTF8Encoding($false)))
    Log "da ghi $added project vao danh sach CapCut"
  }
}

# 5) Gui nhat ky + tinh trang len Drive de AI tu doc va sua (MICC media · Hệ thống (không xóa)\AI dựng CapCut\Nhật ký máy\<ten may>.txt)
try {
  $nk = Join-Path $cache 'Nhật ký máy'
  New-Item -ItemType Directory -Force -Path $nk | Out-Null
  $st = @("may: $env:COMPUTERNAME  nguoi dung: $env:USERNAME  luc: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')", "drive: $root", "drafts: $drafts",
          "capcut dang mo: $([bool](Get-Process -Name 'CapCut' -ErrorAction SilentlyContinue))", '--- thu muc drafts ---')
  foreach ($d in (Get-ChildItem -LiteralPath $drafts -Force -ErrorAction SilentlyContinue)) {
    $lk = if ($d.Attributes -band [IO.FileAttributes]::ReparsePoint) { 'LOITAT -> ' + (($d | Select-Object -ExpandProperty Target) -join ',') } else { '' }
    $st += ('{0}  {1}' -f $d.Name, $lk)
  }
  # kiem tra file video/nhac trong tung project co tim thay tren may khong
  foreach ($line in (Get-Content -LiteralPath $list -Encoding UTF8)) {
    $rel = $line.Trim(); if (-not $rel -or $rel.StartsWith('#')) { continue }
    $par = Resolve-Loose $root (Split-Path ($rel -replace '/', '\') -Parent)
    if ($par) { $st += "--- thu muc cha cua $(Split-Path $rel -Leaf) ---"; $st += ((Get-ChildItem -LiteralPath $par -Force -ErrorAction SilentlyContinue | ForEach-Object { $_.Name }) -join ' | ') }
    $dc = Join-Path (Join-Path $drafts (Split-Path $rel -Leaf)) 'draft_content.json'
    try {
      $raw = [IO.File]::ReadAllText($dc)
      $paths = [regex]::Matches($raw, '"path":\s*"([A-Za-z]:/[^"]+)"') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
      $miss = @($paths | Where-Object { -not (Test-Path -LiteralPath $_) })
      $st += "file trong project: $($paths.Count), thieu: $($miss.Count)"
      $st += ($miss | Select-Object -First 8)
    } catch { $st += "khong doc duoc $dc" }
  }
  # nhat ky loi cua CapCut (de biet vi sao mo project bi tat)
  try {
    $cl = Get-ChildItem -LiteralPath (Join-Path $env:LOCALAPPDATA 'CapCut\User Data\Log') -Recurse -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 2
    foreach ($f in $cl) {
      $st += "--- capcut log: $($f.Name) $($f.LastWriteTime) ---"
      $st += (Get-Content -LiteralPath $f.FullName -Tail 4000 -ErrorAction SilentlyContinue | Select-String -Pattern 'error|fail|crash|exception|invalid|Kich ban 2' | Select-Object -Last 40 | ForEach-Object { $_.Line.Substring(0, [Math]::Min(300, $_.Line.Length)) })
    }
  } catch {}
  $st += '--- nhat ky ---'
  $st += (Get-Content -LiteralPath $log -Tail 40 -ErrorAction SilentlyContinue)
  $rm = Join-Path $drafts 'root_meta_info.json'
  if (Test-Path -LiteralPath $rm) { $st += '--- root_meta_info (ten) ---'; try { $st += ((Get-Content -LiteralPath $rm -Raw | ConvertFrom-Json).all_draft_store | ForEach-Object { $_.draft_name + ' | ' + $_.draft_fold_path }) } catch { $st += 'doc loi' } }
  Set-Content -LiteralPath (Join-Path $nk ($env:COMPUTERNAME + '.txt')) -Value $st -Encoding UTF8
} catch {}
