param([string]$CommandFile,[string]$LogFile,[string]$ExpectedFile)
$ErrorActionPreference = 'Stop'
$a = New-Object -ComObject MultisimInterface.MultisimApp
$a.Path = 'D:\multimism\Circuit Design Suite 14.3\Multisim.exe'
$a.Connect()
try {
    $c = $a.NewFile()
    Write-Output ('Connected: ' + $a.IsConnected)
    $c.DoCommandLine($CommandFile, $LogFile)
    $deadline = (Get-Date).AddMinutes(15)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 3
        if ((Test-Path $ExpectedFile) -and ((Get-Item $ExpectedFile).Length -gt 1000)) {
            $size = (Get-Item $ExpectedFile).Length
            Start-Sleep -Seconds 3
            if ((Get-Item $ExpectedFile).Length -eq $size) { break }
        }
        if (Test-Path $LogFile) {
            if (Select-String -LiteralPath $LogFile -Pattern '^Error:|^Fatal:' -Quiet -ErrorAction SilentlyContinue) {
                throw 'XSPICE reported an error; inspect log.'
            }
        }
    }
    if (-not (Test-Path $ExpectedFile)) { throw 'Expected waveform was not produced.' }
    Write-Output ('Command complete; error=' + $c.LastErrorMessage)
} finally {
    $a.Disconnect()
}
