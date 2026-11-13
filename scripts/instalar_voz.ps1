<#
.SYNOPSIS
    Instala la voz local de LOGOS (whisper.cpp) para el usuario actual, sin administrador.

.DESCRIPTION
    1. ffmpeg con winget (paquete portátil Gyan.FFmpeg, por usuario), si no está ya.
    2. whisper.cpp 1.9.5 para Windows x64 (CPU): zip oficial de GitHub con SHA-256 fijado.
    3. El modelo ggml-base.bin (u otro con -Modelo) de Hugging Face, con tamaño y SHA-256 fijados.

    whisper y el modelo quedan en %LOCALAPPDATA%\LOGOS\voz, donde LOGOS los encuentra sin
    variables de entorno y sin reiniciarse. Cada descarga y cada extracción usan una carpeta
    temporal nueva, y nada se instala sin comprobar antes su SHA-256. Se puede repetir: lo que
    ya está instalado y verificado se salta.

    Ejecutar:  powershell -ExecutionPolicy Bypass -File scripts\instalar_voz.ps1
    Quitar:    Remove-Item -Recurse -Force "$env:LOCALAPPDATA\LOGOS\voz"
               winget uninstall --id Gyan.FFmpeg -e

.PARAMETER Modelo
    base (por defecto, 142 MiB), small (466 MiB: más preciso y más lento) o tiny (75 MiB).

.PARAMETER Destino
    Otra carpeta. LOGOS solo la usa si defines LOGOS_WHISPER_CLI y LOGOS_WHISPER_MODEL.
#>
[CmdletBinding()]
param(
    [ValidateSet('base', 'small', 'tiny')]
    [string] $Modelo = 'base',
    [string] $Destino = (Join-Path $env:LOCALAPPDATA 'LOGOS\voz')
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'  # con barra de progreso, Invoke-WebRequest de PowerShell 5.1 va lentísimo
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

# Versiones fijadas. Para actualizar whisper.cpp: en https://github.com/ggml-org/whisper.cpp/releases
# cada versión vX.Y.Z enlaza su compilación bNNNN, que trae whisper-bin-x64.zip y su SHA-256.
$Whisper = @{
    Version = '1.9.5'
    Url     = 'https://github.com/ggml-org/whisper.cpp/releases/download/b5454/whisper-bin-x64.zip'
    Sha256  = '6ba69e3482d7826214f90a6a9c84ca07782aec1e1d0c6a7c30c994fd5d816ccb'
}
$FirmaWhisper = "whisper.cpp $($Whisper.Version) whisper-bin-x64.zip sha256=$($Whisper.Sha256)"
# Tamaño y SHA-256 que publica Hugging Face (ggerganov/whisper.cpp) para cada modelo.
$Modelos = @{
    base  = @{ Bytes = 147951465; Sha256 = '60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe' }
    small = @{ Bytes = 487601967; Sha256 = '1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b' }
    tiny  = @{ Bytes = 77691713;  Sha256 = 'be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21' }
}
$Habitual = Join-Path $env:LOCALAPPDATA 'LOGOS\voz'
$Destino = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Destino)
$Temporales = New-Object System.Collections.Generic.List[string]

function Paso([string] $texto) { Write-Host "==> $texto" -ForegroundColor Cyan }
function Nota([string] $texto) { Write-Host "    $texto" }

function Get-Sha256([string] $ruta) {
    (Get-FileHash -LiteralPath $ruta -Algorithm SHA256).Hash.ToLowerInvariant()
}

function New-CarpetaTemporal {
    # GetTempPath da la ruta larga: $env:TEMP puede ser un nombre corto 8.3 (perfiles con acentos)
    # que algunos cmdlets de PowerShell 5.1 rechazan.
    $ruta = Join-Path ([IO.Path]::GetTempPath()) ('logos-voz-' + [guid]::NewGuid().ToString('N').Substring(0, 12))
    New-Item -ItemType Directory -Path $ruta | Out-Null
    $Temporales.Add($ruta)
    $ruta
}

function Save-Descarga([string] $url, [string] $salida) {
    $ErrorActionPreference = 'Continue'  # el resultado de curl.exe se mira en su código de salida
    Nota "descargando $url"
    $curl = Get-Command curl.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    $intentos = 5
    for ($intento = 1; $intento -le $intentos; $intento++) {  # --retry de curl no cubre una conexión cortada
        if ($curl) {
            & $curl.Source --fail --location --silent --show-error --proto '=https' --proto-redir '=https' --output $salida $url
            $fallo = if ($LASTEXITCODE -ne 0) { "curl.exe terminó con código $LASTEXITCODE" } else { $null }
        } else {
            try { Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $salida -ErrorAction Stop; $fallo = $null }
            catch { $fallo = $_.Exception.Message }
        }
        if (-not $fallo) { return }
        if ($intento -lt $intentos) { Nota "$fallo; reintento en $(3 * $intento) s"; Start-Sleep -Seconds (3 * $intento) }
    }
    throw "No se pudo descargar $url ($fallo)."
}

