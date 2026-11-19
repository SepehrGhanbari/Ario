#Requires -Version 5.1
<#
R6-B Windows portable, SYNTHETIC ONLY. No Python modules, no admin rights.
No real Ario keys, no signer, no trusted time, no memory or trust effects.
Makes an RSA-2048/SHA-256 test receipt on the PC, checks it on the laptop.
A shared admin controls both machines; all results have authority=false.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('Make','Inspect','Revoke','Status')]
    [string] $Mode,
    [string] $Root = (Join-Path $env:LOCALAPPDATA 'Ario-R6-Windows-Test-v1'),
    [string] $BundleZip = '',
    [int] $IssuedOffsetSeconds = 0
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProfileId = 'ARIO-R6-WINDOWS-SYNTHETIC-1'
$Domain = 'ARIO-R6-WINDOWS-RECEIPT-SYNTHETIC-1|'
$Zero = ('0' * 64)
$MaxRecords = 100
$MaxAge = 300

function To-Json($obj) {
    return (ConvertTo-Json -InputObject $obj -Compress -Depth 8)
}
function To-Bytes([string] $text) {
    return ,([System.Text.Encoding]::UTF8.GetBytes($text))
}
function Hash-Bytes([byte[]] $raw) {
    $hasher = [System.Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($hasher.ComputeHash($raw)).Replace('-','').ToLowerInvariant()) }
    finally { $hasher.Dispose() }
}
function Hash-Text([string] $text) { return (Hash-Bytes (To-Bytes $text)) }
function New-Rsa {
    $csp = [System.Security.Cryptography.CspParameters]::new(24)
    $csp.ProviderName = 'Microsoft Enhanced RSA and AES Cryptographic Provider'
    $rsa = [System.Security.Cryptography.RSACryptoServiceProvider]::new(2048, $csp)
    $rsa.PersistKeyInCsp = $false
    return $rsa
}
function New-Report([string] $code, [string] $head=$Zero, [int] $count=0, [string] $pubsha='', [string] $bundle='') {
    return [ordered]@{
        profile=$ProfileId; reason_code=$code; record_count=$count
        head_sha256=$head; public_key_sha256=$pubsha; bundle_path=$bundle
        os_separation='TWO_HOSTS_NOT_YET_MEASURED'
        administrative_independence='NOT_ESTABLISHED'
        public_key_source='SELF_PINNED_SYNTHETIC'
        trusted_clock='NOT_ESTABLISHED'
        execution_reality='NOT_ESTABLISHED'
        external_floor='NOT_ESTABLISHED'
        evidence_admission_allowed=$false
        memory_write_allowed=$false
        signing_authority_allowed=$false
        trust_activation_allowed=$false
    }
}
function Ensure-LabRoot {
    $full = [IO.Path]::GetFullPath($Root)
    if ($full -eq [IO.Path]::GetPathRoot($full) -or $full.Length -lt 12) { throw 'REFUSE_UNSAFE_ROOT' }
    if ([IO.Directory]::Exists($full)) {
        $attrs = [IO.File]::GetAttributes($full)
        if (($attrs -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'REFUSE_JUNCTION_OR_LINK_ROOT' }
        if (-not [IO.File]::Exists((Join-Path $full '.r6-synthetic-only'))) {
            $existing = @([IO.Directory]::GetFileSystemEntries($full))
            if ($existing.Count -gt 0) { throw 'REFUSE_NONEMPTY_UNMARKED_ROOT' }
        }
    } else {
        [IO.Directory]::CreateDirectory($full) | Out-Null
    }
    $marker = Join-Path $full '.r6-synthetic-only'
    if (-not [IO.File]::Exists($marker)) { [IO.File]::WriteAllText($marker, 'R6_TEST_ONLY', [Text.Encoding]::ASCII) }
    return $full
}
function Safe-Text([string] $path, [int] $max=16384) {
    $info = [IO.FileInfo]::new($path)
    if (-not $info.Exists -or $info.Length -gt $max -or $info.Length -le 0) { throw 'INVALID_FILE_LENGTH' }
    return [IO.File]::ReadAllText($path, [Text.Encoding]::UTF8)
}
function Make-Payload([string] $keySha, [string] $nonce, [long] $epoch) {
    return [ordered]@{
        profile=$ProfileId
        key_id=$keySha
        nonce=$nonce
        issued_epoch=$epoch
        request_sha256=('a' * 64)
        synthetic_result_sha256=('b' * 64)
        role='SYNTHETIC_TEST_ONLY'
    }
}
function New-Bundle([string] $lab) {
    if ($IssuedOffsetSeconds -lt -86400 -or $IssuedOffsetSeconds -gt 3600) { throw 'INVALID_TEST_OFFSET' }
    $private = Join-Path $lab 'executor-private-test-only.xml'
    $public = Join-Path $lab 'executor-public-test-only.xml'
    if ([IO.File]::Exists($private) -ne [IO.File]::Exists($public)) { throw 'PARTIAL_TEST_KEYPAIR' }
    if (-not [IO.File]::Exists($private)) {
        $rsa = New-Rsa
        try {
            $pri = $rsa.ToXmlString($true)
            $pub = $rsa.ToXmlString($false)
        } finally { $rsa.Dispose() }
        $utf8 = [System.Text.UTF8Encoding]::new($false)
        $pstream = [IO.File]::Open($private, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        try {
            $bytes = $utf8.GetBytes($pri)
            $pstream.Write($bytes, 0, $bytes.Length)
            $pstream.Flush($true)
        } finally { $pstream.Dispose() }
        [IO.File]::WriteAllText($public, $pub, $utf8)
    }
    $pri = Safe-Text $private 8192
    $pub = Safe-Text $public 2048
    $rsa = New-Rsa
    try {
        $rsa.FromXmlString($pri)
        if ($rsa.ToXmlString($false) -cne $pub) { throw 'PUBLIC_PRIVATE_TEST_KEY_MISMATCH' }
        $pubsha = Hash-Text $pub
        $nonce = [guid]::NewGuid().ToString('N')
        $epoch = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() + $IssuedOffsetSeconds
        $payload = Make-Payload $pubsha $nonce $epoch
        $signed = To-Bytes ($Domain + (To-Json $payload))
        $sig = [Convert]::ToBase64String($rsa.SignData($signed, 'SHA256'))
    } finally { $rsa.Dispose() }
    $out = Join-Path $lab 'public-handoff'
    [IO.Directory]::CreateDirectory($out) | Out-Null
    $pubout = Join-Path $out 'r6-public.xml'
    $recout = Join-Path $out 'r6-receipt.json'
    [IO.File]::WriteAllText($pubout, $pub, [System.Text.UTF8Encoding]::new($false))
    $receipt = [ordered]@{payload=$payload; signature_base64=$sig}
    [IO.File]::WriteAllText($recout, (To-Json $receipt), [System.Text.UTF8Encoding]::new($false))
    $bundle = Join-Path $lab ('R6-public-handoff-' + $nonce + '.zip')
    Compress-Archive -Path $pubout,$recout -DestinationPath $bundle -CompressionLevel Optimal
    return (New-Report 'SYNTHETIC_BUNDLE_CREATED' $Zero 0 $pubsha $bundle)
}
function Read-ZipEntry($zip,[string]$name,[int]$max) {
    $entry = $zip.GetEntry($name)
    if ($null -eq $entry -or $entry.Length -le 0 -or $entry.Length -gt $max) { throw 'INVALID_PUBLIC_BUNDLE_ENTRY' }
    $stream = $entry.Open()
    try {
        $mem = New-Object IO.MemoryStream
        try {
            $buf = New-Object byte[] 1024
            while (($got = $stream.Read($buf,0,$buf.Length)) -gt 0) {
                if ($mem.Length + $got -gt $max) { throw 'BUNDLE_UNCOMPRESSED_TOO_LARGE' }
                $mem.Write($buf,0,$got)
            }
            return [Text.Encoding]::UTF8.GetString($mem.ToArray())
        } finally { $mem.Dispose() }
    } finally { $stream.Dispose() }
}
function Decode-Bundle([string] $zipfile) {
    if (-not [IO.File]::Exists($zipfile)) { throw 'BUNDLE_NOT_FOUND' }
    $fi = [IO.FileInfo]::new($zipfile)
    if ($fi.Length -gt 32768 -or $fi.Length -le 0) { throw 'INVALID_BUNDLE_SIZE' }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead($zipfile)
    try {
        if ($zip.Entries.Count -ne 2) { throw 'BUNDLE_MUST_HAVE_TWO_PUBLIC_FILES' }
        foreach ($entry in $zip.Entries) {
            if ($entry.FullName -cne 'r6-public.xml' -and $entry.FullName -cne 'r6-receipt.json') {
                throw 'UNEXPECTED_BUNDLE_ENTRY'
            }
        }
        return @{ public=(Read-ZipEntry $zip 'r6-public.xml' 2048);
                  receipt=(Read-ZipEntry $zip 'r6-receipt.json' 4096) }
    } finally { $zip.Dispose() }
}
function Verify-Synthetic($bundle) {
    $pub = [string] $bundle.public
    # Canonical PUBLIC-only XML; reject injected synthetic private key material.
    if ($pub -cnotmatch '^<RSAKeyValue><Modulus>[A-Za-z0-9+/=]+</Modulus><Exponent>[A-Za-z0-9+/=]+</Exponent></RSAKeyValue>$') {
        throw 'REFUSE_NONPUBLIC_RSA_XML'
    }
    $pubsha = Hash-Text $pub
    $receipt = ConvertFrom-Json -InputObject $bundle.receipt
    if ($null -eq $receipt -or $null -eq $receipt.payload) { throw 'INVALID_RECEIPT_SHAPE' }
    $fieldNames = @($receipt.PSObject.Properties.Name)
    if ($fieldNames.Count -ne 2 -or -not ($fieldNames -contains 'payload') -or
        -not ($fieldNames -contains 'signature_base64')) { throw 'INVALID_RECEIPT_FIELDS' }
    $p = $receipt.payload
    $keys = @($p.PSObject.Properties.Name)
    $expected = @('profile','key_id','nonce','issued_epoch','request_sha256','synthetic_result_sha256','role')
    if ($keys.Count -ne $expected.Count) { throw 'INVALID_PAYLOAD_FIELDS' }
    foreach ($k in $expected) { if (-not ($keys -contains $k)) { throw 'INVALID_PAYLOAD_FIELDS' } }
    if ($p.profile -cne $ProfileId -or $p.role -cne 'SYNTHETIC_TEST_ONLY') { throw 'INVALID_SYNTHETIC_PROFILE' }
    if ($p.key_id -cne $pubsha) { throw 'UNPINNED_EXECUTOR_KEY' }
    if ($p.nonce -isnot [string] -or $p.nonce -cnotmatch '^[0-9a-f]{32}$') { throw 'INVALID_NONCE' }
    if ($p.issued_epoch -isnot [long] -and $p.issued_epoch -isnot [int]) { throw 'INVALID_EPOCH' }
    if ($p.request_sha256 -cne ('a' * 64) -or $p.synthetic_result_sha256 -cne ('b' * 64)) {
        throw 'INVALID_SYNTHETIC_DATA'
    }
    $rsa = New-Rsa
    try {
        $rsa.FromXmlString($pub)
        $normalized = Make-Payload $pubsha $p.nonce ([long] $p.issued_epoch)
        $signed = To-Bytes ($Domain + (To-Json $normalized))
        $sig = [Convert]::FromBase64String([string]$receipt.signature_base64)
        if (-not $rsa.VerifyData($signed, 'SHA256', $sig)) { throw 'INVALID_RECEIPT_SIGNATURE' }
    } finally { $rsa.Dispose() }
    $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    if ([Math]::Abs($now - [long]$p.issued_epoch) -gt $MaxAge) { throw 'CUSTODIAN_CLOCK_SKEW' }
    return @{ public=$pub; publicsha=$pubsha; nonce=[string]$p.nonce;
              receiptsha=(Hash-Text $bundle.receipt) }
}
function Read-History([string] $path) {
    $seen = New-Object 'System.Collections.Generic.HashSet[string]'
    $head = $Zero; $count = 0; $revoked = $false
    if ([IO.File]::Exists($path)) {
        $raw = Safe-Text $path 65536
        if (-not $raw.EndsWith([Environment]::NewLine)) { throw 'TRUNCATED_HISTORY' }
        $lines = @($raw.Split([string[]]@([Environment]::NewLine), [StringSplitOptions]::RemoveEmptyEntries))
        if ($lines.Count -gt $MaxRecords) { throw 'HISTORY_LIMIT' }
        foreach ($line in $lines) {
            $item = ConvertFrom-Json -InputObject $line
            if ($null -eq $item -or $null -eq $item.event) { throw 'INVALID_HISTORY' }
            $ev = $item.event
            if ($ev.index -ne ($count+1) -or $ev.previous_sha256 -cne $head) { throw 'HISTORY_CHAIN_GAP' }
            if ($ev.kind -cne 'SPENT' -and $ev.kind -cne 'REVOKED') { throw 'INVALID_HISTORY_KIND' }
            $fixed = [ordered]@{index=[int]$ev.index; previous_sha256=[string]$ev.previous_sha256;
                               kind=[string]$ev.kind; nonce=$ev.nonce; receipt_sha256=[string]$ev.receipt_sha256}
            $nextHead = Hash-Text ('ARIO-R6-WINDOWS-LEDGER-1|' + (To-Json $fixed))
            if ($item.head_sha256 -cne $nextHead) { throw 'HISTORY_DIGEST_MISMATCH' }
            if ($ev.kind -ceq 'REVOKED') {
                if ($revoked -or $null -ne $ev.nonce) { throw 'INVALID_REVOCATION_HISTORY' }
                $revoked = $true
            } else {
                if ($revoked -or $ev.nonce -isnot [string] -or -not $seen.Add($ev.nonce)) {
                    throw 'INVALID_NONCE_HISTORY'
                }
            }
            $head=$nextHead; $count++
        }
    }
    return @{head=$head;count=$count;nonces=$seen;revoked=$revoked}
}
function Append-History([string]$path,$st,[string]$kind,$nonce,[string]$receiptHash,[string]$publicSha='') {
    if ($st.count -ge $MaxRecords) { throw 'HISTORY_LIMIT' }
    $ev=[ordered]@{index=($st.count+1);previous_sha256=$st.head;kind=$kind;
                   nonce=$nonce;receipt_sha256=$receiptHash}
    $newhead = Hash-Text ('ARIO-R6-WINDOWS-LEDGER-1|' + (To-Json $ev))
    $record=To-Json ([ordered]@{event=$ev;head_sha256=$newhead})
    $bytes=To-Bytes ($record + [Environment]::NewLine)
    $file=[IO.File]::Open($path,[IO.FileMode]::Append,[IO.FileAccess]::Write,[IO.FileShare]::Read)
    try { $file.Write($bytes,0,$bytes.Length); $file.Flush($true) }
    finally { $file.Dispose() }
    return (New-Report $(if ($kind -eq 'REVOKED') {'SYNTHETIC_REVOKED'} else {'SYNTHETIC_RECEIPT_RECORDED'}) $newhead ($st.count+1) $publicSha)
}
function With-CustodianLock([string] $lab,[scriptblock] $operation) {
    $lockpath = Join-Path $lab 'C-research-lock'
    $lock = $null
    for ($attempt=0;$attempt -lt 30;$attempt++) {
        try {
            $lock=[IO.File]::Open($lockpath,[IO.FileMode]::OpenOrCreate,
                                 [IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
            break
        } catch [IO.IOException] { Start-Sleep -Milliseconds 100 }
    }
    if ($null -eq $lock) { throw 'C_LOCK_BUSY' }
    try { return (& $operation) }
    finally { $lock.Dispose() }
}

try {
    $lab = Ensure-LabRoot
    if ($Mode -eq 'Make') {
        $result=New-Bundle $lab
    } else {
        $publicPin = Join-Path $lab 'C-pinned-public-test-only.xml'
        $journal = Join-Path $lab 'C-synthetic-history.jsonl'
        $result=With-CustodianLock $lab {
            $st = Read-History $journal
            if ($Mode -eq 'Status') {
                New-Report 'SYNTHETIC_STATE_INSPECTED' $st.head $st.count
            } elseif ($Mode -eq 'Revoke') {
                if (-not [IO.File]::Exists($publicPin)) { New-Report 'HOLD_NOT_PINNED' $st.head $st.count }
                elseif ($st.revoked) { New-Report 'REJECT_ALREADY_REVOKED' $st.head $st.count }
                else { Append-History $journal $st 'REVOKED' $null $Zero }
            } else {
                if ([string]::IsNullOrWhiteSpace($BundleZip)) { throw 'BUNDLE_PATH_REQUIRED' }
                $data = Decode-Bundle $BundleZip
                $v = Verify-Synthetic $data
                if ([IO.File]::Exists($publicPin)) {
                    if ((Safe-Text $publicPin 2048) -cne $v.public) {
                        New-Report 'REJECT_UNPINNED_EXECUTOR_KEY' $st.head $st.count $v.publicsha
                    } elseif ($st.revoked) {
                        New-Report 'REJECT_REVOKED_EXECUTOR' $st.head $st.count $v.publicsha
                    } elseif ($st.nonces.Contains($v.nonce)) {
                        New-Report 'REJECT_REPLAY_NONCE' $st.head $st.count $v.publicsha
                    } else {
                        Append-History $journal $st 'SPENT' $v.nonce $v.receiptsha $v.publicsha
                    }
                } elseif ($st.count -ne 0) {
                    New-Report 'HOLD_MISSING_POLICY_PIN' $st.head $st.count
                } else {
                    # FIRST USE TRUST-ON-FIRST-USE, NOT independent authenticated enrollment.
                    [IO.File]::WriteAllText($publicPin, $v.public, [Text.UTF8Encoding]::new($false))
                    Append-History $journal $st 'SPENT' $v.nonce $v.receiptsha $v.publicsha
                }
            }
        }
    }
    To-Json $result
} catch {
    $reason = [string]$_.Exception.Message
    $safe = @('INVALID_FILE_LENGTH','INVALID_PUBLIC_BUNDLE_ENTRY','UNEXPECTED_BUNDLE_ENTRY',
              'INVALID_BUNDLE_SIZE','BUNDLE_NOT_FOUND','INVALID_SYNTHETIC_PROFILE',
              'INVALID_NONCE','INVALID_EPOCH','INVALID_PAYLOAD_FIELDS',
              'INVALID_SYNTHETIC_DATA','INVALID_RECEIPT_SIGNATURE','UNPINNED_EXECUTOR_KEY',
              'REFUSE_NONPUBLIC_RSA_XML','CUSTODIAN_CLOCK_SKEW','HISTORY_CHAIN_GAP','HISTORY_DIGEST_MISMATCH',
              'TRUNCATED_HISTORY','INVALID_NONCE_HISTORY','C_LOCK_BUSY',
              'REFUSE_NONEMPTY_UNMARKED_ROOT','INVALID_RECEIPT_FIELDS')
    if (-not ($safe -ccontains $reason)) { $reason='HOLD_ERROR_FAIL_CLOSED' }
    To-Json (New-Report $reason)
}
