# R63 G4: OS-peer SID named pipe actor, synthetic Windows CI only
param([Parameter(Mandatory)][ValidateSet('Server','Client','Direct')][string]$Role,
      [Parameter(Mandatory)][string]$PipeName,
      [Parameter(Mandatory)][string]$LabRoot,
      [Parameter(Mandatory)][string]$Python,
      [Parameter(Mandatory)][string]$WriterSid,
      [Parameter(Mandatory)][string]$ReaderSid,
      [string]$ExpectedSid='',
      [string]$Nonce='',[string]$Identifier='',[string]$Claim='',
      [string]$LogPath='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {throw 'WINDOWS_ONLY'}
if (-not $PipeName.StartsWith('ArioR63G4_')) {throw 'WRONG_PIPE_PREFIX'}
if ((Split-Path -Leaf $LabRoot) -ne 'journal' -or
    -not $LabRoot.Contains('ArioR63G4_')) {throw 'REFUSE_NON_DISPOSABLE_JOURNAL'}
$current=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
if ($Role -eq 'Direct') {
    if ($current -ne $ExpectedSid) {throw 'DIRECT_PROBE_TOKEN_MISMATCH'}
    $results=[ordered]@{sid=$current;results=[ordered]@{}}
    foreach ($name in @('v1.jsonl','v2.jsonl')) {
        $path=Join-Path $LabRoot $name
        $results.results['read_'+$name]=([IO.File]::ReadAllBytes($path)).Length
        try {
            [IO.File]::AppendAllText($path,"UNAUTHORIZED_G4"+[char]10)
            $results.results['append_'+$name]='ALLOWED_DANGEROUS'
        } catch {
            $exc=$_.Exception;$denied=$false
            while ($null -ne $exc) {
                if ($exc -is [UnauthorizedAccessException] -or $exc.HResult -eq -2147024891) {
                    $denied=$true;break
                }
                $exc=$exc.InnerException
            }
            if (-not $denied){throw ('INCONCLUSIVE_ERROR_'+$name+'_'+$_.Exception.Message)}
            $results.results['append_'+$name]='ACCESS_DENIED'
        }
    }
    $results | ConvertTo-Json -Depth 5 -Compress
    exit 0
}
Add-Type -Path (Join-Path (Split-Path -Parent $LabRoot) 'G4PipeGate.dll') -ErrorAction Stop
if ($Role -eq 'Server') {
    if ($current -ne $WriterSid) {throw 'SERVER_NON_WRITER_SID'}
    if (-not $LogPath) {throw 'MISSING_LOG_PATH'}
    $result=[G4PipeGate]::Serve($PipeName,$ReaderSid,$WriterSid,$Python,
       (Join-Path $PSScriptRoot 'g4_journal.py'),$LabRoot,4,$LogPath)
    Write-Output ($current+'|'+$result)
} else {
    if ($current -ne $ExpectedSid) {throw 'CLIENT_TOKEN_MISMATCH'}
    $response=[G4PipeGate]::Request($PipeName,$Nonce,$Identifier,$Claim,$ExpectedSid)
    Write-Output ($current+'|'+$response)
}