function Find-Ffmpeg {
    $enSesion = Get-Command ffmpeg.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($enSesion) { return $enSesion.Source }
    # Lo que esta consola aún no ve: el PATH guardado y lo que deja winget. Sin modo de desarrollador,
    # winget no puede crear el enlace en WinGet\Links y deja ffmpeg en la carpeta del paquete.
    $candidatos = New-Object System.Collections.Generic.List[string]
    $guardado = [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine')
    foreach ($carpeta in $guardado.Split(';')) {
        if ($carpeta.Trim()) {
            try { $candidatos.Add([IO.Path]::Combine([Environment]::ExpandEnvironmentVariables($carpeta.Trim()), 'ffmpeg.exe')) } catch { }
        }
    }
    $winget = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet'
    $candidatos.Add((Join-Path $winget 'Links\ffmpeg.exe'))
    $patrones = @((Join-Path $winget 'Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe'),
                  (Join-Path $Destino 'ffmpeg.exe'), (Join-Path $Destino '*\ffmpeg.exe'), (Join-Path $Destino '*\*\ffmpeg.exe'))
    foreach ($encontrado in (Resolve-Path -Path $patrones -ErrorAction SilentlyContinue)) { $candidatos.Add($encontrado.ProviderPath) }
    foreach ($candidato in $candidatos) {
        try { if (Test-Path -LiteralPath $candidato -PathType Leaf) { return $candidato } } catch { }
    }
    return $null
}

function Install-Ffmpeg {
    $ErrorActionPreference = 'Continue'  # winget informa por su código de salida
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
        throw "No encuentro winget. Instala «Instalador de aplicaciones» desde Microsoft Store, o copia ffmpeg.exe en $Destino."
    }
    Nota 'winget install --id Gyan.FFmpeg -e (paquete portátil, solo para este usuario; ocupa unos 660 MB)'
    & winget.exe install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements | Out-Host
    $codigo = $LASTEXITCODE
    $ffmpeg = Find-Ffmpeg
    if (-not $ffmpeg) { throw "winget terminó con código $codigo y no aparece ffmpeg.exe." }
    $ffmpeg
}

function Install-Whisper([string] $carpeta) {
    $descarga = New-CarpetaTemporal
    $zip = Join-Path $descarga 'whisper-bin-x64.zip'
    Save-Descarga $Whisper.Url $zip
    $hash = Get-Sha256 $zip
    if ($hash -ne $Whisper.Sha256) { throw "SHA-256 inesperado en el zip de whisper.cpp: $hash (se esperaba $($Whisper.Sha256))." }
    Nota "SHA-256 correcto: $hash"
    $extraido = New-CarpetaTemporal
    Expand-Archive -LiteralPath $zip -DestinationPath $extraido
    $cli = Get-ChildItem -LiteralPath $extraido -Recurse -Filter 'whisper-cli.exe' | Select-Object -First 1
    if (-not $cli) { throw 'El zip no trae whisper-cli.exe.' }
    # Solo whisper-cli y las bibliotecas que carga; el zip trae además otros programas y pruebas.
    $nueva = "$carpeta.nueva"
    if (Test-Path -LiteralPath $nueva) { Remove-Item -LiteralPath $nueva -Recurse -Force }
    New-Item -ItemType Directory -Path $nueva | Out-Null
    Get-ChildItem -LiteralPath $cli.DirectoryName -File |
        Where-Object { ($_.Name -eq 'whisper-cli.exe') -or ($_.Name -eq 'whisper.dll') -or ($_.Name -like 'ggml*.dll') } |
        Copy-Item -Destination $nueva
    Set-Content -LiteralPath (Join-Path $nueva 'VERSION.txt') -Value $FirmaWhisper -Encoding ASCII
    if (Test-Path -LiteralPath $carpeta) { Remove-Item -LiteralPath $carpeta -Recurse -Force }
    Rename-Item -LiteralPath $nueva -NewName (Split-Path -Leaf $carpeta)
}

function Test-Modelo([string] $ruta, $esperado) {
    (Test-Path -LiteralPath $ruta -PathType Leaf) -and
        ((Get-Item -LiteralPath $ruta).Length -eq $esperado.Bytes) -and
        ((Get-Sha256 $ruta) -eq $esperado.Sha256)
}

