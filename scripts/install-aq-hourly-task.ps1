<#
.SYNOPSIS
Registers a Windows scheduled task that runs scripts/aq-hourly-local.py once an hour.

.DESCRIPTION
CPCB and data.gov.in refuse GitHub's hosted runners, so the hourly air-quality
fetch has to run from a computer in India. This registers that run as a task for
the current user. It runs only while that user is signed in (so git and gh can
use the credentials already stored for them), never starts a second copy while
one is still going, and catches up after the computer was off or asleep.

Run scripts/aq-hourly-local.py --clone <Clone> --dry-run once first: that creates
the clone this task runs from and shows the fetch working.

To remove the task:
    Unregister-ScheduledTask -TaskName "india-geodata air quality hourly" -Confirm:$false

.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts\install-aq-hourly-task.ps1
#>
param(
    [string]$Clone = (Join-Path $env:USERPROFILE "india-geodata-aq\repo"),
    [string]$Python = (Get-Command python -ErrorAction Stop).Source,
    [ValidateRange(0, 59)][int]$Minute = 35,
    [string]$TaskName = "india-geodata air quality hourly"
)
$ErrorActionPreference = "Stop"

$script = Join-Path $Clone "scripts\aq-hourly-local.py"
if (-not (Test-Path $script)) {
    throw "$script not found. Run 'python scripts\aq-hourly-local.py --clone `"$Clone`" --dry-run' first, once the script is on main."
}
# pythonw runs without a console window; fall back to python if it is missing
$pythonw = Join-Path (Split-Path $Python) "pythonw.exe"
if (-not (Test-Path $pythonw)) { $pythonw = $Python }
$log = Join-Path (Split-Path $Clone) "aq-hourly.log"

$action = New-ScheduledTaskAction -Execute $pythonw `
    -Argument "`"$script`" --clone `"$Clone`" --log `"$log`"" `
    -WorkingDirectory (Split-Path $Clone)
$now = Get-Date
$first = $now.Date.AddHours($now.Hour).AddMinutes($Minute)
if ($first -le $now) { $first = $first.AddHours(1) }
$trigger = New-ScheduledTaskTrigger -Once -At $first -RepetitionInterval (New-TimeSpan -Hours 1)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Principal $principal -Force `
    -Description "Fetches CPCB air quality every hour and publishes it to yashveeeeeeer/india-geodata. Log: $log" | Out-Null

$task = Get-ScheduledTask -TaskName $TaskName
Write-Output "Registered '$TaskName': first run $first, then every hour."
Write-Output "Runs: $pythonw $($action.Arguments)"
Write-Output "Log:  $log"
Write-Output "State: $($task.State)"
