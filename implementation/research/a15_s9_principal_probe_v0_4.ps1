$ErrorActionPreference = 'Stop'

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'S9 probe requires an elevated CI coordinator to provision disposable local users.'
}

$tag = 'A15S9' + [Guid]::NewGuid().ToString('N').Substring(0, 6).ToUpperInvariant()
$gateUser = $tag + 'G'
$custodianUser = $tag + 'C'
$passwordText = 'S9!' + [Guid]::NewGuid().ToString('N') + 'aA7'
$password = ConvertTo-SecureString $passwordText -AsPlainText -Force
$gateCredential = New-Object System.Management.Automation.PSCredential("$($env:COMPUTERNAME)\$gateUser", $password)
$custodianCredential = New-Object System.Management.Automation.PSCredential("$($env:COMPUTERNAME)\$custodianUser", $password)

$root = Join-Path $env:RUNNER_TEMP $tag
$protected = Join-Path $root 'protected'
$gateOut = Join-Path $root 'gate-output'
$recorder = Join-Path $protected 'recorder.ps1'
$ledger = Join-Path $protected 'ledger.jsonl'
$probe = Join-Path $root 'gate-probe.ps1'
$outFile = Join-Path $gateOut 'result.json'
$service = $null

try {
    New-LocalUser -Name $gateUser -Password $password -PasswordNeverExpires -UserMayNotChangePassword | Out-Null
    New-LocalUser -Name $custodianUser -Password $password -PasswordNeverExpires -UserMayNotChangePassword | Out-Null

    New-Item -ItemType Directory -Path $root -Force | Out-Null
    New-Item -ItemType Directory -Path $protected -Force | Out-Null
    New-Item -ItemType Directory -Path $gateOut -Force | Out-Null

    $gatePrincipal = "$($env:COMPUTERNAME)\$gateUser"
    $custodianPrincipal = "$($env:COMPUTERNAME)\$custodianUser"

    # Gate can read the probe and write only to its own result directory.
    & icacls.exe $root /grant ("{0}:(OI)(CI)(RX)" -f $gatePrincipal) ("{0}:(OI)(CI)(RX)" -f $custodianPrincipal) | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not grant Gate traversal/read access to test root.' }
    & icacls.exe $gateOut /inheritance:r /grant:r "NT AUTHORITY\SYSTEM:(OI)(CI)(F)" "BUILTIN\Administrators:(OI)(CI)(F)" ("{0}:(OI)(CI)(M)" -f $gatePrincipal) | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not isolate Gate output directory.' }

    # Protected service directory: Custodian may manage it; Gate receives read/execute only.
    & icacls.exe $protected /inheritance:r /grant:r "NT AUTHORITY\SYSTEM:(OI)(CI)(F)" "BUILTIN\Administrators:(OI)(CI)(F)" ("{0}:(OI)(CI)(F)" -f $custodianPrincipal) ("{0}:(OI)(CI)(RX)" -f $gatePrincipal) | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not apply protected service ACL.' }

    @'
'use strict'
# Fixed synthetic service-image marker; no production broker or authority.
'A15_CUSTODIAN_IMAGE_V04'
'@ | Set-Content -LiteralPath $recorder -Encoding UTF8
    '{"seq":1,"event":"GENESIS_SYNTHETIC"}' | Set-Content -LiteralPath $ledger -Encoding UTF8
    & icacls.exe $protected /setowner $custodianPrincipal /T /C | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not set Custodian as protected directory/file owner.' }
    & icacls.exe $ledger /inheritance:r /grant:r "NT AUTHORITY\SYSTEM:F" "BUILTIN\Administrators:F" ("{0}:F" -f $custodianPrincipal) | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not isolate the custodian ledger ACL.' }
    & icacls.exe $ledger /setowner $custodianPrincipal | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not set Custodian as ledger owner.' }

    $probeText = @'
param(
    [Parameter(Mandatory=$true)][string]$ProtectedFile,
    [Parameter(Mandatory=$true)][int]$ServicePid,
    [Parameter(Mandatory=$true)][string]$LedgerFile,
    [Parameter(Mandatory=$true)][string]$OutputFile
)
$ErrorActionPreference = 'Stop'
$readAllowed = $false
$writeDenied = $false
$deleteDenied = $false
$killDenied = $false
$ledgerReadDenied = $false
$ledgerWriteDenied = $false
try { Get-Content -LiteralPath $ProtectedFile -ErrorAction Stop | Out-Null; $readAllowed = $true } catch {}
try { Add-Content -LiteralPath $ProtectedFile -Value 'MALICIOUS_REPLACEMENT' -ErrorAction Stop } catch { $writeDenied = $true }
try { Remove-Item -LiteralPath $ProtectedFile -Force -ErrorAction Stop } catch { $deleteDenied = $true }
try { Get-Content -LiteralPath $LedgerFile -ErrorAction Stop | Out-Null } catch { $ledgerReadDenied = $true }
try { Add-Content -LiteralPath $LedgerFile -Value 'FORGED_LEDGER_ENTRY' -ErrorAction Stop } catch { $ledgerWriteDenied = $true }
try { Stop-Process -Id $ServicePid -Force -ErrorAction Stop } catch { $killDenied = $true }
[pscustomobject]@{
    ReadAllowed = $readAllowed
    WriteDenied = $writeDenied
    DeleteDenied = $deleteDenied
    KillDenied = $killDenied
    LedgerReadDenied = $ledgerReadDenied
    LedgerWriteDenied = $ledgerWriteDenied
} | ConvertTo-Json -Compress | Set-Content -LiteralPath $OutputFile -Encoding UTF8
if (-not ($readAllowed -and $writeDenied -and $deleteDenied -and $killDenied -and $ledgerReadDenied -and $ledgerWriteDenied)) { exit 9 }
exit 0
'@
    $probeText | Set-Content -LiteralPath $probe -Encoding UTF8

    $powerShell = Join-Path $PSHOME 'powershell.exe'
    $service = Start-Process -FilePath $powerShell -Credential $custodianCredential -ArgumentList '-NoProfile -NonInteractive -Command "Start-Sleep -Seconds 90"' -PassThru -WindowStyle Hidden
    Start-Sleep -Milliseconds 400
    if ($service.HasExited) { throw 'Custodian process exited before the Gate probe.' }

    $argumentLine = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $probe + '" -ProtectedFile "' + $recorder + '" -ServicePid ' + $service.Id + ' -LedgerFile "' + $ledger + '" -OutputFile "' + $outFile + '"'
    $gateProcess = Start-Process -FilePath $powerShell -Credential $gateCredential -ArgumentList $argumentLine -PassThru -Wait -WindowStyle Hidden

    if ($gateProcess.ExitCode -ne 0) { throw "Gate isolation probe failed with exit code $($gateProcess.ExitCode)." }
    if (-not (Test-Path -LiteralPath $outFile)) { throw 'Gate probe did not write its result.' }
    $result = Get-Content -LiteralPath $outFile -Raw | ConvertFrom-Json
    if (-not ($result.ReadAllowed -and $result.WriteDenied -and $result.DeleteDenied -and $result.KillDenied -and $result.LedgerReadDenied -and $result.LedgerWriteDenied)) {
        throw "Unexpected Gate access result: $($result | ConvertTo-Json -Compress)"
    }
    if (-not (Test-Path -LiteralPath $recorder)) { throw 'Gate removed the protected service image.' }
    if ((Get-Content -LiteralPath $recorder -Raw) -notmatch 'A15_CUSTODIAN_IMAGE_V04') { throw 'Protected service image content changed.' }
    if ($service.HasExited) { throw 'Gate terminated the Custodian process.' }

    Write-Output 'S9_OS_PRINCIPAL_BOUNDARY=PASS'
    Write-Output "GATE_IDENTITY=$gateUser"
    Write-Output "CUSTODIAN_IDENTITY=$custodianUser"
    Write-Output 'GATE_CAN_READ_EXECUTABLE=YES'
    Write-Output 'GATE_CAN_WRITE_OR_DELETE_EXECUTABLE=NO'
    Write-Output 'GATE_CAN_TERMINATE_CUSTODIAN_PROCESS=NO'
    Write-Output 'GATE_CAN_READ_OR_WRITE_LEDGER=NO'
    Write-Output 'SCOPE=LOCAL_OS_PRINCIPAL_ONLY_NOT_EXTERNAL_CUSTODY'
}
finally {
    if ($service -and -not $service.HasExited) { Stop-Process -Id $service.Id -Force -ErrorAction SilentlyContinue }
    if ($root -and (Test-Path -LiteralPath $root)) {
        & icacls.exe $root /reset /T /C | Out-Null
        Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (Get-LocalUser -Name $gateUser -ErrorAction SilentlyContinue) { Remove-LocalUser -Name $gateUser -ErrorAction SilentlyContinue }
    if (Get-LocalUser -Name $custodianUser -ErrorAction SilentlyContinue) { Remove-LocalUser -Name $custodianUser -ErrorAction SilentlyContinue }
}
