# A run's memory footprint (333-10, Evan's row 106; for loop.py's FOOTPRINT_GB): every -Interval seconds for -Seconds, the summed
# working set and private bytes of the process tree under -RootPid (the run's chain shell, its trainer and its Node workers),
# plus the machine's free RAM; prints each sample and the peaks. Read-only.
#   powershell -NoProfile -File notes/scripts/mem_tree.ps1 -RootPid 1234 -Seconds 300 -Interval 5
param([int]$RootPid, [int]$Seconds = 300, [int]$Interval = 5)
$peakWs = 0; $peakPriv = 0; $minFree = 1e9; $t0 = Get-Date
while (((Get-Date) - $t0).TotalSeconds -lt $Seconds) {
  $all = Get-CimInstance Win32_Process
  $tree = @($all | Where-Object { $_.ProcessId -eq $RootPid })
  if ($tree.Count -eq 0) { "root $RootPid gone"; break }
  $frontier = @($RootPid)
  while ($frontier.Count -gt 0) {
    $kids = @($all | Where-Object { $frontier -contains $_.ParentProcessId })
    $tree += $kids; $frontier = @($kids | ForEach-Object { $_.ProcessId })
  }
  $ws = ($tree | Measure-Object -Property WorkingSetSize -Sum).Sum / 1GB
  $priv = ($tree | Measure-Object -Property PrivatePageCount -Sum).Sum / 1GB
  $free = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB
  if ($ws -gt $peakWs) { $peakWs = $ws }; if ($priv -gt $peakPriv) { $peakPriv = $priv }; if ($free -lt $minFree) { $minFree = $free }
  "{0:HH:mm:ss} procs {1} ws {2:N2} GB private {3:N2} GB free {4:N2} GB" -f (Get-Date), $tree.Count, $ws, $priv, $free
  Start-Sleep -Seconds $Interval
}
"PEAK ws {0:N2} GB private {1:N2} GB; min free {2:N2} GB" -f $peakWs, $peakPriv, $minFree
