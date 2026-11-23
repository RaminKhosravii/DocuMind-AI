param(
    [Parameter(Mandatory = $true)]
    [string]$FilePath
)

$ErrorActionPreference = "Stop"

$certificateBase64 = $env:DOCUMIND_SIGNING_CERT_BASE64
$certificatePassword = $env:DOCUMIND_SIGNING_CERT_PASSWORD

if ([string]::IsNullOrWhiteSpace($certificateBase64) -or [string]::IsNullOrWhiteSpace($certificatePassword)) {
    Write-Warning "Authenticode signing was skipped: configure DOCUMIND_SIGNING_CERT_BASE64 and DOCUMIND_SIGNING_CERT_PASSWORD repository secrets with a trusted code-signing certificate."
    exit 0
}

$resolvedFile = (Resolve-Path $FilePath).Path
$tempRoot = if ([string]::IsNullOrWhiteSpace($env:RUNNER_TEMP)) { $env:TEMP } else { $env:RUNNER_TEMP }
$tempCertificate = Join-Path $tempRoot "documind-codesign.pfx"

try {
    [IO.File]::WriteAllBytes($tempCertificate, [Convert]::FromBase64String($certificateBase64))
    $sdkRoot = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"
    $signTool = Get-ChildItem -Path $sdkRoot -Filter signtool.exe -File -Recurse |
        Where-Object { $_.FullName -match "\\x64\\signtool\.exe$" } |
        Sort-Object FullName -Descending |
        Select-Object -First 1

    if (-not $signTool) {
        throw "Windows SDK signtool.exe was not found."
    }

    & $signTool.FullName sign /fd SHA256 /td SHA256 /tr "http://timestamp.digicert.com" /f $tempCertificate /p $certificatePassword $resolvedFile
    if ($LASTEXITCODE -ne 0) {
        throw "Authenticode signing failed with exit code $LASTEXITCODE."
    }

    & $signTool.FullName verify /pa /v $resolvedFile
    if ($LASTEXITCODE -ne 0) {
        throw "Authenticode signature verification failed."
    }

    Write-Host "Authenticode signature verified: $resolvedFile"
}
finally {
    if (Test-Path $tempCertificate) {
        Remove-Item $tempCertificate -Force
    }
}
