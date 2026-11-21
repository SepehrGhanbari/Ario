# R63 G4, ephemeral Windows Actions only; no production or native V9 signer.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or
    $env:RUNNER_OS -ne 'Windows' -or $env:GITHUB_ACTIONS -ne 'true' -or
    $env:GITHUB_REPOSITORY -ne 'SepehrGhanbari/Ario') {
    throw 'REFUSE_OUTSIDE_GITHUB_WINDOWS_CI'
}
$current=[Security.Principal.WindowsIdentity]::GetCurrent()
if (-not [Security.Principal.WindowsPrincipal]::new($current).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'HOLD_EPHEMERAL_LOCAL_USER_CREATION_REQUIRES_ELEVATION'
}
$short=[Guid]::NewGuid().ToString('N').Substring(0,8)
$names=@(('R63G4W'+$short),('R63G4R'+$short),('R63G4X'+$short))
$root=Join-Path $env:PUBLIC ('ArioR63G4_'+$short)
$journal=Join-Path $root 'journal'
$pipeName='ArioR63G4_'+$short
$psExe=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$actor=Join-Path $PSScriptRoot 'Invoke-G4PipeActor.ps1'
$journalPy=Join-Path $PSScriptRoot 'g4_journal.py'
$python=(Get-Command python -ErrorAction Stop).Source
$report=Join-Path $env:GITHUB_WORKSPACE 'r63-g4-peer-report.json'
$created=@();$children=@()
$observations=[ordered]@{experiment='R63_G4_WINDOWS_NAMED_PIPE_ACTUAL_PEER_TOKEN';
  scope='EPHEMERAL_CI_ONLY';source='RESEARCH_ONLY';result='HOLD';
  real_v9='NOT_EXECUTED';signer='NOT_EXECUTED';external_custody='NOT_ESTABLISHED'}