function Install-Modelo([string] $nombre, $esperado, [string] $destino) {
    $descarga = New-CarpetaTemporal
    $archivo = Join-Path $descarga $nombre
    Nota ('{0:N0} MB: puede tardar unos minutos' -f ($esperado.Bytes / 1MB))
    Save-Descarga "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/$nombre" $archivo
    $bytes = (Get-Item -LiteralPath $archivo).Length
    $hash = Get-Sha256 $archivo
    if (($bytes -ne $esperado.Bytes) -or ($hash -ne $esperado.Sha256)) {
        throw "El modelo descargado no coincide con el publicado ($bytes bytes, SHA-256 $hash)."
    }
    Nota "tamaño ($bytes bytes) y SHA-256 correctos: $hash"
    Move-Item -LiteralPath $archivo -Destination $destino -Force
}

function Get-VersionWhisper([string] $cli) {
    $ErrorActionPreference = 'Continue'  # whisper-cli escribe en stderr
    $salida = (& $cli --version 2>&1 | ForEach-Object { "$_" }) -join ' '
    if ($LASTEXITCODE -ne 0) {
        throw "whisper-cli.exe no arranca (código $LASTEXITCODE). Si falta el runtime de Visual C++, instálalo y repite."
    }
    $salida.Trim()
}

try {
    Write-Host "Voz local de LOGOS en $Destino"
    $admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
    if ($admin) { Write-Warning 'No hace falta ser administrador: esto instala solo para el usuario actual.' }
    New-Item -ItemType Directory -Force -Path $Destino | Out-Null

    Paso '1/3 ffmpeg'
    $ffmpeg = Find-Ffmpeg
    if ($ffmpeg) { Nota "ya está: $ffmpeg" } else { $ffmpeg = Install-Ffmpeg; Nota "instalado: $ffmpeg" }

    Paso "2/3 whisper.cpp $($Whisper.Version) para Windows x64 (CPU)"
    $carpetaWhisper = Join-Path $Destino 'whisper'
    $cli = Join-Path $carpetaWhisper 'whisper-cli.exe'
    $marca = Join-Path $carpetaWhisper 'VERSION.txt'
    if ((Test-Path -LiteralPath $cli) -and (Test-Path -LiteralPath $marca) -and
        ((Get-Content -LiteralPath $marca -Raw).Trim() -eq $FirmaWhisper)) {
        Nota "ya está: $cli"
    } else {
        Install-Whisper $carpetaWhisper
        Nota "instalado en $carpetaWhisper"
    }

    $nombre = "ggml-$Modelo.bin"
    $modeloDestino = Join-Path $Destino $nombre
    Paso "3/3 modelo $nombre"
    if (Test-Modelo $modeloDestino $Modelos[$Modelo]) {
        Nota "ya está y su SHA-256 es correcto: $modeloDestino"
    } else {
        Install-Modelo $nombre $Modelos[$Modelo] $modeloDestino
        Nota "instalado en $modeloDestino"
    }

    Paso 'Comprobación'
    $faltan = @('msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll', 'vcomp140.dll' |
        Where-Object { -not (Test-Path -LiteralPath (Join-Path $env:WINDIR "System32\$_")) })
    if ($faltan.Count) {
        Write-Warning ("whisper-cli necesita el runtime de Visual C++ 2015-2022 x64 y faltan {0}. " -f ($faltan -join ', ') +
            'Instálalo (pide permiso de administrador): winget install --id Microsoft.VCRedist.2015+.x64 -e')
    }
    Nota (Get-VersionWhisper $cli)

    Write-Host ''
    Write-Host 'Listo. LOGOS usa esta voz local sin variables de entorno y sin reiniciarse.' -ForegroundColor Green
    if ($Destino.TrimEnd('\') -ne $Habitual.TrimEnd('\')) {
        Nota 'Esta no es la carpeta habitual: define estas variables antes de abrir LOGOS:'
        Nota "  `$env:LOGOS_WHISPER_CLI = '$cli'"
        Nota "  `$env:LOGOS_WHISPER_MODEL = '$modeloDestino'"
    }
    if ($env:LOGOS_WHISPER_CLI -or $env:LOGOS_WHISPER_MODEL) {
        Nota 'Aviso: LOGOS_WHISPER_CLI o LOGOS_WHISPER_MODEL están definidas y mandan sobre esta carpeta.'
    }
    $otro = Get-Command whisper-cli.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($otro) { Nota "Aviso: el whisper-cli del PATH ($($otro.Source)) tiene prioridad sobre esta carpeta." }
    Nota 'Para quitarla:'
    Nota "  Remove-Item -Recurse -Force '$Destino'"
    Nota '  winget uninstall --id Gyan.FFmpeg -e   (si nada más usa ese ffmpeg)'
} finally {
    foreach ($temporal in $Temporales) { Remove-Item -LiteralPath $temporal -Recurse -Force -ErrorAction SilentlyContinue }
}
