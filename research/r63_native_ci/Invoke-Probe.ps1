# R63 research-only Windows GitHub runner probe. NO Ario signer, service, TPM, or host access.
$ErrorActionPreference = 'Stop'
if (-not $IsWindows -or $env:RUNNER_OS -ne 'Windows') { throw 'REFUSE_NONWINDOWS_OR_NONCI' }
if ($env:GITHUB_REPOSITORY -ne 'SepehrGhanbari/Ario') { throw 'REFUSE_UNEXPECTED_REPOSITORY' }
Write-Host 'RESEARCH_ONLY / DIRECT_CNG_PROBE_NOT_R63_BROKER / NO_REAL_KEYS'
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
public static class NativeCngProbe {
    [DllImport("ncrypt.dll", ExactSpelling=true, EntryPoint="NCryptSignHash")]
    public static extern int SignHash(
        SafeNCryptKeyHandle hKey,
        IntPtr paddingInfo,
        byte[] digest,
        int digestLength,
        byte[] signature,
        int signatureCapacity,
        out int signatureLength,
        int flags);
}
'@
$keyName = 'ARIO_R63_CI_DISPOSABLE_' + [Guid]::NewGuid().ToString('N')
$provider = [System.Security.Cryptography.CngProvider]::MicrosoftSoftwareKeyStorageProvider
$key = $null
$signer = $null
$verifier = $null
$entered = 0
$returned = 0
$deleted = $false
try {
    $p = [System.Security.Cryptography.CngKeyCreationParameters]::new()
    $p.Provider = $provider
    $p.ExportPolicy = [System.Security.Cryptography.CngExportPolicies]::None
    $p.KeyUsage = [System.Security.Cryptography.CngKeyUsages]::Signing
    $key = [System.Security.Cryptography.CngKey]::Create(
        [System.Security.Cryptography.CngAlgorithm]::ECDsaP256, $keyName, $p)
    $signer = [System.Security.Cryptography.ECDsaCng]::new($key)
    $publicOnly = $signer.ExportParameters($false)
    $verifier = [System.Security.Cryptography.ECDsa]::Create($publicOnly)
    $pubPin = [Convert]::ToHexString(
        [System.Security.Cryptography.SHA256]::HashData($verifier.ExportSubjectPublicKeyInfo()))
    $digest = [System.Security.Cryptography.SHA256]::HashData(
        [Text.Encoding]::UTF8.GetBytes('Ario R63 standalone CNG research-only fixed digest'))
    $signature = [byte[]]::new(64)
    $written = 0
    $entered += 1
    $nativeStatus = [NativeCngProbe]::SignHash($key.Handle,[IntPtr]::Zero,
        $digest,$digest.Length,$signature,$signature.Length,[ref]$written,0)
    $returned += 1
    if ($nativeStatus -ne 0) { throw ('NCryptSignHash NTSTATUS=' + $nativeStatus) }
    if ($written -ne 64) { throw ('UNEXPECTED_SIGNATURE_LENGTH=' + $written) }
    if (-not $verifier.VerifyHash($digest,$signature)) {
        throw 'INDEPENDENT_PUBLIC_VERIFIER_REJECTED'
    }
    $tampered = [byte[]]$digest.Clone()
    $tampered[0] = $tampered[0] -bxor 1
    if ($verifier.VerifyHash($tampered,$signature)) {
        throw 'MUTATED_DIGEST_WAS_ACCEPTED'
    }
    Write-Host 'DIRECT_NCRYPTSIGNHASH_PUBLIC_VERIFY_PASS'
    Write-Host ('NCRYPT_ENTER=' + $entered)
    Write-Host ('NCRYPT_RETURN=' + $returned)
    Write-Host ('PUBLIC_PIN_SHA256=' + $pubPin)
    Write-Host 'MUTATED_DIGEST_PUBLIC_VERIFY=REJECT'
    Write-Host 'R63_NATIVE_BROKER_CRASH_AND_RACE=NOT_EXECUTED'
} finally {
    if ($verifier) { $verifier.Dispose() }
    if ($signer) { $signer.Dispose() }
    if ($key) {
        try {
            $key.Delete()
            $deleted = -not [System.Security.Cryptography.CngKey]::Exists($keyName,$provider)
        } finally { $key.Dispose() }
    }
    Write-Host ('DISPOSABLE_TEST_KEY_ABSENT_AFTER_DELETE=' + $deleted)
}
if (-not $deleted) { throw 'TEST_KEY_CLEANUP_NOT_VERIFIED' }
if ($entered -ne 1 -or $returned -ne 1) { throw 'NATIVE_CALL_COUNT_MISMATCH' }
