<#
.SYNOPSIS
    Moku 的按板构建入口；共用 Python 构建器生成独立源码视图和 USB 包。
    Moku's board entry; use the common Python builder for isolated source views and USB bundles.
.DESCRIPTION
    中文：metalio47 默认带上与 CI 一致的 S31 选项（PIE 像素算子与四级文字波纹），避免本机构建与正式
    Metalio 包不同；需要纯 C 对照时用 -Plain。-Board 接受历史别名 metalio_s31。
    English: metalio47 defaults to the same S31 switches CI uses (PIE pixel kernels and the four-level
    text ripple) so a local build matches the Metalio package; pass -Plain for the C-only comparison.
    -Board keeps the historical metalio_s31 alias.
.EXAMPLE
    .\tools\build_board.ps1 -Board metalio_s31
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("pico", "metalio47", "metalio_s31", "all")]
    [string]$Board,
    [string]$Output = "build/boards",
    [string]$Python = "python",
    [switch]$Plain
)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not $env:IDF_PATH) { throw "先载入对应板型的 ESP-IDF / Load this board's ESP-IDF first." }
$extra = @()
if (-not $Plain -and $Board -in @("metalio47", "metalio_s31", "all")) {
    $extra = @("--s31-pie", "--s31-text-ripple")
}
Push-Location $repo
try {
    $pythonPath = (Get-Command $Python -ErrorAction Stop).Source
    & $pythonPath tools/build_firmware.py --board $Board --output $Output --python $pythonPath @extra
    if ($LASTEXITCODE -ne 0) { throw "Board build failed ($LASTEXITCODE)" }
} finally { Pop-Location }
