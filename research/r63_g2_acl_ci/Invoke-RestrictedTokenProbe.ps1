# R63 G2 — direct uncooperative I/O probe under a real distinct Windows token.
# This script is invoked ONLY against a new disposable fake journal directory.
param([Parameter(Mandatory)][ValidateSet('AuthorizedWriter','RestrictedReader')][string]$Mode,
      [Parameter(Mandatory)][string]$Root)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'WINDOWS_ONLY' }
$rootPath = [IO.Path]::GetFullPath($Root)
if ((Split-Path -Leaf $rootPath) -ne 'journal') { throw 'REFUSE_NON_LAB_JOURNAL_DIRECTORY' }
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$admin = [Security.Principal.WindowsPrincipal]::new($identity).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
$paths = @{
    v1 = Join-Path $rootPath 'v1.jsonl'
    v2 = Join-Path $rootPath 'v2.jsonl'
    flag = Join-Path $rootPath 'uncertain.flag'
    sibling = Join-Path $rootPath 'unauthorized-new-file.txt'
}
foreach ($k in @('v1','v2','flag')) {
    if (-not [IO.File]::Exists($paths[$k])) { throw ('MISSING_TEST_FILE_' + $k) }
}
$results = [ordered]@{
    mode = $Mode
    current_token_sid = $identity.User.Value
    current_token_name = $identity.Name
    is_admin = $admin
    read_v1_bytes = ([IO.File]::ReadAllBytes($paths.v1)).Length
    read_v2_bytes = ([IO.File]::ReadAllBytes($paths.v2)).Length
    operations = [ordered]@{}
}
function Attempt([string]$label, [scriptblock]$body) {
    try {
        & $body
        $results.operations[$label] = 'ALLOWED'
    } catch {
        # Windows PowerShell 5.1 wraps static .NET method errors inside
        # MethodInvocationException. Only genuine AccessDenied in the nested
        # exception chain qualifies; a sharing/IO error is INCONCLUSIVE.
        $outer=$_.Exception
        $inner=$outer
        $denied=$false
        while ($null -ne $inner) {
            if ($inner -is [UnauthorizedAccessException] -or $inner.HResult -eq -2147024891) {
                $denied=$true
                break
            }
            $inner=$inner.InnerException
        }
        if ($denied) { $results.operations[$label] = 'ACCESS_DENIED' }
        else { throw ('INCONCLUSIVE_' + $label + '_' + $outer.GetType().FullName + '_' + $outer.Message) }
    }
}
if ($Mode -eq 'AuthorizedWriter') {
    if ($admin) { throw 'AUTHORIZED_WRITER_UNEXPECTEDLY_ADMIN' }
    Attempt 'append_v1' { [IO.File]::AppendAllText($paths.v1, "AUTHORIZED_WRITER_TEST_ONLY" + [char]10) }
    Attempt 'append_v2' { [IO.File]::AppendAllText($paths.v2, "AUTHORIZED_WRITER_TEST_ONLY" + [char]10) }
    Attempt 'create_sibling' { [IO.File]::WriteAllText((Join-Path $rootPath 'authorized-new-file.txt'),'ALLOWED_WRITER') }
} else {
    if ($admin) { throw 'RESTRICTED_READER_UNEXPECTEDLY_ADMIN' }
    Attempt 'append_v1' { [IO.File]::AppendAllText($paths.v1, "UNAUTHORIZED" + [char]10) }
    Attempt 'append_v2' { [IO.File]::AppendAllText($paths.v2, "UNAUTHORIZED" + [char]10) }
    Attempt 'overwrite_v1' { [IO.File]::WriteAllText($paths.v1, "UNAUTHORIZED") }
    Attempt 'delete_flag' { [IO.File]::Delete($paths.flag) }
    Attempt 'create_sibling' { [IO.File]::WriteAllText($paths.sibling, "UNAUTHORIZED") }
}
ConvertTo-Json -InputObject $results -Depth 6 -Compress
