# R63 G8: disposable GitHub Windows runner ONLY. Test-only local accounts and Software KSP.
# Integrates REAL Windows Named Pipe peer token + signed synthetic actor grants/veto +
# durable per-nonce use-intent + actual NCryptSignHash + process-death/retry.
# No Ario original signer, Windows service, real keys, main, laptop, or trust activation.
param([Parameter(Mandatory=$true)][string]$PayloadFile)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or
    $env:RUNNER_OS -ne 'Windows' -or $env:GITHUB_ACTIONS -ne 'true' -or
    $env:GITHUB_REPOSITORY -ne 'SepehrGhanbari/Ario') { throw 'REFUSE_G9_NON_CI_ENVIRONMENT' }
$who=[Security.Principal.WindowsIdentity]::GetCurrent()
if (-not [Security.Principal.WindowsPrincipal]::new($who).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'G9_REQUIRES_EPHEMERAL_RUNNER_ADMIN' }
$psExe=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$short=[guid]::NewGuid().ToString('N').Substring(0,8)
$root=Join-Path $env:PUBLIC ('ArioR63G9_'+$short)
$custodyDir=Join-Path $env:PUBLIC ('ArioR63G9Cust_'+$short)
$custodyPipe='ArioR63G9C_'+$short
$actor=Join-Path $PSScriptRoot 'Invoke-G9-Actor.ps1'
$source=Join-Path $PSScriptRoot 'G9IntegratedBroker.cs'
$names=@(('R63G9W'+$short),('R63G9R'+$short),('R63G9X'+$short),('R63G9C'+$short))
$created=@();$processes=@();$actorCreds=@()
$reportPath=Join-Path $env:GITHUB_WORKSPACE ('r63-g9-native-report-'+$short+'.json')
$zipPath=Join-Path $env:GITHUB_WORKSPACE ('r63-g9-native-evidence-'+$short+'.zip')
$successful=$false;$cleanup=$true;$outcome='HOLD';$errors=@()
$summary=[ordered]@{scope='RESEARCH_ONLY_SYNTHETIC_WINDOWS_G8';run=$short;source='G9IntegratedBroker.cs';
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
    $args+=@('-CustodyPipe',$custodyPipe,'-CustodyDir',('"'+$custodyDir+'"'),'-CustodianSid',$custodianSid,'-BrokerSid',$writerSid)
    $kwargs=@{FilePath=$psExe;ArgumentList=($args -join ' ');PassThru=$true;
       WindowStyle='Hidden';RedirectStandardOutput=$out;RedirectStandardError=$err}
    if($null -ne $credential){$kwargs['Credential']=$credential}
    $p=Start-Process @kwargs
    # Cache process handle immediately (G3 Windows PowerShell 5.1 regression).
    $keep=$p.Handle
    Need ($null -ne $keep -and $keep -ne [IntPtr]::Zero) ('G9_MISSING_PROCESS_HANDLE_'+$tag)
    $child=[pscustomobject]@{tag=$tag;process=$p;stdout=$out;stderr=$err;pid=$p.Id}
    $script:processes+=,$child
    return $child
}
function Await([object]$child,[int]$expected){
    if (-not $child.process.WaitForExit(60000)) {
        try{$child.process.Kill()}catch{}
        throw ('G9_PROCESS_TIMEOUT_'+$child.tag)
    }
    $got=$child.process.ExitCode
    if($null -eq $got -or $got -ne $expected){
        $detail=if(Test-Path $child.stderr){Get-Content $child.stderr -Raw}else{'NO_STDERR'}
        throw ('G9_EXIT_WRONG_'+$child.tag+'_ACTUAL_'+$got+'_EXPECTED_'+$expected+'_'+$detail)
    }
    $lines=if(Test-Path $child.stdout){(Get-Content $child.stdout -Raw).Trim()}else{''}
    return [string]$lines
}
function Pair([string]$case,[string]$phase,[int]$expectExit,
              [object]$whoCred,[string]$expectedSid){
    $pipe='ArioR63G9_'+$short
    $server=As $actorCreds[0] ('s-'+$case+'-'+$phase) 'Server' $case $pipe '' $phase 1
    Start-Sleep -Milliseconds 600
    Need (-not $server.process.HasExited) ('G9_SERVER_FAILED_BEFORE_PIPE_'+$case)
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
    Need (-not [IO.Directory]::Exists($root) -and -not [IO.Directory]::Exists($custodyDir) -and -not [IO.File]::Exists($reportPath) -and -not [IO.File]::Exists($zipPath)) 'G9_REFUSE_EXISTING_OUTPUT'
    Need ([IO.File]::Exists($PayloadFile)) 'G9_MISSING_G7_SOURCE_BOUND_PAYLOAD'
    $g7=(Get-FileHash -Algorithm SHA256 -LiteralPath $PayloadFile).Hash.ToLowerInvariant()
    $summary['g7_source_bound_payload_sha256']=$g7
    $summary['source_sha256']=(Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash.ToLowerInvariant()
    for($i=0;$i -lt $names.Length;$i++) {
        $credential=Cred $names[$i]
        New-LocalUser -Name $names[$i] -Password $credential.Password -AccountNeverExpires -PasswordNeverExpires -Description 'R63 G9 disposable synthetic Windows CI actor'|Out-Null
        $created+=,$names[$i];$actorCreds+=,$credential
    }
    $writerSid=(Get-LocalUser -Name $names[0]).SID.Value
    $readerSid=(Get-LocalUser -Name $names[1]).SID.Value
    $rogueSid=(Get-LocalUser -Name $names[2]).SID.Value
    $custodianSid=(Get-LocalUser -Name $names[3]).SID.Value
    Need ($writerSid -ne $readerSid -and $readerSid -ne $rogueSid -and $writerSid -ne $rogueSid -and $custodianSid -ne $writerSid) 'G9_SID_COLLISION'
    $summary['sids']=[ordered]@{writer=$writerSid;reader=$readerSid;rogue=$rogueSid;custodian=$custodianSid;admin=$who.User.Value}
    [IO.Directory]::CreateDirectory($root)|Out-Null
    & icacls.exe $root /inheritance:r | Out-Null;NativeOk 'REMOVE_DACL_INHERITANCE'
    $grants=@('*S-1-5-18:(OI)(CI)F','*S-1-5-32-544:(OI)(CI)F',
        ('*'+$writerSid+':(OI)(CI)M'),('*'+$readerSid+':(OI)(CI)RX'),('*'+$rogueSid+':(OI)(CI)RX'),('*'+$custodianSid+':(OI)(CI)RX'))
    & icacls.exe $root /grant:r $grants | Out-Null;NativeOk 'SET_DACL'
    [IO.Directory]::CreateDirectory($custodyDir)|Out-Null
    & icacls.exe $custodyDir /inheritance:r | Out-Null;NativeOk 'CUSTODY_REMOVE_INHERITANCE'
    $custodyAcl=@('*S-1-5-18:(OI)(CI)F','*S-1-5-32-544:(OI)(CI)F',('*'+$custodianSid+':(OI)(CI)M'))
    & icacls.exe $custodyDir /grant:r $custodyAcl | Out-Null;NativeOk 'CUSTODY_EXCLUSIVE_DACL'
    Copy-Item -LiteralPath $PayloadFile -Destination (Join-Path $root 'payload.bin') -ErrorAction Stop
    $dll=Join-Path $root 'G9IntegratedBroker.dll'
    $compile='Add-Type -Path "'+$source+'" -OutputAssembly "'+$dll+'" -ErrorAction Stop'
    & $psExe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command $compile
    NativeOk 'G9_CSHARP_COMPILE'
    Need ([IO.File]::Exists($dll)) 'G9_COMPILED_ASSEMBLY_MISSING'
    $f=As $null 'fixture' 'Fixture' '' '' '' '' 1
    $fixtureLog=Await $f 0
    Need ($fixtureLog -match 'G9_EPHEMERAL_TWO_ACTOR_FIXTURES=PASS') 'G9_ACTOR_FIXTURE_FAILED'
    $summary['actor_public_pins']=[ordered]@{
       founder=(Get-FileHash -LiteralPath (Join-Path $root 'founder.pub') -Algorithm SHA256).Hash.ToLowerInvariant();
       ario=(Get-FileHash -LiteralPath (Join-Path $root 'ario.pub') -Algorithm SHA256).Hash.ToLowerInvariant()}
    Need ($summary['actor_public_pins']['founder'] -ne $summary['actor_public_pins']['ario']) 'G9_ACTORS_NOT_DISTINCT'


    $custodian=As $actorCreds[3] 'custodian' 'Custodian' '' '' '' '' 3
    Start-Sleep -Milliseconds 700
    Need (-not $custodian.process.HasExited) 'G9_CUSTODIAN_EARLY_EXIT'
    $first=Pair 'normal' 'normal' 0 $actorCreds[1] $readerSid
    Need ($first.reply.StartsWith('SIGNED_')) 'G9_FIRST_SIGN_FAILED'
    $firstState=State 'normal'
    Need ($firstState.intent -and $firstState.native_enter -and $firstState.native_return -and $firstState.receipt) 'G9_FIRST_NATIVE_CALL_INCOMPLETE'
    $firstAuditor=Await (As $null 'public-audit-first' 'Verify' 'normal' '' '' '' 1) 0
    Need ($firstAuditor -match 'G9_SEPARATE_PUBLIC_RECEIPT_VERIFY=PASS') 'G9_FIRST_PUBLIC_AUDIT_FAILED'
    $oldPin=[IO.File]::ReadAllText((Join-Path $root 'normal/public-pin.sha256')).Trim()
    $observer=Join-Path $root 'observer'
    [IO.Directory]::CreateDirectory($observer)|Out-Null
    Copy-Item (Join-Path $root 'normal/receipt-public.txt') (Join-Path $observer 'first-receipt-public.txt')
    $oldSha=(Get-FileHash (Join-Path $observer 'first-receipt-public.txt') -Algorithm SHA256).Hash.ToLowerInvariant()
    $markers=@(Get-ChildItem $custodyDir -File -Filter '*.used')
    Need ($markers.Count -eq 1) 'G9_CUSTODIAN_DID_NOT_COMMIT'
    $marker=$markers[0].FullName
    $markerSha=(Get-FileHash $marker -Algorithm SHA256).Hash.ToLowerInvariant()
    $probe=Await (As $actorCreds[0] 'writer-direct-custody-probe' 'Probe' '' '' '' '' 1) 0
    Need ($probe -eq 'G9_WRITER_CUSTODY_WRITE_ACCESS_DENIED') 'G9_WRITER_BYPASSED_DACL'
    # Restore ALL G9 local spend/receipt evidence to pre-first-sign absence.
    foreach($n in @('use-intent.txt','native-enter.txt','native-return.txt','receipt-public.txt','public-pin.sha256')){
      Remove-Item -LiteralPath (Join-Path $root ('normal/'+$n)) -Force -ErrorAction Stop
    }
    $local=State 'normal'
    Need (-not $local.intent -and -not $local.native_enter -and -not $local.native_return -and -not $local.receipt) 'G9_ROLLBACK_INCOMPLETE'
    $denied=Pair 'normal' 'normal' 0 $actorCreds[1] $readerSid
    Need ($denied.reply -eq 'HOLD_EXTERNAL_SPENT') ('G9_REMOTE_FENCE_FAILED_'+$denied.reply)
    $blockedState=State 'normal'
    Need (-not $blockedState.intent -and -not $blockedState.native_enter -and -not $blockedState.native_return -and -not $blockedState.receipt) 'G9_FENCE_DID_NOT_PREVENT_CNG'
    Need ([IO.File]::Exists($marker)) 'G9_CUSTODY_MARKER_LOST'
    Need ((Get-FileHash $marker -Algorithm SHA256).Hash.ToLowerInvariant() -eq $markerSha) 'G9_CUSTODY_MARKER_CHANGED'
    $summary['results']['OS_SEPARATE_FLOOR']=[ordered]@{
      first_public_receipt_sha256=$oldSha;writer_direct_custody_write='ACCESS_DENIED';
      kept_custody_marker_sha256=$markerSha;local_rollback=$local;retry=$denied.reply;
      no_second_CNG_call=((-not $blockedState.native_enter) -and (-not $blockedState.native_return))}
    Write-Host 'G9_DIFFERENT_SID_CUSTODY_BLOCKED_LOCAL_ROLLBACK=PASS'
    # DELIBERATELY RED: common admin erases custodian marker too.
    Remove-Item -LiteralPath $marker -Force -ErrorAction Stop
    Need (-not [IO.File]::Exists($marker)) 'G9_COMMON_ADMIN_CANNOT_DELETE_REMOTE_MARKER'
    $unsafe=Pair 'normal' 'normal' 0 $actorCreds[1] $readerSid
    Need ($unsafe.reply.StartsWith('SIGNED_')) 'G9_EXPECTED_SHARED_ADMIN_RED_NOT_REPRODUCED'
    $secondState=State 'normal'
    Need ($secondState.intent -and $secondState.native_enter -and $secondState.native_return -and $secondState.receipt) 'G9_SECOND_SIGN_INCOMPLETE'
    $secondPin=[IO.File]::ReadAllText((Join-Path $root 'normal/public-pin.sha256')).Trim()
    Need ($oldPin -ceq $secondPin) 'G9_SIGNER_KEY_CHANGED_INSTEAD_OF_REUSED'
    $secondAudit=Await (As $null 'public-audit-second' 'Verify' 'normal' '' '' '' 1) 0
    Need ($secondAudit -match 'G9_SEPARATE_PUBLIC_RECEIPT_VERIFY=PASS') 'G9_SECOND_PUBLIC_AUDIT_FAILED'
    $secondSha=(Get-FileHash (Join-Path $root 'normal/receipt-public.txt') -Algorithm SHA256).Hash.ToLowerInvariant()
    $summary['results']['SHARED_ADMIN_RED']=[ordered]@{
      common_admin_erased_custody=$true; same_signed_request_repeated=$true;
      same_native_CNG_public_pin=($oldPin -ceq $secondPin);
      native_enter_observed_in_two_broker_processes=2;
      two_public_receipts_verified=$true;first_receipt_sha256=$oldSha;
      second_receipt_sha256=$secondSha;
      decision='RED_COMMON_ADMIN_CAN_RESIGN_AFTER_ERASING_ALL_LOCAL_USE_STATE'}
    Write-Host 'G9_SHARED_ADMIN_COHERENT_ROLLBACK=RED_RESIGN_REPRODUCED'
    $custodianLog=Await $custodian 0
    Need ($custodianLog -match 'G9_CUSTODIAN_PROCESSED_3') 'G9_CUSTODIAN_MISSING_REQUESTS'
    $responses=@($custodianLog -split [char]10)
    Need ((@($responses|Where-Object{$_ -match 'RESPONSE=G9_CUSTODY_GRANTED'})).Count -eq 2) 'G9_WRONG_GRANT_COUNT'
    Need ((@($responses|Where-Object{$_ -match 'RESPONSE=HOLD_EXTERNAL_SPENT'})).Count -eq 1) 'G9_WRONG_HOLD_COUNT'
    $summary['custody_trace']=$custodianLog
    $summary['custody_dacl']=@(& icacls.exe $custodyDir)

    $last=Await (As $actorCreds[0] 'delete-all-disposable-keys' 'Cleanup' '' '' '' '' 1) 0
    Need ($last -match 'G9_TEMP_CNG_KEYS_REMOVED=1') ('G9_DISPOSABLE_KEY_CLEANUP_WRONG_'+$last)
    $summary['keys_removed_readback']=$last
    $successful=$true;$outcome='PASS_DISTINCT_SID_FLOOR_WITH_EXPECTED_SHARED_ADMIN_RED';
    $summary['status']=$outcome
    Write-Host 'G9_REAL_NATIVE_CNG_ENTER_RETURN_PER_CASE=PASS'
    Write-Host 'G9_SYNTHETIC_NATIVE_SIGNER_INTEGRATION=PASS'
} catch {
    $summary['status']='HOLD'
    $summary['error']=$_.Exception.GetType().FullName+' '+$_.Exception.Message
    Write-Host ('G9_HOLD='+$summary['error'])
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
           # Archive only public synthetic custodian use marker, never real credentials.
           if([IO.Directory]::Exists($custodyDir)){ Copy-Item -LiteralPath $custodyDir -Destination (Join-Path $root 'custody-final-public-snapshot') -Recurse -Force }
          [IO.Compression.ZipFile]::CreateFromDirectory($root,$zipPath)
       }
    } catch { $cleanup=$false;Write-Host ('G9_EVIDENCE_CAPTURE_HOLD='+$_.Exception.Message) }
    if([IO.Directory]::Exists($root)){
       try{Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction Stop}catch{$cleanup=$false}
    }
    foreach($name in @($created)) {
      try{Remove-LocalUser -Name $name -ErrorAction Stop}catch{$cleanup=$false}
      if(Get-LocalUser -Name $name -ErrorAction SilentlyContinue){$cleanup=$false}
    }
    if([IO.Directory]::Exists($custodyDir)){
      try{Remove-Item -LiteralPath $custodyDir -Recurse -Force -ErrorAction Stop}catch{$cleanup=$false}
    }
    if([IO.Directory]::Exists($root) -or [IO.Directory]::Exists($custodyDir)){$cleanup=$false}
    $summary['cleanup_verified']=$cleanup
    $summary['final_verdict']=if($successful -and $cleanup){'PASS_SYNTHETIC_G9_EXPECTED_SHARED_ADMIN_RED'}else{'HOLD'}
    [IO.File]::WriteAllText($reportPath,(ConvertTo-Json -InputObject $summary -Depth 20)+[char]10,[Text.UTF8Encoding]::new($false))
    Write-Host ('G9_REPORT='+$reportPath)
    if([IO.File]::Exists($zipPath)){Write-Host ('G9_EVIDENCE='+$zipPath)}
    Write-Host ('G9_TEMP_USER_AND_JOURNAL_CLEANUP='+$(if($cleanup){'PASS'}else{'HOLD'}))
    Write-Host ('G9_VERDICT='+$summary['final_verdict'])
}
if($summary['final_verdict'] -ne 'PASS_SYNTHETIC_G9_EXPECTED_SHARED_ADMIN_RED'){exit 1}
exit 0
