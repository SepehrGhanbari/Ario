# R63 V11 experimental native CNG post-sign fault windows; ephemeral CI only.
# NO real Ario keys, ACL or services, no signer/witness changes.
param([Parameter(Mandatory)][ValidateSet('AfterSignBeforeReceipt','AfterReceiptBeforeAck')][string]$Scenario,
      [Parameter(Mandatory)][string]$Root)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if (-not $IsWindows -or $env:RUNNER_OS -ne 'Windows' -or
    $env:GITHUB_REPOSITORY -ne 'SepehrGhanbari/Ario') { throw 'REFUSE_NON_CI_ENVIRONMENT' }
$rootPath=[IO.Path]::GetFullPath($Root)
$runnerTemp=[IO.Path]::GetFullPath($env:RUNNER_TEMP).TrimEnd('\','/')
if (-not $rootPath.StartsWith($runnerTemp+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {throw 'REFUSE_NON_EPHEMERAL_ROOT'}
$payloadPath=Join-Path $rootPath 'payload.bin'
$receiptPath=Join-Path $rootPath 'receipt-public.json'
$namePath=Join-Path $rootPath 'temporary-key-name.txt'
$pinPath=Join-Path $rootPath 'expected-public-pin.sha256'
$intentPath=Join-Path $rootPath 'use-entered.json'
$returnPath=Join-Path $rootPath 'use-returned.json'
if (-not [IO.File]::Exists($payloadPath)) {throw 'MISSING_SYNTHETIC_PAYLOAD'}
foreach ($item in @($receiptPath,$namePath,$pinPath,$intentPath,$returnPath)){
    if ([IO.File]::Exists($item)){throw ('REFUSE_EXISTING_OUTPUT '+$item)}
}
$payload=[IO.File]::ReadAllBytes($payloadPath)
if ($payload.Length -lt 64 -or $payload.Length -gt 8192){throw 'BAD_SYNTHETIC_PAYLOAD_SIZE'}
$hash=[Security.Cryptography.SHA256]::HashData($payload)
function WriteNewFsync([string]$P,[string]$S){
    $bytes=[Text.Encoding]::UTF8.GetBytes($S)
    $f=[IO.FileStream]::new($P,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{$f.Write($bytes,0,$bytes.Length);$f.Flush($true)}finally{$f.Dispose()}
}
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
public static class R63V11DisposableNCrypt {
 [DllImport("ncrypt.dll", ExactSpelling=true, EntryPoint="NCryptSignHash")]
 public static extern int SignHash(SafeNCryptKeyHandle key,IntPtr padding,
     byte[] hash,int hashLen,byte[] sig,int capacity,out int written,int flags);
}
'@
$provider=[Security.Cryptography.CngProvider]::MicrosoftSoftwareKeyStorageProvider
$name='ARIO_R63_CI_ONLY_'+[Guid]::NewGuid().ToString('N')
$key=$null;$signer=$null;$entered=0;$returned=0;$deleted=$false
try{
    $parameters=[Security.Cryptography.CngKeyCreationParameters]::new()
    $parameters.Provider=$provider
    $parameters.ExportPolicy=[Security.Cryptography.CngExportPolicies]::None
    $parameters.KeyUsage=[Security.Cryptography.CngKeyUsages]::Signing
    $key=[Security.Cryptography.CngKey]::Create([Security.Cryptography.CngAlgorithm]::ECDsaP256,$name,$parameters)
    $signer=[Security.Cryptography.ECDsaCng]::new($key)
    $publicSpki=$signer.ExportSubjectPublicKeyInfo()
    $pubPin=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($publicSpki)).ToLowerInvariant()
    WriteNewFsync $namePath ($name+[char]10)
    WriteNewFsync $pinPath ($pubPin+[char]10)
    $intent=[ordered]@{
        mode='R63_V11_SYNTHETIC_SIGN_USE_INTENT';scenario=$Scenario
        payload_sha256=[Convert]::ToHexString($hash).ToLowerInvariant()
        pid=$PID; target='DISPOSABLE_P256_KEY_ONLY'
    }
    WriteNewFsync $intentPath ((ConvertTo-Json -InputObject $intent -Compress)+[char]10)
    $sig=[byte[]]::new(64);$written=0
    $entered++
    $status=[R63V11DisposableNCrypt]::SignHash($key.Handle,[IntPtr]::Zero,
        $hash,$hash.Length,$sig,$sig.Length,[ref]$written,0)
    $returned++
    if ($status -ne 0 -or $written -ne 64){throw ('BAD_NATIVE_SIGN_'+$status)}
    $verifier=[Security.Cryptography.ECDsa]::Create()
    try{
        $read=0
        $verifier.ImportSubjectPublicKeyInfo($publicSpki,[ref]$read)
        if ($read -ne $publicSpki.Length -or -not $verifier.VerifyHash($hash,$sig)){
            throw 'PRODUCER_PUBLIC_VERIFY_FAILED'
        }
    }finally{$verifier.Dispose()}
    $done=[ordered]@{
        mode='R63_V11_SYNTHETIC_SIGN_USE_RETURNED';scenario=$Scenario
        enter=$entered;returned=$returned;ntstatus=$status;pid=$PID
    }
    WriteNewFsync $returnPath ((ConvertTo-Json -InputObject $done -Compress)+[char]10)
    if ($Scenario -eq 'AfterReceiptBeforeAck'){
        $receipt=[ordered]@{
            version='R63_CI_SELF_PINNED_PUBLIC_RECEIPT_V1'
            payload_sha256=[Convert]::ToHexString($hash).ToLowerInvariant()
            public_spki_b64=[Convert]::ToBase64String($publicSpki)
            public_pin_sha256=$pubPin
            signature_p1363_b64=[Convert]::ToBase64String($sig)
        }
        WriteNewFsync $receiptPath ((ConvertTo-Json -InputObject $receipt -Compress)+[char]10)
    }
}finally{
    if ($signer){$signer.Dispose()}
    if ($key){
        try{$key.Delete();$deleted=-not [Security.Cryptography.CngKey]::Exists($name,$provider)}
        finally{$key.Dispose()}
    }
}
if (-not $deleted -or $entered -ne 1 -or $returned -ne 1){throw 'CNG_OR_KEY_DELETION_UNVERIFIED'}
Write-Host ('SCENARIO='+$Scenario)
Write-Host ('CNG_ENTER='+$entered)
Write-Host ('CNG_RETURN='+$returned)
Write-Host ('KEY_ABSENT_AFTER_DELETE='+$deleted)
Write-Host ('RECEIPT_PRESENT='+[IO.File]::Exists($receiptPath))
Write-Host 'FORCED_POSTSIGN_PROCESS_EXIT_AFTER_KEY_CLEANUP=73'
Write-Host 'NATIVE_V9_BROKER=NOT_EXECUTED'
[Console]::Out.Flush()
# This exits after key cleanup; NOT a mid-NCrypt, power-loss, or V9 witness crash.
[Environment]::Exit(73)
