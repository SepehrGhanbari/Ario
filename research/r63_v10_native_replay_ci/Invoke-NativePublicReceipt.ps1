# Windows GitHub-hosted CI only: ephemeral native CNG receipt producer/public-only replay.
param([Parameter(Mandatory)][ValidateSet('Produce','Verify','Negative')][string]$Mode,
      [Parameter(Mandatory)][string]$Root)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if (-not $IsWindows -or $env:RUNNER_OS -ne 'Windows' -or $env:GITHUB_REPOSITORY -ne 'SepehrGhanbari/Ario') { throw 'UNAUTHORIZED_ENVIRONMENT' }
$rootPath=[IO.Path]::GetFullPath($Root)
$runnerTemp=[IO.Path]::GetFullPath($env:RUNNER_TEMP).TrimEnd('\','/')
if (-not $rootPath.StartsWith($runnerTemp+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'NON_EPHEMERAL_PATH' }
$payloadFile=Join-Path $rootPath 'payload.bin'
$receiptFile=Join-Path $rootPath 'receipt-public.json'
$keyMarker=Join-Path $rootPath 'temporary-key-name.txt'
if (-not (Test-Path -LiteralPath $payloadFile -PathType Leaf)) { throw 'NO_PAYLOAD' }
$payload=[IO.File]::ReadAllBytes($payloadFile)
if ($payload.Length -lt 64 -or $payload.Length -gt 8192) { throw 'PAYLOAD_OUT_OF_BOUNDS' }
$hash=[Security.Cryptography.SHA256]::HashData($payload)
$provider=[Security.Cryptography.CngProvider]::MicrosoftSoftwareKeyStorageProvider

if ($Mode -eq 'Produce') {
    if (Test-Path $receiptFile) { throw 'RECEIPT_ALREADY_EXISTS' }
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
public static class R63EphemeralSign {
    [DllImport("ncrypt.dll", ExactSpelling=true, EntryPoint="NCryptSignHash")]
    public static extern int SignHash(
        SafeNCryptKeyHandle key, IntPtr padding,
        byte[] hash, int hashLength, byte[] sig, int sigSize,
        out int written, int flags);
}
'@
    $name='ARIO_R63_CI_ONLY_'+[Guid]::NewGuid().ToString('N')
    $key=$null; $signer=$null; $entered=0; $returned=0; $absent=$false
    try {
        $p=[Security.Cryptography.CngKeyCreationParameters]::new()
        $p.Provider=$provider
        $p.ExportPolicy=[Security.Cryptography.CngExportPolicies]::None
        $p.KeyUsage=[Security.Cryptography.CngKeyUsages]::Signing
        $key=[Security.Cryptography.CngKey]::Create([Security.Cryptography.CngAlgorithm]::ECDsaP256,$name,$p)
        $signer=[Security.Cryptography.ECDsaCng]::new($key)
        $spki=$signer.ExportSubjectPublicKeyInfo()
        $signature=[byte[]]::new(64)
        $written=0
        $entered++
        $status=[R63EphemeralSign]::SignHash($key.Handle,[IntPtr]::Zero,$hash,$hash.Length,$signature,$signature.Length,[ref]$written,0)
        $returned++
        if ($status -ne 0 -or $written -ne 64) { throw ('BAD_CNG_STATUS_'+$status) }
        $public=[Security.Cryptography.ECDsa]::Create()
        try {
            $consumed=0
            $public.ImportSubjectPublicKeyInfo($spki,[ref]$consumed)
            if ($consumed -ne $spki.Length -or -not $public.VerifyHash($hash,$signature)) { throw 'PUBLIC_VERIFY_FAILED' }
        } finally { $public.Dispose() }
        $record=[ordered]@{
            version='R63_CI_SELF_PINNED_PUBLIC_RECEIPT_V1'
            payload_sha256=[Convert]::ToHexString($hash).ToLowerInvariant()
            public_spki_b64=[Convert]::ToBase64String($spki)
            public_pin_sha256=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($spki)).ToLowerInvariant()
            signature_p1363_b64=[Convert]::ToBase64String($signature)
        }
        $json=ConvertTo-Json -InputObject $record -Depth 3 -Compress
        [IO.File]::WriteAllText($receiptFile,$json+[char]10,[Text.UTF8Encoding]::new($false))
        [IO.File]::WriteAllText($keyMarker,$name+[char]10,[Text.UTF8Encoding]::new($false))
        Write-Host ('NCRYPT_ENTER='+$entered)
        Write-Host ('NCRYPT_RETURN='+$returned)
        Write-Host 'NATIVE_RECEIPT_PERSISTED=YES'
    } finally {
        if ($signer) { $signer.Dispose() }
        if ($key) {
            try {
                $key.Delete()
                $absent=-not [Security.Cryptography.CngKey]::Exists($name,$provider)
            } finally { $key.Dispose() }
        }
        Write-Host ('DISPOSABLE_KEY_ABSENT_AFTER_DELETE='+$absent)
    }
    if ($entered -ne 1 -or $returned -ne 1 -or -not $absent) { throw 'NATIVE_USE_OR_CLEANUP_INCOMPLETE' }
    Write-Host 'NATIVE_CNG_PRODUCER_PASS_RESEARCH_ONLY'
    return
}

if (-not (Test-Path $receiptFile) -or -not (Test-Path $keyMarker)) { throw 'RECEIPT_OR_KEY_MARKER_MISSING' }
$keyName=[IO.File]::ReadAllText($keyMarker).Trim()
if (-not $keyName.StartsWith('ARIO_R63_CI_ONLY_',[StringComparison]::Ordinal)) { throw 'INVALID_TEST_KEY_NAME' }
if ([Security.Cryptography.CngKey]::Exists($keyName,$provider)) { throw 'TEST_KEY_STILL_EXISTS' }
$json=[IO.File]::ReadAllText($receiptFile,[Text.Encoding]::UTF8)
$r=ConvertFrom-Json -InputObject $json
if ($r.version -ne 'R63_CI_SELF_PINNED_PUBLIC_RECEIPT_V1') { throw 'BAD_VERSION' }
if ($r.payload_sha256 -cne [Convert]::ToHexString($hash).ToLowerInvariant()) { throw 'WRONG_PAYLOAD_HASH' }
$spki=[Convert]::FromBase64String([string]$r.public_spki_b64)
$sig=[Convert]::FromBase64String([string]$r.signature_p1363_b64)
$pin=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($spki)).ToLowerInvariant()
if ($pin -cne $r.public_pin_sha256 -or $sig.Length -ne 64) { throw 'BAD_PIN_OR_SIG_SIZE' }
$public=[Security.Cryptography.ECDsa]::Create()
try {
    $read=0
    $public.ImportSubjectPublicKeyInfo($spki,[ref]$read)
    if ($read -ne $spki.Length -or -not $public.VerifyHash($hash,$sig)) { throw 'VERIFIER_REJECTED_VALID_RECEIPT' }
    if ($Mode -eq 'Negative') {
        $badHash=[byte[]]$hash.Clone(); $badHash[0]=$badHash[0] -bxor 1
        $badSig=[byte[]]$sig.Clone(); $badSig[0]=$badSig[0] -bxor 1
        if ($public.VerifyHash($badHash,$sig)) { throw 'MUTATED_HASH_ACCEPTED' }
        if ($public.VerifyHash($hash,$badSig)) { throw 'MUTATED_SIG_ACCEPTED' }
        Write-Host 'NEGATIVE_MUTATED_HASH_AND_SIG_REJECTED=YES'
    } else { Write-Host 'SEPARATE_PUBLIC_ONLY_VERIFIER_PASS' }
    $receiptBytes=[IO.File]::ReadAllBytes($receiptFile)
    Write-Host ('PERSISTED_RECEIPT_SHA256='+[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($receiptBytes)).ToLowerInvariant())
    Write-Host 'NCRYPT_IN_VERIFIER_PATH=NOT_INVOKED_IN_SOURCE'
    Write-Host 'INDEPENDENT_CUSTODY=NOT_ESTABLISHED'
    Write-Host 'NATIVE_V9_SIGNER=NOT_EXECUTED'
} finally { $public.Dispose() }
