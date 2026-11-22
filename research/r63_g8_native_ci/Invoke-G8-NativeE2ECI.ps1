# R63 G8: disposable GitHub Windows runner ONLY. Test-only local accounts and Software KSP.
# Integrates REAL Windows Named Pipe peer token + signed synthetic actor grants/veto +
# durable per-nonce use-intent + actual NCryptSignHash + process-death/retry.
# No Ario original signer, Windows service, real keys, main, laptop, or trust activation.
param([Parameter(Mandatory=$true)][string]$PayloadFile)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or
    $env:RUNNER_OS -ne 'Windows' -or $env:GITHUB_ACTIONS -ne 'true' -or
    $env:GITHUB_REPOSITORY -ne 'SepehrGhanbari/Ario') { throw 'REFUSE_G8_NON_CI_ENVIRONMENT' }
$who=[Security.Principal.WindowsIdentity]::GetCurrent()
if (-not [Security.Principal.WindowsPrincipal]::new($who).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'G8_REQUIRES_EPHEMERAL_RUNNER_ADMIN' }
$psExe=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$short=[guid]::NewGuid().ToString('N').Substring(0,8)
$root=Join-Path $env:PUBLIC ('ArioR63G8_'+$short)
$actor=Join-Path $PSScriptRoot 'Invoke-G8-Actor.ps1'
$source=Join-Path $PSScriptRoot 'G8IntegratedBroker.cs'
$names=@(('R63G8W'+$short),('R63G8R'+$short),('R63G8X'+$short))
$created=@();$processes=@();$actorCreds=@()
$reportPath=Join-Path $env:GITHUB_WORKSPACE ('r63-g8-native-report-'+$short+'.json')
$zipPath=Join-Path $env:GITHUB_WORKSPACE ('r63-g8-native-evidence-'+$short+'.zip')
$successful=$false;$cleanup=$true;$outcome='HOLD';$errors=@()
$summary=[ordered]@{scope='RESEARCH_ONLY_SYNTHETIC_WINDOWS_G8';run=$short;source='G8IntegratedBroker.cs';
    real_ario_key='NOT_USED';native_v9_signer='NOT_EXECUTED';independent_admin='NOT_ESTABLISHED';
    phone_floor='SEQ3_UNCHANGED';latest_seq4='NOT_APPROVED';
    native_signer='SOFTWARE_KSP_DISPOSABLE_P256';status='HOLD';results=[ordered]@{}}
