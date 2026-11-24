# R63 G8 disposable Windows test actor; no real keys or production state.
param([Parameter(Mandatory=$true)][ValidateSet('Fixture','Server','Client','Cleanup','Verify','Custodian','Probe')][string]$Role,
      [Parameter(Mandatory=$true)][string]$Root,
      [string]$Case='', [string]$Pipe='', [string]$WriterSid='', [string]$ReaderSid='',
      [string]$ExpectedSid='', [string]$Phase='normal', [int]$Count=1,
      [string]$CustodyPipe='', [string]$CustodyDir='', [string]$CustodianSid='', [string]$BrokerSid='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or
    $env:RUNNER_OS -ne 'Windows' -or $env:GITHUB_REPOSITORY -ne 'SepehrGhanbari/Ario' -or
    $env:GITHUB_ACTIONS -ne 'true') {throw 'G9_REFUSE_NON_DISPOSABLE_WINDOWS_ACTIONS'}
if ((Split-Path -Leaf $Root) -notmatch '^ArioR63G9_[a-f0-9]{8}$' -or -not [IO.Directory]::Exists($Root)) { throw 'G9_REFUSE_WRONG_ROOT' }
$actual=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
Add-Type -Path (Join-Path $Root 'G9IntegratedBroker.dll') -ErrorAction Stop
switch ($Role) {
    'Fixture' {Write-Output ([G9IntegratedBroker]::Fixture($Root))}
    'Server' {
      if ($actual -cne $WriterSid) {throw 'G9_WRITER_OS_TOKEN_MISMATCH'}
      Write-Output ([G9IntegratedBroker]::Serve($Root,$Case,$Pipe,$WriterSid,$ReaderSid,$Count,$Phase,$CustodyPipe))
    }
    'Client' {
      if ($actual -cne $ExpectedSid) {throw 'G9_CLIENT_OS_TOKEN_MISMATCH'}
      Write-Output ([G9IntegratedBroker]::Client($Pipe,(Join-Path (Join-Path $Root $Case) 'request.txt'),$ExpectedSid))
    }
    'Custodian' {
       if ($actual -cne $CustodianSid) {throw 'G9_CUSTODIAN_SID_INVALID'}
       Write-Output ([G9ExternalSyntheticCustodian]::Serve($CustodyPipe,$CustodyDir,$CustodianSid,$BrokerSid,$Count))
    }
    'Probe' {
       if ($actual -cne $WriterSid) {throw 'G9_WRITER_FOR_PROBE_REQUIRED'}
       try {
          $f=[IO.FileStream]::new((Join-Path $CustodyDir 'WRITER_UNAUTHORIZED.used'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
          $f.Dispose()
          Write-Output 'UNSAFE_WRITER_CAN_MODIFY_CUSTODY'
       } catch [UnauthorizedAccessException] {Write-Output 'G9_WRITER_CUSTODY_WRITE_ACCESS_DENIED'}
    }
    'Cleanup' {
      if ($actual -cne $WriterSid) {throw 'G9_CLEANUP_WRITER_TOKEN_MISMATCH'}
      Write-Output ([G9IntegratedBroker]::Cleanup($Root))
    }
    'Verify' { Write-Output ([G9IntegratedBroker]::PublicAudit((Join-Path $Root $Case),$Root)) }
}
