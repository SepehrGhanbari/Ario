# R63 G3 — DISPOSABLE Windows SID-restricted synthetic witness RPC acceptance.
# No real Ario key, original V9 service, production journal, host-policy change.
param([Parameter(Mandatory=$true)][ValidateSet('CI','Guest')][string]$Mode)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'WINDOWS_ONLY' }
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=[Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'HOLD_G3_REQUIRES_ELEVATED_EPHEMERAL_RUNNER_OR_GUEST'
}
if ($Mode -eq 'CI') {
    if ($env:RUNNER_OS -ne 'Windows' -or $env:GITHUB_ACTIONS -ne 'true' -or
        $env:GITHUB_REPOSITORY -ne 'SepehrGhanbari/Ario') { throw 'REFUSE_NON_ARIO_CI' }
    $inputRoot=$PSScriptRoot
    $python=(Get-Command python -ErrorAction Stop).Source
    $exportRoot=$env:GITHUB_WORKSPACE
} else {
    if ($env:USERNAME -ne 'WDAGUtilityAccount' -or
        -not [IO.Directory]::Exists('C:\R63-G3-Input') -or
        -not [IO.Directory]::Exists('C:\R63-G3-Runtime') -or
        -not [IO.Directory]::Exists('C:\R63-G3-Exports')) {
        throw 'REFUSE_NOT_IN_EXPECTED_FRESH_WINDOWS_SANDBOX'
    }
    $inputRoot='C:\R63-G3-Input'
    $python='C:\R63-G3-Runtime\python.exe'
    $exportRoot='C:\R63-G3-Exports'
}
$code=Join-Path $inputRoot 'witness_g3.py'
$v2=Join-Path $inputRoot 'spend_chain_v2.py'
$expected='c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd'
if (-not [IO.File]::Exists($code) -or -not [IO.File]::Exists($v2) -or
    -not [IO.File]::Exists($python) -or -not [IO.Directory]::Exists($exportRoot)) {
    throw 'MISSING_REQUIRED_SOURCE_RUNTIME_EXPORT'
}
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $v2).Hash.ToLowerInvariant() -cne $expected) {
    throw 'FROZEN_V9_V2_PIN_MISMATCH'
}
$short=[Guid]::NewGuid().ToString('N').Substring(0,7)
$runID=('{0}-{1}' -f $PID,$short)
$writer='R63G3W'+$short
$reader='R63G3R'+$short
$root=Join-Path $env:PUBLIC ('ArioR63G3_'+$short)
$runLog=Join-Path $exportRoot ('R63-G3-Run-'+$runID+'.txt')
$reportPath=Join-Path $exportRoot ('R63-G3-Report-'+$runID+'.json')
$evidencePath=Join-Path $exportRoot ('R63-G3-Evidence-'+$runID+'.zip')
$writerCreated=$false;$readerCreated=$false;$outcome='HOLD';$cleanup='UNKNOWN'
$report=[ordered]@{mode=$Mode;run_id=$runID;scope='RESEARCH_ONLY_SYNTHETIC_G3';
                   frozen_v9_v2_sha256=$expected;real_v9='NOT_EXECUTED';signer='NOT_EXECUTED';
                   independent_custody='NOT_ESTABLISHED';rpc_peer_token_auth='NOT_ESTABLISHED';
                   controller_token_sid=$identity.User.Value;
                   source_sha256=[ordered]@{witness=(Get-FileHash -Algorithm SHA256 -LiteralPath $code).Hash.ToLowerInvariant();
                       controller=(Get-FileHash -Algorithm SHA256 -LiteralPath $PSCommandPath).Hash.ToLowerInvariant();
                       v2=$expected;runtime_python=(Get-FileHash -Algorithm SHA256 -LiteralPath $python).Hash.ToLowerInvariant()};
                   results=[ordered]@{}}
