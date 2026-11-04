param([string]$WorkbookPath)

$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$output = Join-Path $project 'site\data\games.json'
$workbookWasSelected = -not $WorkbookPath

try {
    if ($workbookWasSelected) {
        Add-Type -AssemblyName System.Windows.Forms
        $picker = New-Object System.Windows.Forms.OpenFileDialog
        try {
            $picker.Title = 'Choose your updated referee workbook'
            $picker.Filter = 'Excel workbooks (*.xlsx;*.xlsm)|*.xlsx;*.xlsm'
            $picker.InitialDirectory = [Environment]::GetFolderPath('MyDocuments')
            if ($picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { exit 0 }
            $WorkbookPath = $picker.FileName
        } finally {
            $picker.Dispose()
        }
    }

    $candidates = @(
        @{ Name = (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'); Flags = @() },
        @{ Name = 'py.exe'; Flags = @('-3') },
        @{ Name = 'python.exe'; Flags = @() }
    )
    $python = $null
    foreach ($candidate in $candidates) {
        $command = Get-Command $candidate.Name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $command -or $command.Source -like '*\Microsoft\WindowsApps\*') { continue }
        $flags = $candidate.Flags
        try {
            & $command.Source @flags -c 'import openpyxl' 2>$null
            if ($LASTEXITCODE -eq 0) {
                $python = $command.Source
                break
            }
        } catch {
            continue
        }
    }
    if (-not $python) { throw 'Python with openpyxl is required. See the setup steps in README.md.' }

    & $python @flags (Join-Path $PSScriptRoot 'export_games.py') --workbook $WorkbookPath --output $output
    if ($LASTEXITCODE -ne 0) { throw 'Refresh failed. Fix the reported workbook issue before publishing.' }
    Write-Host "Public data file: $output"
    Write-Host 'Commit site/data/games.json in GitHub Desktop, then push to update the dashboard.'
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($workbookWasSelected) { [void](Read-Host 'Press Enter to close') }
    exit 1
}

if ($workbookWasSelected) { [void](Read-Host 'Press Enter to close') }
