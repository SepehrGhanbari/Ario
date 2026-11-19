# R63 G2 — two short-lived, non-admin Windows SID identities on CI.
# No real Ario signer, no source journaling, no production ACL or host changes.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $IsWindows -or $env:RUNNER_OS -ne 'Windows' -or
    $env:GITHUB_REPOSITORY -ne 'SepehrGhanbari/Ario' -or
    $env:GITHUB_ACTIONS -ne 'true') { throw 'REFUSE_OUTSIDE_HOSTED_WINDOWS_GITHUB_CI' }
$me=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=[Security.Principal.WindowsPrincipal]::new($me)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'CI_RUNNER_NOT_ELEVATED_G2_CANNOT_CREATE_SYNTHETIC_USERS'
}
$id=[Guid]::NewGuid().ToString('N').Substring(0,7)
$writer='R63G2W'+$id
$reader='R63G2R'+$id
$root=Join-Path $env:PUBLIC ('ArioR63G2CI_'+$id)
$journal=Join-Path $root 'journal'
$probePath=Join-Path $root 'Invoke-RestrictedTokenProbe.ps1'
$reportPath=Join-Path $env:GITHUB_WORKSPACE 'r63-g2-acl-report.json'
$writerCreated=$false
$readerCreated=$false
if ((Test-Path -LiteralPath $root) -or (Test-Path -LiteralPath $reportPath)) {
    throw 'REFUSE_OVERWRITE_SYNTHETIC_G2_DIRECTORY_OR_REPORT'
}
if (-not $root.StartsWith([IO.Path]::GetFullPath($env:PUBLIC).TrimEnd('\')+'\',
    [StringComparison]::OrdinalIgnoreCase)) { throw 'UNEXPECTED_G2_ROOT' }
$writerOutput=Join-Path $env:RUNNER_TEMP ('r63g2-'+$id+'-writer.out')
$readerOutput=Join-Path $env:RUNNER_TEMP ('r63g2-'+$id+'-reader.out')
$writerError=Join-Path $env:RUNNER_TEMP ('r63g2-'+$id+'-writer.err')
$readerError=Join-Path $env:RUNNER_TEMP ('r63g2-'+$id+'-reader.err')
function MustSuccess([string]$what) {
    if ($LASTEXITCODE -ne 0) { throw ('G2_OS_CALL_FAILED_'+$what+'_EXIT_'+$LASTEXITCODE) }
}
function MakeCredential([string]$account) {
    $password=[Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(48))
    $secure=ConvertTo-SecureString -String $password -AsPlainText -Force
    return [PSCredential]::new(('.\'+$account),$secure)
}
function LaunchProbe($credential,[string]$mode,[string]$output,[string]$err) {
    $exe=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $args='-NoLogo -NoProfile -NonInteractive -File "'+$probePath+'" -Mode '+$mode+' -Root "'+$journal+'"'
    $params=@{FilePath=$exe;ArgumentList=$args;Credential=$credential;Wait=$true;PassThru=$true;WindowStyle='Hidden';RedirectStandardOutput=$output;RedirectStandardError=$err}
    $p=Start-Process @params
    if ($p.ExitCode -ne 0) {
        $detail=if (Test-Path $err) { (Get-Content $err -Raw) } else { '<no stderr file>' }
        throw ('G2_'+$mode+'_CHILD_EXIT_'+$p.ExitCode+' '+$detail)
    }
    return ConvertFrom-Json -InputObject (Get-Content -LiteralPath $output -Raw)
}
try {
    $writerCred=MakeCredential $writer
    $readerCred=MakeCredential $reader
    New-LocalUser -Name $writer -Password $writerCred.Password -PasswordNeverExpires -AccountNeverExpires -Description 'R63 G2 ephemeral CI authorized writer' | Out-Null
    $writerCreated=$true
    New-LocalUser -Name $reader -Password $readerCred.Password -PasswordNeverExpires -AccountNeverExpires -Description 'R63 G2 ephemeral CI restricted reader' | Out-Null
    $readerCreated=$true
    $writerSid=(Get-LocalUser -Name $writer).SID.Value
    $readerSid=(Get-LocalUser -Name $reader).SID.Value
    if ($writerSid -eq $readerSid) { throw 'SAME_WINDOWS_SID_FOR_BOTH_USERS' }
    New-Item -ItemType Directory -Path $root -ErrorAction Stop | Out-Null

    # Only these four exact SIDs remain after inheritance is removed:
    # SYSTEM, built-in Administrators, disposable writer M, reader RX.
    & icacls.exe $root /inheritance:r | Out-Null
    MustSuccess 'REMOVE_INHERITANCE'
    $grants=@('*S-1-5-18:(OI)(CI)F','*S-1-5-32-544:(OI)(CI)F',
              ('*'+$writerSid+':(OI)(CI)M'),('*'+$readerSid+':(OI)(CI)RX'))
    & icacls.exe $root /grant:r $grants | Out-Null
    MustSuccess 'EXPLICIT_SID_DACL'
    New-Item -ItemType Directory -Path $journal | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Invoke-RestrictedTokenProbe.ps1') -Destination $probePath
    $v1=Join-Path $journal 'v1.jsonl'
    $v2=Join-Path $journal 'v2.jsonl'
    $flag=Join-Path $journal 'uncertain.flag'
    [IO.File]::WriteAllText($v1, "G2_ACL_ONLY_DISPOSABLE_V1"+[char]10)
    [IO.File]::WriteAllText($v2, "G2_ACL_ONLY_DISPOSABLE_V2"+[char]10)
    [IO.File]::WriteAllText($flag, "G2_ACL_ONLY_DISPOSABLE_FLAG"+[char]10)

    $aclBefore=& icacls.exe $journal $v1 $v2 $flag
    MustSuccess 'READBACK_DACLS'
    $writerResult=LaunchProbe $writerCred 'AuthorizedWriter' $writerOutput $writerError
    if ($writerResult.current_token_sid -ne $writerSid -or $writerResult.is_admin) {
        throw 'AUTHORIZED_WRITER_TOKEN_NOT_DISTINCT_UNPRIVILEGED'
    }
    foreach ($action in @('append_v1','append_v2','create_sibling')) {
        if ($writerResult.operations.$action -ne 'ALLOWED') {
            throw ('AUTHORIZED_WRITER_NOT_ALLOWED_'+$action)
        }
    }
    foreach ($path in @($v1,$v2)) {
        if (-not ([IO.File]::ReadAllText($path).Contains('AUTHORIZED_WRITER_TEST_ONLY'))) {
            throw 'WRITER_DID_NOT_WRITE_ACTUAL_JOURNAL_FIXTURE'
        }
    }
    $before=[ordered]@{}
    foreach ($path in @($v1,$v2,$flag)) {
        $before[[IO.Path]::GetFileName($path)]=(Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
    }
    $readerResult=LaunchProbe $readerCred 'RestrictedReader' $readerOutput $readerError
    if ($readerResult.current_token_sid -ne $readerSid -or $readerResult.is_admin) {
        throw 'RESTRICTED_READER_TOKEN_NOT_DISTINCT_UNPRIVILEGED'
    }
    foreach ($action in @('append_v1','append_v2','overwrite_v1','delete_flag','create_sibling')) {
        if ($readerResult.operations.$action -ne 'ACCESS_DENIED') {
            throw ('DIRECT_UNCOOPERATIVE_WRITE_NOT_DENIED_'+$action+'_'+$readerResult.operations.$action)
        }
    }
    $after=[ordered]@{}
    foreach ($path in @($v1,$v2,$flag)) {
        $after[[IO.Path]::GetFileName($path)]=(Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
    }
    foreach ($key in $before.Keys) {
        if ($after[$key] -ne $before[$key]) {
            throw ('RESTRICTED_DIRECT_WRITER_CHANGED_PROTECTED_BYTES_'+$key)
        }
    }
    if (-not (Test-Path $flag) -or (Test-Path (Join-Path $journal 'unauthorized-new-file.txt'))) {
        throw 'FLAG_OR_DIRECTORY_CHILD_DID_NOT_REMAIN_PROTECTED'
    }
    $report=[ordered]@{
        experiment='R63_G2_NATIVE_WINDOWS_ACL_DIRECT_WRITER_DENIAL'
        scope='GITHUB_HOSTED_EPHEMERAL_CI_ONLY'
        writer_sid=$writerSid;reader_sid=$readerSid
        writer_is_admin=$writerResult.is_admin;reader_is_admin=$readerResult.is_admin
        distinct_token_sids=($writerSid -ne $readerSid)
        dacl_snapshot=@($aclBefore)
        authorized_writer_operations=$writerResult.operations
        restricted_direct_operations=$readerResult.operations
        journals_unchanged_after_restricted_attempts=$true
        sha_before=$before;sha_after=$after
        acl_only_fixture_not_v9_journal_chain=$true
        real_v9_witness='NOT_EXECUTED'
        real_signer_or_key='NOT_TOUCHED'
        same_admin_rollback_defense='NOT_ESTABLISHED'
        source_control='RESEARCH_ONLY_HOLD_NO_MERGE'
    }
    [IO.File]::WriteAllText($reportPath,(ConvertTo-Json -InputObject $report -Depth 8)+[char]10,[Text.UTF8Encoding]::new($false))
    Write-Host 'G2_DISTINCT_WINDOWS_SIDS=PASS'
    Write-Host 'G2_NONADMIN_WRITER_ALLOW=PASS'
    Write-Host 'G2_NONADMIN_READER_DIRECT_WRITE_DENIED=5/5'
    Write-Host 'G2_V1_V2_FLAG_HASHES_UNCHANGED_AFTER_DENIAL=PASS'
    Write-Host 'G2_REAL_V9_SERVICE=NOT_EXECUTED'
    Write-Host 'G2_INDEPENDENT_ADMIN_CUSTODY=NOT_ESTABLISHED'
} finally {
    if (Test-Path -LiteralPath $root) {
        try { Remove-Item -LiteralPath $root -Force -Recurse -ErrorAction Stop }
        catch { Write-Warning ('EPHEMERAL_ROOT_CLEANUP_ERROR_'+$_.Exception.Message) }
    }
    if ($readerCreated) {
        try { Remove-LocalUser -Name $reader -ErrorAction Stop }
        catch { Write-Warning 'DISPOSABLE_READER_ACCOUNT_CLEANUP_ERROR' }
    }
    if ($writerCreated) {
        try { Remove-LocalUser -Name $writer -ErrorAction Stop }
        catch { Write-Warning 'DISPOSABLE_WRITER_ACCOUNT_CLEANUP_ERROR' }
    }
}
