# R63 G8 disposable Windows test actor; no real keys or production state.
param([Parameter(Mandatory=$true)][ValidateSet('Fixture','Server','Client','Cleanup','Verify')][string]$Role,
      [Parameter(Mandatory=$true)][string]$Root,
      [string]$Case='', [string]$Pipe='', [string]$WriterSid='', [string]$ReaderSid='',
      [string]$ExpectedSid='', [string]$Phase='normal', [int]$Count=1)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or
    $env:RUNNER_OS -ne 'Windows' -or $env:GITHUB_REPOSITORY -ne 'SepehrGhanbari/Ario' -or
    $env:GITHUB_ACTIONS -ne 'true') {throw 'G8_REFUSE_NON_DISPOSABLE_WINDOWS_ACTIONS'}
if ((Split-Path -Leaf $Root) -notmatch '^ArioR63G8_[a-f0-9]{8}$' -or -not [IO.Directory]::Exists($Root)) { throw 'G8_REFUSE_WRONG_ROOT' }
$actual=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
Add-Type -Path (Join-Path $Root 'G8IntegratedBroker.dll') -ErrorAction Stop
switch ($Role) {
    'Fixture' {Write-Output ([G8IntegratedBroker]::Fixture($Root))}
    'Server' {
      if ($actual -cne $WriterSid) {throw 'G8_WRITER_OS_TOKEN_MISMATCH'}
      Write-Output ([G8IntegratedBroker]::Serve($Root,$Case,$Pipe,$WriterSid,$ReaderSid,$Count,$Phase))
    }
    'Client' {
      if ($actual -cne $ExpectedSid) {throw 'G8_CLIENT_OS_TOKEN_MISMATCH'}
      Write-Output ([G8IntegratedBroker]::Client($Pipe,(Join-Path (Join-Path $Root $Case) 'request.txt'),$ExpectedSid))
    }
    'Cleanup' {
      if ($actual -cne $WriterSid) {throw 'G8_CLEANUP_WRITER_TOKEN_MISMATCH'}
      Write-Output ([G8IntegratedBroker]::Cleanup($Root))
    }
    'Verify' { Write-Output ([G8IntegratedBroker]::PublicAudit((Join-Path $Root $Case),$Root)) }
}