function Need([bool]$ok,[string]$msg){if(-not $ok){throw $msg}}
function Cred([string]$name){
    $rng=[Security.Cryptography.RandomNumberGenerator]::Create()
    $bytes=New-Object byte[] 48
    try{$rng.GetBytes($bytes)}finally{$rng.Dispose()}
    return [PSCredential]::new(('.\'+$name),(ConvertTo-SecureString -String ([Convert]::ToBase64String($bytes)) -AsPlainText -Force))
}
function NativeOk([string]$msg){if($LASTEXITCODE -ne 0){throw ('WINDOWS_API_FAILED_'+$msg+'_'+$LASTEXITCODE)}}
function StartActor($credential,[string]$tag,[string]$mode,[string]$expected,[string]$nonce,[string]$ident,[string]$claim,[string]$logfile){
    $out=Join-Path $env:RUNNER_TEMP ('G4-'+$short+'-'+$tag+'.out')
    $err=Join-Path $env:RUNNER_TEMP ('G4-'+$short+'-'+$tag+'.err')
    $a=@('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',('"'+$actor+'"'),'-Role',$mode,
      '-PipeName',$pipeName,'-LabRoot',('"'+$journal+'"'),'-Python',('"'+$python+'"'),'-WriterSid',$writerSid,'-ReaderSid',$readerSid)
    if ($expected){$a+=@('-ExpectedSid',$expected)}
    if ($nonce){$a+=@('-Nonce',$nonce)}
    if ($ident){$a+=@('-Identifier',$ident)}
    if ($claim){$a+=@('-Claim',$claim)}
    if ($logfile){$a+=@('-LogPath',('"'+$logfile+'"'))}
    $params=@{FilePath=$psExe;ArgumentList=($a -join ' ');PassThru=$true;
      WindowStyle='Hidden';RedirectStandardOutput=$out;RedirectStandardError=$err}
    if ($null -ne $credential){$params['Credential']=$credential}
    $p=Start-Process @params
    $handle=$p.Handle
    if ($null -eq $handle -or $handle -eq [IntPtr]::Zero){throw 'MISSING_PROCESS_HANDLE'}
    $child=[pscustomobject]@{tag=$tag;process=$p;stdout=$out;stderr=$err}
    $script:children+=,$child
    return $child
}
function WaitActor($child){
    if(-not $child.process.WaitForExit(50000)) {
        try{$child.process.Kill()}catch{}
        throw ('CHILD_TIMEOUT_'+$child.tag)
    }
    if ($null -eq $child.process.ExitCode -or $child.process.ExitCode -ne 0){
        $errorText=if(Test-Path $child.stderr){Get-Content $child.stderr -Raw}else{''}
        throw ('CHILD_FAILED_'+$child.tag+'_CODE_'+$child.process.ExitCode+'_'+$errorText)
    }
    return (Get-Content $child.stdout -Raw).Trim()
}
try {
    Need (-not (Test-Path $root)) 'REFUSE_EXISTING_LAB_DIR'
    Need (-not (Test-Path $report)) 'REFUSE_EXISTING_REPORT'
    $creds=@()
    foreach($n in $names){
        $c=Cred $n;$creds+=,$c
        New-LocalUser -Name $n -Password $c.Password -AccountNeverExpires -PasswordNeverExpires -Description 'R63 G4 disposable named pipe peer test' | Out-Null
        $created+=,$n
    }
    $writerSid=(Get-LocalUser -Name $names[0]).SID.Value
    $readerSid=(Get-LocalUser -Name $names[1]).SID.Value
    $rogueSid=(Get-LocalUser -Name $names[2]).SID.Value
    Need ($writerSid -ne $readerSid -and $readerSid -ne $rogueSid -and $writerSid -ne $rogueSid) 'SIDS_NOT_DISTINCT'
    $observations['writer_sid']=$writerSid
    $observations['allowed_peer_sid']=$readerSid
    $observations['rogue_peer_sid']=$rogueSid
    [IO.Directory]::CreateDirectory($root)|Out-Null
    & icacls.exe $root /inheritance:r | Out-Null;NativeOk 'REMOVE_INHERITANCE'
    $grants=@('*S-1-5-18:(OI)(CI)F','*S-1-5-32-544:(OI)(CI)F',
      ('*'+$writerSid+':(OI)(CI)M'),('*'+$readerSid+':(OI)(CI)RX'),('*'+$rogueSid+':(OI)(CI)RX'))
    & icacls.exe $root /grant:r $grants | Out-Null;NativeOk 'EXPLICIT_G4_DACL'
    $baseline=& $python -I -B $journalPy --prepare $journal
    Need ($LASTEXITCODE -eq 0) 'JOURNAL_PREPARE_FAILURE'
    $observations['baseline']=(ConvertFrom-Json -InputObject ($baseline|Out-String))
    Need ($observations['baseline'].v2_events -eq 2 -and $observations['baseline'].coherent) 'BASE_NOT_CANONICAL'
    $logFile=Join-Path $journal 'server-peer-log.txt'
    $serv=StartActor $creds[0] 'server' 'Server' '' '' '' '' $logFile
    Start-Sleep -Seconds 2
    Need (-not $serv.process.HasExited) 'SERVER_EXITED_BEFORE_FIRST_CONNECTION'
    $nonce='c'*64;$ident='3'*64
    $admitted=WaitActor (StartActor $creds[1] 'good' 'Client' $readerSid $nonce $ident $rogueSid '')
    $duplicate=WaitActor (StartActor $creds[1] 'duplicate' 'Client' $readerSid $nonce $ident $readerSid '')
    $denied=WaitActor (StartActor $creds[2] 'rogue-spoof' 'Client' $rogueSid ('d'*64) ('4'*64) $readerSid '')
    $adminDenied=WaitActor (StartActor $null 'admin-spoof' 'Client' $current.User.Value ('e'*64) ('5'*64) $readerSid '')
    $serverResult=WaitActor $serv
    $observations['client_replies']=[ordered]@{positive=$admitted;duplicate=$duplicate;
        rogue_claimed_reader=$denied;admin_claimed_reader=$adminDenied}
    Need ($admitted -eq ($readerSid+'|RESERVED_ONLY_NO_SIGN')) 'VALID_PEER_COULD_NOT_RESERVE'
    Need ($duplicate -eq ($readerSid+'|ALREADY_RESERVED_NO_APPEND')) 'VALID_PEER_DUPLICATE_NOT_DETECTED'
    Need ($denied -eq ($rogueSid+'|HOLD_PEER_IDENTITY')) 'ROGUE_SID_SPOOF_NOT_REJECTED'
    Need ($adminDenied -eq ($current.User.Value+'|HOLD_PEER_IDENTITY')) 'ADMIN_PEER_NOT_REJECTED'
    Need ($serverResult -eq ($writerSid+'|G4_PIPE_GATE_COMPLETED')) 'SERVER_NOT_COMPLETE'
    $serverLines=@(Get-Content $logFile)
    Need ((@($serverLines|Where-Object{$_ -eq 'ALLOW_COUNT=2'})).Count -eq 1) 'SERVER_ALLOW_COUNT_WRONG'
    Need ((@($serverLines|Where-Object{$_ -eq 'DENY_COUNT=2'})).Count -eq 1) 'SERVER_DENY_COUNT_WRONG'
    Need ((@($serverLines|Where-Object{$_ -eq ('CLIENT_2_SID='+$rogueSid)})).Count -eq 1) 'SERVER_NOT_OBSERVING_ACTUAL_ROGUE_SID'
    Need ((@($serverLines|Where-Object{$_ -eq ('CLIENT_3_SID='+$current.User.Value)})).Count -eq 1) 'SERVER_NOT_OBSERVING_ACTUAL_ADMIN_SID'
    $state=& $python -I -B $journalPy --inspect $journal
    Need ($LASTEXITCODE -eq 0) 'AFTER_JOURNAL_INSPECT_FAILED'
    $observations['journal']=(ConvertFrom-Json -InputObject ($state|Out-String))
    Need ($observations['journal'].coherent -and $observations['journal'].v2_events -eq 3 -and $observations['journal'].v1_rows -eq 3) 'JOURNAL_NOT_EXACTLY_ONE_APPEND'
    $direct=WaitActor (StartActor $creds[1] 'reader-direct' 'Direct' $readerSid '' '' '' '')
    $directObj=ConvertFrom-Json $direct
    Need ($directObj.results.'append_v1.jsonl' -eq 'ACCESS_DENIED' -and $directObj.results.'append_v2.jsonl' -eq 'ACCESS_DENIED') 'READER_DIRECT_WRITE_NOT_DENIED'
    $post=& $python -I -B $journalPy --inspect $journal
    Need ($LASTEXITCODE -eq 0) 'AFTER_DIRECT_INSPECT_FAILED'
    Need (($post|Out-String).Trim() -eq ($state|Out-String).Trim()) 'DIRECT_WRITE_MODIFIED_JOURNALS'
    $observations['direct_probe']=$directObj
    $observations['server_readback']=$serverLines
    $observations['dacl']=@(& icacls.exe $journal)
    $observations['result']='PASS_SYNTHETIC_PEER_SID'
    Write-Host 'G4_OS_PEER_SID_ON_PIPE=PASS'
    Write-Host 'G4_FORGED_PAYLOAD_SID_REJECTED=PASS'
    Write-Host 'G4_ADMIN_WITHOUT_PEER_ROLE_REJECTED=PASS'
    Write-Host 'G4_REAL_V9_JOURNAL_FORMAT_ONE_APPEND=PASS'
    Write-Host 'G4_RESTRICTED_DIRECT_IO_DENIED=2/2'
} catch {
    $observations['result']='HOLD'
    $observations['error']=$_.Exception.Message
    Write-Host ('G4_HOLD='+$_.Exception.Message)
    throw
} finally {
    foreach($p in $children){
        if($null -ne $p.process -and -not $p.process.HasExited){try{$p.process.Kill()}catch{}}
    }
    $clean=$true
    if(Test-Path $root){try{Remove-Item -LiteralPath $root -Recurse -Force}catch{$clean=$false}}
    foreach($n in @($created)){try{Remove-LocalUser -Name $n -ErrorAction Stop}catch{$clean=$false}}
    foreach($n in @($created)){if(Get-LocalUser -Name $n -ErrorAction SilentlyContinue){$clean=$false}}
    if(Test-Path $root){$clean=$false}
    $observations['cleanup_verified']=$clean
    [IO.File]::WriteAllText($report,(ConvertTo-Json -InputObject $observations -Depth 10)+[char]10,[Text.UTF8Encoding]::new($false))
    Write-Host ('G4_SYNTHETIC_CLEANUP='+$(if($clean){'PASS'}else{'HOLD'}))
}
