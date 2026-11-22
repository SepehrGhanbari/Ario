$ErrorActionPreference = 'Stop'

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'S9 probe requires an elevated CI coordinator to provision disposable local users.'
}

$tag = 'A15S9' + [Guid]::NewGuid().ToString('N').Substring(0, 6).ToUpperInvariant()
$gateUser = $tag + 'G'
$custodianUser = $tag + 'C'
$gatePassword = ConvertTo-SecureString ('G!' + [Guid]::NewGuid().ToString('N') + 'aA7') -AsPlainText -Force
$custodianPassword = ConvertTo-SecureString ('C!' + [Guid]::NewGuid().ToString('N') + 'bB8') -AsPlainText -Force
$gateCredential = New-Object System.Management.Automation.PSCredential("$($env:COMPUTERNAME)\$gateUser", $gatePassword)
$custodianCredential = New-Object System.Management.Automation.PSCredential("$($env:COMPUTERNAME)\$custodianUser", $custodianPassword)

$root = Join-Path $env:RUNNER_TEMP $tag
$protected = Join-Path $root 'protected'
$gateOut = Join-Path $root 'gate-output'
$recorder = Join-Path $protected 'recorder.ps1'
$ledger = Join-Path $protected 'ledger.jsonl'
$probe = Join-Path $root 'gate-probe.ps1'
$custodianProbe = Join-Path $root 'custodian-probe.ps1'
$outFile = Join-Path $gateOut 'result.json'
$service = $null
$createdGateUser = $false
$createdCustodianUser = $false
$createdRoot = $false