function Say([string]$msg) {
    Write-Host $msg
    Add-Content -LiteralPath $runLog -Value $msg -Encoding UTF8
}
function NativeOk([string]$name) {
    if ($LASTEXITCODE -ne 0) {throw ('NATIVE_WINDOWS_CALL_FAILED_'+$name+'_'+$LASTEXITCODE)}
}
function Credential([string]$name) {
    $rng=[Security.Cryptography.RandomNumberGenerator]::Create()
    try { $bytes=New-Object byte[] 48; $rng.GetBytes($bytes) }
    finally { $rng.Dispose() }
    $secure=ConvertTo-SecureString ([Convert]::ToBase64String($bytes)) -AsPlainText -Force
    return [PSCredential]::new(('.\'+$name),$secure)
}
function PyAdmin([string[]]$arguments) {
    $output=& $python -I -B $code @arguments 2>&1
    if ($LASTEXITCODE -ne 0) {throw ('ADMIN_SYNTHETIC_PYTHON_FAILED_'+($output | Out-String))}
    return ($output | Out-String).Trim()
}
function StartAs([PSCredential]$cred,[string[]]$a,[string]$tag,[bool]$wait) {
    $out=Join-Path $env:TEMP ('r63g3-'+$short+'-'+$tag+'.out')
    $err=Join-Path $env:TEMP ('r63g3-'+$short+'-'+$tag+'.err')
    $cmd='-I -B "'+$code+'" '+(($a | ForEach-Object {'"'+$_+'"'}) -join ' ')
    $kwargs=@{FilePath=$python;ArgumentList=$cmd;Credential=$cred;PassThru=$true;
              WindowStyle='Hidden';RedirectStandardOutput=$out;RedirectStandardError=$err}
    if ($wait) { $kwargs['Wait']=$true }
    $p=Start-Process @kwargs
    # Windows PowerShell 5.1 / Start-Process -Credential can lose
    # the ExitCode after WaitForExit unless the handle is cached early.
    # Null exit codes are never interpreted as success.
    if (-not $wait) {
        try { $savedHandle=$p.Handle }
        catch { throw ('HOLD_PROCESS_HANDLE_NOT_AVAILABLE_'+$tag+'_'+$_.Exception.Message) }
        if ($null -eq $savedHandle -or $savedHandle -eq [IntPtr]::Zero) {
            throw ('HOLD_PROCESS_HANDLE_NULL_'+$tag)
        }
    }
    if ($wait) {
        if ($p.ExitCode -ne 0) {
            $detail=if ([IO.File]::Exists($err)) { [IO.File]::ReadAllText($err) } else { '<NO_CHILD_STDERR>' }
            throw ('CHILD_'+$tag+'_EXIT_'+$p.ExitCode+'_'+$detail)
        }
        return [ordered]@{stdout=[IO.File]::ReadAllText($out).Trim();pid=$p.Id;exit=$p.ExitCode}
    }
    return [ordered]@{process=$p;stdout_path=$out;stderr_path=$err;pid=$p.Id}
}
function AwaitPort([string]$case,[object]$job) {
    $target=Join-Path $case 'port.txt';$t=[Diagnostics.Stopwatch]::StartNew()
    while ($t.Elapsed.TotalSeconds -lt 25) {
        if ([IO.File]::Exists($target)) {
            $p=[IO.File]::ReadAllText($target).Trim()
            if ($p -match '^[0-9]+$' -and [int]$p -gt 0) {return}
        }
        if ($job.process.HasExited) {
            $stderr=if ([IO.File]::Exists($job.stderr_path)) {[IO.File]::ReadAllText($job.stderr_path)}else{''}
            throw ('WITNESS_EXITED_BEFORE_LISTEN_'+$stderr)
        }
        Start-Sleep -Milliseconds 80
    }
    throw 'WITNESS_READINESS_TIMEOUT'
}
function AwaitExit([object]$job,[int]$expected) {
    if (-not $job.process.WaitForExit(90000)) {
        try { $job.process.Kill() } catch {}
        throw 'WITNESS_EXIT_TIMEOUT'
    }
    if ($job.process.ExitCode -ne $expected) {
        $stderr=if ([IO.File]::Exists($job.stderr_path)) {[IO.File]::ReadAllText($job.stderr_path)} else{''}
        throw ('WITNESS_EXIT_WRONG_'+$job.process.ExitCode+'_EXPECTED_'+$expected+'_'+$stderr)
    }
}
function Inspect([string]$case) {
    return ConvertFrom-Json -InputObject (PyAdmin @('--inspect',$case))
}
function RawCapture([string]$case,[string]$dest) {
    [IO.Directory]::CreateDirectory($dest) | Out-Null
    foreach($name in @('v1.jsonl','v2.jsonl','uncertain.flag','writer-identity.json')) {
        $p=Join-Path $case $name
        if ([IO.File]::Exists($p)) { Copy-Item -LiteralPath $p -Destination (Join-Path $dest $name) -ErrorAction Stop }
    }
    $snap=Inspect $case
    [IO.File]::WriteAllText((Join-Path $dest 'inspect.json'),(ConvertTo-Json $snap -Depth 10),[Text.UTF8Encoding]::new($false))
    return $snap
}
function ReadAcl([string]$case) {
    $arr=@()
    foreach($p in @($case,(Join-Path $case 'v1.jsonl'),(Join-Path $case 'v2.jsonl'))) {
        $arr+=& icacls.exe $p
        NativeOk 'ICACLS_READBACK'
    }
    if ([IO.File]::Exists((Join-Path $case 'uncertain.flag'))) {
        $arr+=& icacls.exe (Join-Path $case 'uncertain.flag')
        NativeOk 'ICACLS_FLAG_READBACK'
    }
    return $arr
}
function MakeCase([string]$name) {
    $case=Join-Path $root $name
    $init=ConvertFrom-Json -InputObject (PyAdmin @('--prepare',$case))
    if ($init.v1_lines -ne 2 -or $init.v2_events -ne 2 -or -not $init.coherent) {throw 'BAD_BASELINE'}
    return $case
}
function Reader([string[]]$a,[string]$tag) {
    $done=StartAs $readerCred $a $tag $true
    return ConvertFrom-Json -InputObject $done.stdout
}
function CheckWriter([string]$case) {
    $obj=ConvertFrom-Json -InputObject ([IO.File]::ReadAllText((Join-Path $case 'writer-identity.json')))
    if ($obj.sid -ne $writerSid) {throw 'NOT_ACTUAL_WRITER_TOKEN'}
    return $obj
}
function CheckDirect([string]$case,[bool]$flag,[string]$tag) {
    $mode=if($flag){'flag'}else{'noflag'}
    $r=Reader @('--direct',$case,$readerSid,$mode) $tag
    if ($r.token.sid -ne $readerSid) {throw 'NOT_ACTUAL_READER_TOKEN'}
    $expected=if($flag){5}else{4}
    $denialNames=@($r.denials.PSObject.Properties | ForEach-Object { $_.Name })
    if ($denialNames.Count -ne $expected) {throw 'WRONG_DIRECT_DENIAL_COUNT'}
    foreach($entry in $r.denials.PSObject.Properties) {
        if ($entry.Value -ne 'ACCESS_DENIED') {throw ('UNAUTHORIZED_DIRECT_WRITE_ACCEPTED_'+$entry.Name)}
    }
    return $r
}
$jobs=@()
try {
    if ([IO.Directory]::Exists($root) -or [IO.File]::Exists($reportPath) -or
        [IO.File]::Exists($evidencePath)) {throw 'REFUSE_EXISTING_OUTPUT'}
    $writerCred=Credential $writer
    $readerCred=Credential $reader
    New-LocalUser -Name $writer -Password $writerCred.Password -AccountNeverExpires -PasswordNeverExpires -Description 'R63 G3 synthetic CI/guest writer' | Out-Null
    $writerCreated=$true
    New-LocalUser -Name $reader -Password $readerCred.Password -AccountNeverExpires -PasswordNeverExpires -Description 'R63 G3 synthetic CI/guest reader' | Out-Null
    $readerCreated=$true
    $writerSid=(Get-LocalUser -Name $writer).SID.Value
    $readerSid=(Get-LocalUser -Name $reader).SID.Value
    if ($writerSid -eq $readerSid) {throw 'DUPLICATED_SID'}
    $report['writer_sid']=$writerSid;$report['reader_sid']=$readerSid
    [IO.Directory]::CreateDirectory($root)|Out-Null
    & icacls.exe $root /inheritance:r | Out-Null; NativeOk 'REMOVE_INHERITANCE'
    $grants=@('*S-1-5-18:(OI)(CI)F','*S-1-5-32-544:(OI)(CI)F',
       ('*'+$writerSid+':(OI)(CI)M'),('*'+$readerSid+':(OI)(CI)RX'))
    & icacls.exe $root /grant:r $grants | Out-Null; NativeOk 'EXPLICIT_RESTRICTED_DACL'
    $evidenceDir=Join-Path $root 'captured'
    [IO.Directory]::CreateDirectory($evidenceDir)|Out-Null
    # Case normal: one successful V2+V1 append per separate-client group.
    $normal=MakeCase 'normal'
    $job=StartAs $writerCred @('--server',$normal,'normal','26',$writerSid) 'writer-normal' $false
    $jobs+=,$job;AwaitPort $normal $job
    $liveDirect=CheckDirect $normal $false 'direct-while-witness-online'
    $batchResults=@()
    foreach($cnt in @(2,8,16)) {
        $nonce=('{0:x64}' -f (5000+$cnt))
        $ident=('{0:x64}' -f (6000+$cnt))
        $b=Reader @('--batch',$normal,$nonce,$ident,[string]$cnt,$readerSid) ('batch-'+$cnt)
        if ($b.token.sid -ne $readerSid -or $b.count -ne $cnt) {throw 'READER_BATCH_SID_OR_COUNT_BAD'}
        if ((@($b.replies|Where-Object{$_ -eq 'RESERVED_ONLY_NO_SIGN'})).Count -ne 1 -or
            (@($b.replies|Where-Object{$_ -eq 'ALREADY_RESERVED_NO_APPEND'})).Count -ne ($cnt-1)) {
            throw ('EXACTLY_ONE_RESERVATION_BROKEN_'+$cnt)
        }
        $batchResults+=,$b
        $state=Inspect $normal
        if (-not $state.coherent -or $state.v2_events -ne (2+$batchResults.Count)) {throw 'JOURNAL_AFTER_BATCH_INVALID'}
    }
    AwaitExit $job 0
    $direct=CheckDirect $normal $false 'direct-normal'
    $normalSnap=RawCapture $normal (Join-Path $evidenceDir 'normal')
    $report['results']['normal']=[ordered]@{batches=$batchResults;direct=$direct;direct_live=$liveDirect;snapshot=$normalSnap;
        writer=CheckWriter $normal;dacl=@(ReadAcl $normal)}
    Say 'G3_NORMAL_WRITER_RPC_V1_V2_CANONICAL=PASS'
    Say 'G3_2_8_16_SEPARATE_READER_CLIENTS=PASS'
    Say 'G3_DIRECT_NONCOOPERATIVE_WRITES_DENIED=4/4'

    $expected=@{pre_v2=@(2,2);post_v2=@(2,3);post_v1=@(3,3)}
    $index=0
    foreach($phase in @('pre_v2','post_v2','post_v1')) {
        $index++
        $case=MakeCase $phase
        $job=StartAs $writerCred @('--server',$case,$phase,'1',$writerSid) ('writer-crash-'+$phase) $false
        $jobs+=,$job;AwaitPort $case $job
        $n=('{0:x64}' -f (7000+$index));$k=('{0:x64}' -f (8000+$index))
        $first=StartAs $readerCred @('--client',$case,$n,$k,'crash',$readerSid) ('reader-crash-'+$phase) $true
        if ($first.stdout -ne 'NO_ACK') {throw ('CRASH_UNEXPECTED_ACK_'+$phase+'_'+$first.stdout)}
        AwaitExit $job 73
        $afterCrash=RawCapture $case (Join-Path $evidenceDir ($phase+'-after-crash'))
        if ($afterCrash.v1_lines -ne $expected[$phase][0] -or
            $afterCrash.v2_events -ne $expected[$phase][1] -or -not $afterCrash.flag_present) {
            throw ('WRONG_CRASH_STATE_'+$phase)
        }
        $denials=CheckDirect $case $true ('direct-'+$phase)
        Remove-Item -LiteralPath (Join-Path $case 'port.txt') -ErrorAction Stop
        $recovery=StartAs $writerCred @('--server',$case,'recovery','1',$writerSid) ('writer-recovery-'+$phase) $false
        $jobs+=,$recovery;AwaitPort $case $recovery
        $retry=StartAs $readerCred @('--client',$case,$n,$k,'normal',$readerSid) ('reader-retry-'+$phase) $true
        if ($retry.stdout -ne 'HOLD_UNCERTAIN') {throw ('RETRY_NOT_HOLD_'+$phase+'_'+$retry.stdout)}
        AwaitExit $recovery 0
        $afterRecovery=RawCapture $case (Join-Path $evidenceDir ($phase+'-after-recovery'))
        if ($afterRecovery.v1_sha256 -ne $afterCrash.v1_sha256 -or
            $afterRecovery.v2_sha256 -ne $afterCrash.v2_sha256 -or
            $afterRecovery.flag_sha256 -ne $afterCrash.flag_sha256 -or
            $afterRecovery.v2_head -ne $afterCrash.v2_head) {throw ('RESTART_CHANGED_DURABLE_BYTES_'+$phase)}
        if ($job.pid -eq $recovery.pid) {throw 'CRASH_RECOVERY_SAME_PID'}
        $report['results'][$phase]=[ordered]@{parent_pid=$job.pid;recovery_pid=$recovery.pid;
            parent_exit=73;first_response=$first.stdout;replay_response=$retry.stdout;
            after_crash=$afterCrash;after_recovery=$afterRecovery;restricted_direct=$denials;
            recovery_writer=CheckWriter $case;dacl=@(ReadAcl $case)}
        Say ('G3_'+$phase.ToUpper()+'_EXIT73_RETRY_HOLD=PASS')
    }
    $report['status']='PASS_SYNTHETIC_G3_ONLY'
    $outcome='PASS'
    [IO.File]::WriteAllText((Join-Path $evidenceDir 'report.json'),
        (ConvertTo-Json -InputObject $report -Depth 35)+[char]10,[Text.UTF8Encoding]::new($false))
    # Export an authenticated-by-no-one yet internally hashed archive (same-admin).
    $zipScript=Join-Path $inputRoot 'evidence_g3.py'
    & $python -I -B $zipScript $evidenceDir $evidencePath
    if ($LASTEXITCODE -ne 0) {throw 'ZIP_EVIDENCE_EXPORT_FAILED'}
    Say 'G3_GUEST_SYNTHETIC_ACCEPTANCE=PASS'
} catch {
    $outcome='HOLD'
    $report['status']='HOLD_OR_FAIL'
    $report['error']=($_.Exception.GetType().FullName+' '+$_.Exception.Message)
    Say ('G3_HOLD='+$report['error'])
} finally {
    foreach($j in $jobs) {
        if ($null -ne $j.process -and -not $j.process.HasExited) {
            try { $j.process.Kill();$j.process.WaitForExit(10000)|Out-Null }
            catch { Say 'G3_PROCESS_CLEANUP_ERROR' }
        }
    }
    $clean=$true
    if ([IO.Directory]::Exists($root)) {
        try { Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction Stop }
        catch { $clean=$false;Say ('G3_TEMP_ROOT_CLEANUP_ERROR='+$_.Exception.Message) }
    }
    if ($readerCreated) {
        try { Remove-LocalUser -Name $reader -ErrorAction Stop }
        catch { $clean=$false;Say 'G3_READER_ACCOUNT_CLEANUP_ERROR' }
    }
    if ($writerCreated) {
        try { Remove-LocalUser -Name $writer -ErrorAction Stop }
        catch { $clean=$false;Say 'G3_WRITER_ACCOUNT_CLEANUP_ERROR' }
    }
    if ($readerCreated -and (Get-LocalUser -Name $reader -ErrorAction SilentlyContinue)) {$clean=$false}
    if ($writerCreated -and (Get-LocalUser -Name $writer -ErrorAction SilentlyContinue)) {$clean=$false}
    if ([IO.Directory]::Exists($root)) {$clean=$false}
    $report['cleanup_verified']=$clean
    $report['final_verdict']=if ($outcome -eq 'PASS' -and $clean) {'PASS_SYNTHETIC_G3'}else{'HOLD'}
    $report['custody']='SAME_GUEST_ADMIN_NOT_INDEPENDENT'
    [IO.File]::WriteAllText($reportPath,(ConvertTo-Json -InputObject $report -Depth 35)+[char]10,[Text.UTF8Encoding]::new($false))
    Say ('G3_TEMPORARY_CLEANUP='+$(if($clean){'PASS'}else{'HOLD'}))
    Say ('G3_REPORT='+$reportPath)
    if ([IO.File]::Exists($evidencePath)) {Say ('G3_EVIDENCE='+$evidencePath)}
    Say ('G3_VERDICT='+$report['final_verdict'])
}
if ($report['final_verdict'] -ne 'PASS_SYNTHETIC_G3') {exit 1}