function Need([bool]$valid,[string]$msg){if(-not $valid){throw $msg}}
function NativeOk([string]$tag){if($LASTEXITCODE -ne 0){throw ('NATIVE_WINDOWS_CALL_FAILED_'+$tag+'_'+$LASTEXITCODE)}}
function Cred([string]$username){
    $rng=[Security.Cryptography.RandomNumberGenerator]::Create()
    $bytes=[byte[]]::new(48);try{$rng.GetBytes($bytes)}finally{$rng.Dispose()}
    return [PSCredential]::new(('.\'+$username),
       (ConvertTo-SecureString ([Convert]::ToBase64String($bytes)) -AsPlainText -Force))
}
function As([object]$credential,[string]$tag,[string]$role,[string]$case,[string]$pipe,
   [string]$expected,[string]$phase,[int]$count){
    $out=Join-Path $env:RUNNER_TEMP ('g8-'+$short+'-'+$tag+'.out')
    $err=Join-Path $env:RUNNER_TEMP ('g8-'+$short+'-'+$tag+'.err')
    $args=@('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
            '-File',('"'+$actor+'"'),'-Role',$role,'-Root',('"'+$root+'"'))
    if($case){$args+=@('-Case',$case)}
    if($pipe){$args+=@('-Pipe',$pipe)}
    if($writerSid){$args+=@('-WriterSid',$writerSid)}
    if($readerSid){$args+=@('-ReaderSid',$readerSid)}
    if($expected){$args+=@('-ExpectedSid',$expected)}
    if($phase){$args+=@('-Phase',$phase)}
    if($count){$args+=@('-Count',[string]$count)}
    $kwargs=@{FilePath=$psExe;ArgumentList=($args -join ' ');PassThru=$true;
       WindowStyle='Hidden';RedirectStandardOutput=$out;RedirectStandardError=$err}
    if($null -ne $credential){$kwargs['Credential']=$credential}
    $p=Start-Process @kwargs
    # Cache process handle immediately (G3 Windows PowerShell 5.1 regression).
    $keep=$p.Handle
    Need ($null -ne $keep -and $keep -ne [IntPtr]::Zero) ('G8_MISSING_PROCESS_HANDLE_'+$tag)
    $child=[pscustomobject]@{tag=$tag;process=$p;stdout=$out;stderr=$err;pid=$p.Id}
    $script:processes+=,$child
    return $child
}
function Await([object]$child,[int]$expected){
    if (-not $child.process.WaitForExit(60000)) {
        try{$child.process.Kill()}catch{}
        throw ('G8_PROCESS_TIMEOUT_'+$child.tag)
    }
    $got=$child.process.ExitCode
    if($null -eq $got -or $got -ne $expected){
        $detail=if(Test-Path $child.stderr){Get-Content $child.stderr -Raw}else{'NO_STDERR'}
        throw ('G8_EXIT_WRONG_'+$child.tag+'_ACTUAL_'+$got+'_EXPECTED_'+$expected+'_'+$detail)
    }
    $lines=if(Test-Path $child.stdout){(Get-Content $child.stdout -Raw).Trim()}else{''}
    return [string]$lines
}
function Pair([string]$case,[string]$phase,[int]$expectExit,
              [object]$whoCred,[string]$expectedSid){
    $pipe='ArioR63G8_'+$short
    $server=As $actorCreds[0] ('s-'+$case+'-'+$phase) 'Server' $case $pipe '' $phase 1
    Start-Sleep -Milliseconds 600
    Need (-not $server.process.HasExited) ('G8_SERVER_FAILED_BEFORE_PIPE_'+$case)
    $client=As $whoCred ('c-'+$case+'-'+$phase) 'Client' $case $pipe $expectedSid '' 1
    $reply=Await $client 0
    $output=Await $server $expectExit
    return [pscustomobject]@{reply=$reply;server=$output;server_pid=$server.pid;client_pid=$client.pid}
}
function State([string]$case){
    $dir=Join-Path $root $case
    $out=[ordered]@{intent=[IO.File]::Exists((Join-Path $dir 'use-intent.txt'));
        native_enter=[IO.File]::Exists((Join-Path $dir 'native-enter.txt'));
        native_return=[IO.File]::Exists((Join-Path $dir 'native-return.txt'));
        receipt=[IO.File]::Exists((Join-Path $dir 'receipt-public.txt'))}
    foreach($n in @('use-intent.txt','native-enter.txt','native-return.txt','receipt-public.txt')) {
        $path=Join-Path $dir $n
        if([IO.File]::Exists($path)){$out[$n+'_sha256']=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
    }
    return $out
}
try {
    Need (-not [IO.Directory]::Exists($root) -and -not [IO.File]::Exists($reportPath) -and -not [IO.File]::Exists($zipPath)) 'G8_REFUSE_EXISTING_OUTPUT'
    Need ([IO.File]::Exists($PayloadFile)) 'G8_MISSING_G7_SOURCE_BOUND_PAYLOAD'
    $g7=(Get-FileHash -Algorithm SHA256 -LiteralPath $PayloadFile).Hash.ToLowerInvariant()
    $summary['g7_source_bound_payload_sha256']=$g7
    $summary['source_sha256']=(Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash.ToLowerInvariant()
    for($i=0;$i -lt $names.Length;$i++) {
        $credential=Cred $names[$i]
        New-LocalUser -Name $names[$i] -Password $credential.Password -AccountNeverExpires -PasswordNeverExpires -Description 'R63 G8 disposable synthetic Windows CI actor'|Out-Null
        $created+=,$names[$i];$actorCreds+=,$credential
    }
    $writerSid=(Get-LocalUser -Name $names[0]).SID.Value
    $readerSid=(Get-LocalUser -Name $names[1]).SID.Value
    $rogueSid=(Get-LocalUser -Name $names[2]).SID.Value
    Need ($writerSid -ne $readerSid -and $readerSid -ne $rogueSid -and $writerSid -ne $rogueSid) 'G8_SID_COLLISION'
    $summary['sids']=[ordered]@{writer=$writerSid;reader=$readerSid;rogue=$rogueSid;admin=$who.User.Value}
    [IO.Directory]::CreateDirectory($root)|Out-Null
    & icacls.exe $root /inheritance:r | Out-Null;NativeOk 'REMOVE_DACL_INHERITANCE'
    $grants=@('*S-1-5-18:(OI)(CI)F','*S-1-5-32-544:(OI)(CI)F',
        ('*'+$writerSid+':(OI)(CI)M'),('*'+$readerSid+':(OI)(CI)RX'),('*'+$rogueSid+':(OI)(CI)RX'))
    & icacls.exe $root /grant:r $grants | Out-Null;NativeOk 'SET_DACL'
    Copy-Item -LiteralPath $PayloadFile -Destination (Join-Path $root 'payload.bin') -ErrorAction Stop
    $dll=Join-Path $root 'G8IntegratedBroker.dll'
    $compile='Add-Type -Path "'+$source+'" -OutputAssembly "'+$dll+'" -ErrorAction Stop'
    & $psExe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command $compile
    NativeOk 'G8_CSHARP_COMPILE'
    Need ([IO.File]::Exists($dll)) 'G8_COMPILED_ASSEMBLY_MISSING'
    $f=As $null 'fixture' 'Fixture' '' '' '' '' 1
    $fixtureLog=Await $f 0
    Need ($fixtureLog -match 'G8_EPHEMERAL_TWO_ACTOR_FIXTURES=PASS') 'G8_ACTOR_FIXTURE_FAILED'
    $summary['actor_public_pins']=[ordered]@{
       founder=(Get-FileHash -LiteralPath (Join-Path $root 'founder.pub') -Algorithm SHA256).Hash.ToLowerInvariant();
       ario=(Get-FileHash -LiteralPath (Join-Path $root 'ario.pub') -Algorithm SHA256).Hash.ToLowerInvariant()}
    Need ($summary['actor_public_pins']['founder'] -ne $summary['actor_public_pins']['ario']) 'G8_ACTORS_NOT_DISTINCT'

    # One actual OS-token authenticated server: good grant signs, repeat replays, rogue SID denied.
    $pipe='ArioR63G8_'+$short
    $serv=As $actorCreds[0] 'server-normal' 'Server' 'normal' $pipe '' 'normal' 3
    Start-Sleep -Milliseconds 800
    Need (-not $serv.process.HasExited) 'G8_NORMAL_SERVER_NOT_READY'
    $ok=Await (As $actorCreds[1] 'client-valid' 'Client' 'normal' $pipe $readerSid '' 1) 0
    $same=Await (As $actorCreds[1] 'client-replay' 'Client' 'normal' $pipe $readerSid '' 1) 0
    $rogue=Await (As $actorCreds[2] 'client-rogue' 'Client' 'normal' $pipe $rogueSid '' 1) 0
    $normalLog=Await $serv 0
    Need ($ok.StartsWith('SIGNED_') -and $same -ceq $ok -and $rogue -eq 'HOLD_PEER_IDENTITY') 'G8_NORMAL_PEER_GATE_REPLAY_FAILED'
    Need ($normalLog -match [regex]::Escape($writerSid)) 'G8_WRITER_OS_TOKEN_NOT_LOGGED'
    $normal=State 'normal'
    Need ($normal.intent -and $normal.native_enter -and $normal.native_return -and $normal.receipt) 'G8_NORMAL_DURABILITY_FAILED'
    $verify=Await (As $null 'public-audit-normal' 'Verify' 'normal' '' '' '' 1) 0
    Need ($verify -match 'G8_SEPARATE_PUBLIC_RECEIPT_VERIFY=PASS') 'G8_PUBLIC_ONLY_NORMAL_BAD'
    $summary['results']['normal']=[ordered]@{first='SIGNED_VERIFIED';same_public_bytes_replayed=($same -ceq $ok);
      rogue_sid_holds=($rogue -eq 'HOLD_PEER_IDENTITY');state=$normal;public_verifier=$verify;
      source_logs=$normalLog}
    Write-Host 'G8_NATIVE_AUTHENTICATED_TWO_ACTOR_GRANT=PASS'
    Write-Host 'G8_DUPLICATE_REPLAYS_EXACT_PUBLIC_RECEIPT=PASS'
    Write-Host 'G8_FORGED_RPC_PEER_REJECTED=PASS'

    foreach($badCase in @(@('veto','HOLD_ARIO_VETO'),@('bad','HOLD_BAD_ACTOR_APPROVAL'),@('revoked','HOLD_REVOKED'))) {
        $c=$badCase[0];$expect=$badCase[1]
        $one=Pair $c 'normal' 0 $actorCreds[1] $readerSid
        Need ($one.reply -eq $expect) ('G8_AUTH_GATE_FAIL_OPEN_'+$c+'_'+$one.reply)
        $st=State $c
        Need (-not $st.intent -and -not $st.native_enter -and -not $st.native_return -and -not $st.receipt) ('G8_BAD_AUTH_REACHED_CNG_'+$c)
        $summary['results'][$c]=[ordered]@{response=$one.reply;state=$st}
        Write-Host ('G8_'+$c.ToUpper()+'_NO_SIGN=PASS')
    }

    # Each crash case is a separate *persistent* test key that must survive parent process death.
    # The recovery parent MUST NOT issue an extra NCryptSignHash for the same nonce.
    $faults=@(
      [pscustomobject]@{case='before';enter=$false;returned=$false;receipt=$false;replay='HOLD_UNCERTAIN'},
      [pscustomobject]@{case='after';enter=$true;returned=$true;receipt=$false;replay='HOLD_UNCERTAIN'},
      [pscustomobject]@{case='receipt';enter=$true;returned=$true;receipt=$true;replay='SIGNED_'})
    foreach($fault in $faults) {
        $first=Pair $fault.case $fault.case 73 $actorCreds[1] $readerSid
        Need ($first.reply -eq 'NO_ACK') ('G8_CRASH_ACK_NOT_LOST_'+$fault.case+'_'+$first.reply)
        $before=State $fault.case
        Need ($before.intent -and $before.native_enter -eq $fault.enter -and
             $before.native_return -eq $fault.returned -and $before.receipt -eq $fault.receipt) ('G8_FAULT_STATE_BAD_'+$fault.case)
        $recovery=Pair $fault.case 'recovery' 0 $actorCreds[1] $readerSid
        $after=State $fault.case
        Need ($first.server_pid -ne $recovery.server_pid) ('G8_RESTART_REUSED_PID_'+$fault.case)
        Need ($after.native_enter -eq $before.native_enter -and $after.native_return -eq $before.native_return -and
              $after.receipt -eq $before.receipt) ('G8_RESTART_USED_CNG_AGAIN_'+$fault.case)
        foreach($k in @('use-intent.txt_sha256','native-enter.txt_sha256','native-return.txt_sha256','receipt-public.txt_sha256')){
            Need ($after[$k] -ceq $before[$k]) ('G8_RESTART_CHANGED_EVIDENCE_'+$fault.case+'_'+$k)
        }
        if ($fault.case -eq 'receipt') {
            Need ($recovery.reply.StartsWith('SIGNED_')) 'G8_RECEIPT_REPLAY_NOT_SIGNED'
            $raw=[Convert]::ToBase64String([IO.File]::ReadAllBytes((Join-Path (Join-Path $root $fault.case) 'receipt-public.txt')))
            Need ($recovery.reply -ceq ('SIGNED_'+$raw)) 'G8_SAVED_RECEIPT_NOT_BYTE_IDENTICAL'
            $checked=Await (As $null 'public-audit-receipt' 'Verify' 'receipt' '' '' '' 1) 0
            Need ($checked -match 'G8_SEPARATE_PUBLIC_RECEIPT_VERIFY=PASS') 'G8_DURABLE_RECEIPT_INVALID'
        } else {
            Need ($recovery.reply -eq 'HOLD_UNCERTAIN') ('G8_RETRY_NOT_HOLD_'+$fault.case+'_'+$recovery.reply)
        }
        $summary['results'][$fault.case]=[ordered]@{crash_exit=73;first_reply=$first.reply;
           parent_pid=$first.server_pid;recovery_pid=$recovery.server_pid;
           retry=if($fault.case -eq 'receipt'){'EXACT_STORED_RECEIPT'}else{$recovery.reply};
           before=$before;after=$after}
        Write-Host ('G8_'+$fault.case.ToUpper()+'_CRASH_RECOVERED_WITHOUT_RESIGN=PASS')
    }

    $last=Await (As $actorCreds[0] 'delete-all-disposable-keys' 'Cleanup' '' '' '' '' 1) 0
    Need ($last -match 'G8_TEMP_CNG_KEYS_REMOVED=3') ('G8_DISPOSABLE_KEY_CLEANUP_WRONG_'+$last)
    $summary['keys_removed_readback']=$last
    $successful=$true;$outcome='PASS_NATIVE_INTEGRATED_SYNTHETIC_ONLY';
    $summary['status']=$outcome
    Write-Host 'G8_REAL_NATIVE_CNG_ENTER_RETURN_PER_CASE=PASS'
    Write-Host 'G8_SYNTHETIC_NATIVE_SIGNER_INTEGRATION=PASS'
} catch {
    $summary['status']='HOLD'
    $summary['error']=$_.Exception.GetType().FullName+' '+$_.Exception.Message
    Write-Host ('G8_HOLD='+$summary['error'])
    $errors+=,$summary['error']
} finally {
    foreach($child in @($processes)){
      if($null -ne $child.process -and -not $child.process.HasExited){
        try{$child.process.Kill();$child.process.WaitForExit(10000)|Out-Null}catch{$cleanup=$false}
      }
    }
    # Capture only public source+requests+receipts+durable synthetic markers, never actor private keys.
    try {
       if([IO.Directory]::Exists($root)){
          Add-Type -AssemblyName System.IO.Compression.FileSystem
          [IO.Compression.ZipFile]::CreateFromDirectory($root,$zipPath)
       }
    } catch { $cleanup=$false;Write-Host ('G8_EVIDENCE_CAPTURE_HOLD='+$_.Exception.Message) }
    if([IO.Directory]::Exists($root)){
       try{Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction Stop}catch{$cleanup=$false}
    }
    foreach($name in @($created)) {
      try{Remove-LocalUser -Name $name -ErrorAction Stop}catch{$cleanup=$false}
      if(Get-LocalUser -Name $name -ErrorAction SilentlyContinue){$cleanup=$false}
    }
    if([IO.Directory]::Exists($root)){$cleanup=$false}
    $summary['cleanup_verified']=$cleanup
    $summary['final_verdict']=if($successful -and $cleanup){'PASS_SYNTHETIC_G8_ONLY'}else{'HOLD'}
    [IO.File]::WriteAllText($reportPath,(ConvertTo-Json -InputObject $summary -Depth 20)+[char]10,[Text.UTF8Encoding]::new($false))
    Write-Host ('G8_REPORT='+$reportPath)
    if([IO.File]::Exists($zipPath)){Write-Host ('G8_EVIDENCE='+$zipPath)}
    Write-Host ('G8_TEMP_USER_AND_JOURNAL_CLEANUP='+$(if($cleanup){'PASS'}else{'HOLD'}))
    Write-Host ('G8_VERDICT='+$summary['final_verdict'])
}
if($summary['final_verdict'] -ne 'PASS_SYNTHETIC_G8_ONLY'){exit 1}
exit 0