try {
    if (Get-LocalUser -Name $gateUser -ErrorAction SilentlyContinue) { throw 'Refusing to reuse pre-existing Gate account.' }
    if (Get-LocalUser -Name $custodianUser -ErrorAction SilentlyContinue) { throw 'Refusing to reuse pre-existing Custodian account.' }
    if (Test-Path -LiteralPath $root) { throw 'Refusing to reuse pre-existing probe directory.' }

    New-LocalUser -Name $gateUser -Password $gatePassword -PasswordNeverExpires -UserMayNotChangePassword | Out-Null
    $createdGateUser = $true
    New-LocalUser -Name $custodianUser -Password $custodianPassword -PasswordNeverExpires -UserMayNotChangePassword | Out-Null
    $createdCustodianUser = $true

    New-Item -ItemType Directory -Path $root -ErrorAction Stop | Out-Null
    $createdRoot = $true
    New-Item -ItemType Directory -Path $protected -Force | Out-Null
    New-Item -ItemType Directory -Path $gateOut -Force | Out-Null

    $gatePrincipal = "$($env:COMPUTERNAME)\$gateUser"
    $custodianPrincipal = "$($env:COMPUTERNAME)\$custodianUser"
    $gateSid = (Get-LocalUser -Name $gateUser).SID.Value
    $custodianSid = (Get-LocalUser -Name $custodianUser).SID.Value

    # Both identities may traverse the test root; Gate can write only to its result directory.
    & icacls.exe $root /grant ("{0}:(OI)(CI)(RX)" -f $gatePrincipal) ("{0}:(OI)(CI)(RX)" -f $custodianPrincipal) | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not grant Gate/Custodian traversal access to test root.' }
    & icacls.exe $gateOut /inheritance:r /grant:r "NT AUTHORITY\SYSTEM:(OI)(CI)(F)" "BUILTIN\Administrators:(OI)(CI)(F)" ("{0}:(OI)(CI)(M)" -f $gatePrincipal) | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not isolate Gate output directory.' }

    # Protected service directory: Custodian FullControl; Gate read/execute only.
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
    [Parameter(Mandatory=$true)][string]$OutputFile,
    [Parameter(Mandatory=$true)][string]$ExpectedGateSid,
    [Parameter(Mandatory=$true)][string]$CustodianSid
)
$ErrorActionPreference = 'Stop'
function Assert-AccessDenied {
    param([scriptblock]$Action, [string]$Label)
    try {
        & $Action
        throw "S9_ASSERT_SUCCEEDED:$Label"
    } catch {
        if ($_.Exception.Message -like 'S9_ASSERT_SUCCEEDED:*') { throw }
        $exception = $_.Exception
        while ($null -ne $exception) {
            if ($exception -is [System.UnauthorizedAccessException]) { return $true }
            if ($exception -is [System.ComponentModel.Win32Exception] -and $exception.NativeErrorCode -eq 5) { return $true }
            $exception = $exception.InnerException
        }
        throw "S9_EXPECTED_ACCESS_DENIED_BUT_GOT:$($Label):$($_.Exception.GetType().FullName):$($_.Exception.Message)"
    }
}
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$gatePrincipal = New-Object Security.Principal.WindowsPrincipal($identity)
if ($identity.User.Value -ne $ExpectedGateSid) { throw 'Gate probe ran under the wrong Windows SID.' }
if ($gatePrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Gate probe unexpectedly has Administrator membership.' }
if (@($identity.Groups | ForEach-Object { $_.Value }) -contains $CustodianSid) { throw 'Gate probe inherited Custodian SID membership.' }

$readAllowed = $false
$executeAllowed = $false
try {
    if ((Get-Content -LiteralPath $ProtectedFile -Raw -ErrorAction Stop) -match 'A15_CUSTODIAN_IMAGE_V04') { $readAllowed = $true }
} catch { throw "Gate could not read protected image: $($_.Exception.Message)" }

$powerShell = Join-Path $PSHOME 'pwsh.exe'
$executeOutput = & $powerShell -NoProfile -NonInteractive -File $ProtectedFile 2>&1
if ($LASTEXITCODE -eq 0 -and ($executeOutput -join [Environment]::NewLine) -match 'A15_CUSTODIAN_IMAGE_V04') { $executeAllowed = $true } else { throw 'Gate could not execute the read-only service image.' }
$writeDenied = Assert-AccessDenied { Add-Content -LiteralPath $ProtectedFile -Value 'MALICIOUS_REPLACEMENT' -ErrorAction Stop } 'executable-write'
$deleteDenied = Assert-AccessDenied { Remove-Item -LiteralPath $ProtectedFile -Force -ErrorAction Stop } 'executable-delete'
$acl = Get-Acl -LiteralPath $ProtectedFile -ErrorAction Stop
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule($identity.User, [System.Security.AccessControl.FileSystemRights]::FullControl, [System.Security.AccessControl.AccessControlType]::Allow)
$acl.SetAccessRule($rule)
$aclChangeDenied = Assert-AccessDenied { Set-Acl -LiteralPath $ProtectedFile -AclObject $acl -ErrorAction Stop } 'executable-acl-change'
$ledgerReadDenied = Assert-AccessDenied { Get-Content -LiteralPath $LedgerFile -Raw -ErrorAction Stop | Out-Null } 'ledger-read'
$ledgerWriteDenied = Assert-AccessDenied { Add-Content -LiteralPath $LedgerFile -Value 'FORGED_LEDGER_ENTRY' -ErrorAction Stop } 'ledger-write'
$killDenied = Assert-AccessDenied { Stop-Process -Id $ServicePid -Force -ErrorAction Stop } 'custodian-process-terminate'

[pscustomobject]@{
    GateSid = $identity.User.Value
    GateIsAdministrator = $gatePrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    GateHasCustodianSid = @($identity.Groups | ForEach-Object { $_.Value }) -contains $CustodianSid
    ReadAllowed = $readAllowed
    ExecuteAllowed = $executeAllowed
    WriteDenied = $writeDenied
    DeleteDenied = $deleteDenied
    AclChangeDenied = $aclChangeDenied
    LedgerReadDenied = $ledgerReadDenied
    LedgerWriteDenied = $ledgerWriteDenied
    KillDenied = $killDenied
} | ConvertTo-Json -Compress | Set-Content -LiteralPath $OutputFile -Encoding UTF8
'@
    $probeText | Set-Content -LiteralPath $probe -Encoding UTF8

    $custodianProbeText = @'
param(
    [Parameter(Mandatory=$true)][string]$LedgerFile,
    [Parameter(Mandatory=$true)][string]$ProtectedFile,
    [Parameter(Mandatory=$true)][string]$ExpectedCustodianSid
)
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if ($identity.User.Value -ne $ExpectedCustodianSid) { throw 'Custodian positive control ran under the wrong SID.' }
if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Custodian test identity unexpectedly has Administrator membership.' }
if ((Get-Content -LiteralPath $ProtectedFile -Raw -ErrorAction Stop) -notmatch 'A15_CUSTODIAN_IMAGE_V04') { throw 'Custodian could not read its installed image.' }
Add-Content -LiteralPath $LedgerFile -Value 'CUSTODIAN_WRITE' -ErrorAction Stop
'@
    $custodianProbeText | Set-Content -LiteralPath $custodianProbe -Encoding UTF8

    $powerShell = Join-Path $PSHOME 'pwsh.exe'
    $service = Start-Process -FilePath $powerShell -Credential $custodianCredential -ArgumentList '-NoProfile -NonInteractive -Command "Start-Sleep -Seconds 90"' -PassThru -WindowStyle Hidden
    Start-Sleep -Milliseconds 400
    if ($service.HasExited) { throw 'Custodian process exited before the Gate probe.' }

    $processInfo = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $($service.Id)"
    $ownerInfo = Invoke-CimMethod -InputObject $processInfo -MethodName GetOwner
    if ($ownerInfo.ReturnValue -ne 0 -or $ownerInfo.User -ne $custodianUser -or $ownerInfo.Domain -ne $env:COMPUTERNAME) {
        throw "Custodian process identity mismatch: $($ownerInfo.Domain)\$($ownerInfo.User)"
    }

    $argumentLine = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $probe + '" -ProtectedFile "' + $recorder + '" -ServicePid ' + $service.Id + ' -LedgerFile "' + $ledger + '" -OutputFile "' + $outFile + '" -ExpectedGateSid "' + $gateSid + '" -CustodianSid "' + $custodianSid + '"'
    $gateProcess = Start-Process -FilePath $powerShell -Credential $gateCredential -ArgumentList $argumentLine -PassThru -Wait -WindowStyle Hidden

    if (-not (Test-Path -LiteralPath $outFile)) { throw "Gate probe did not write its result (exit code $($gateProcess.ExitCode))." }
    $result = Get-Content -LiteralPath $outFile -Raw | ConvertFrom-Json
    if ($gateProcess.ExitCode -ne 0 -or -not ($result.GateSid -eq $gateSid -and -not $result.GateIsAdministrator -and -not $result.GateHasCustodianSid -and $result.ReadAllowed -and $result.ExecuteAllowed -and $result.WriteDenied -and $result.DeleteDenied -and $result.AclChangeDenied -and $result.LedgerReadDenied -and $result.LedgerWriteDenied -and $result.KillDenied)) {
        throw "Gate isolation probe failed with exit code $($gateProcess.ExitCode); observed result: $($result | ConvertTo-Json -Compress)"
    }

    $custodianArgs = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $custodianProbe + '" -LedgerFile "' + $ledger + '" -ProtectedFile "' + $recorder + '" -ExpectedCustodianSid "' + $custodianSid + '"'
    $custodianWrite = Start-Process -FilePath $powerShell -Credential $custodianCredential -ArgumentList $custodianArgs -PassThru -Wait -WindowStyle Hidden
    if ($custodianWrite.ExitCode -ne 0) { throw "Custodian positive control failed with exit code $($custodianWrite.ExitCode)." }
    if ((Get-Content -LiteralPath $ledger -Raw) -notmatch 'CUSTODIAN_WRITE') { throw 'Custodian positive control did not persist its ledger entry.' }

    if (-not (Test-Path -LiteralPath $recorder)) { throw 'Gate removed the protected service image.' }
    if ((Get-Content -LiteralPath $recorder -Raw) -notmatch 'A15_CUSTODIAN_IMAGE_V04') { throw 'Protected service image content changed.' }
    if ($service.HasExited) { throw 'Gate terminated the Custodian process.' }

    Write-Output 'S9_OS_PRINCIPAL_BOUNDARY=PASS'
    Write-Output "GATE_IDENTITY=$gateUser"
    Write-Output "CUSTODIAN_IDENTITY=$custodianUser"
    Write-Output 'GATE_IS_NONADMIN=YES'
    Write-Output 'CUSTODIAN_IS_NONADMIN=YES'
    Write-Output 'GATE_CAN_READ_AND_EXECUTE_READONLY_IMAGE=YES'
    Write-Output 'GATE_CAN_WRITE_DELETE_OR_CHANGE_ACL=NO'
    Write-Output 'GATE_CAN_READ_OR_WRITE_LEDGER=NO'
    Write-Output 'GATE_CAN_TERMINATE_CUSTODIAN_PROCESS=NO'
    Write-Output 'CUSTODIAN_POSITIVE_CONTROL=PASS'
    Write-Output 'SCOPE=LOCAL_OS_PRINCIPAL_ONLY_NOT_EXTERNAL_CUSTODY'
}
finally {
    if ($service -and -not $service.HasExited) { Stop-Process -Id $service.Id -Force -ErrorAction SilentlyContinue }
    if ($createdRoot -and $root -and (Test-Path -LiteralPath $root)) {
        & icacls.exe $root /reset /T /C | Out-Null
        Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
    }
    if ($createdGateUser) { Remove-LocalUser -Name $gateUser -ErrorAction SilentlyContinue }
    if ($createdCustodianUser) { Remove-LocalUser -Name $custodianUser -ErrorAction SilentlyContinue }
}
