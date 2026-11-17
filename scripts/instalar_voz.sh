#!/usr/bin/env bash
# Instala la voz local de Bat’z (whisper.cpp) en Linux o macOS para el usuario actual.
#
# SIN PROBAR en un Linux o macOS reales. Se probó en WSL (Ubuntu) con cmake simulado: clon y
# verificación del commit, descarga y SHA-256 del modelo, repetición sin cambios. No se probaron
# la compilación real con cmake ni las instalaciones con apt o brew.
#
#   1. ffmpeg con apt (Debian/Ubuntu) o Homebrew (macOS), si no está.
#   2. whisper.cpp v1.9.5 compilado con cmake desde el repositorio oficial (commit verificado).
#   3. El modelo ggml-base.bin (u otro) de Hugging Face, con tamaño y SHA-256 comprobados.
#
# whisper-cli y el modelo quedan en ~/.local/share/batz/voz, donde Bat’z los encuentra sin
# variables de entorno y sin reiniciarse. Se puede repetir: lo ya instalado y verificado se salta.
#
# Uso:    bash scripts/instalar_voz.sh [base|small|tiny] [carpeta]
#         base: 142 MiB (por defecto); small: 466 MiB, más preciso y más lento; tiny: 75 MiB.
#         Con otra carpeta, Bat’z solo la usa si defines BATZ_WHISPER_CLI y BATZ_WHISPER_MODEL.
# Quitar: rm -rf ~/.local/share/batz/voz   (y ffmpeg con apt o brew si nada más lo usa)
set -euo pipefail

MODELO="${1:-base}"
HABITUAL="$HOME/.local/share/batz/voz"
DESTINO="${2:-$HABITUAL}"
WHISPER_TAG="v1.9.5"
WHISPER_COMMIT="d1be6fde11ac6e0407606b4e42fe72d34add8037"
# Tamaño y SHA-256 que publica Hugging Face (ggerganov/whisper.cpp) para cada modelo.
case "$MODELO" in
  base)  BYTES=147951465; SHA256=60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe ;;
  small) BYTES=487601967; SHA256=1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b ;;
  tiny)  BYTES=77691713;  SHA256=be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21 ;;
  *) printf 'Modelo desconocido: %s (usa base, small o tiny)\n' "$MODELO" >&2; exit 2 ;;
esac

paso() { printf '==> %s\n' "$*"; }
nota() { printf '    %s\n' "$*"; }
falla() { printf 'Error: %s\n' "$*" >&2; exit 1; }
hay() { command -v "$1" >/dev/null 2>&1; }
tamano() { wc -c < "$1" | tr -d ' '; }
sha256() {
  if hay sha256sum; then sha256sum "$1" | cut -d ' ' -f 1; else shasum -a 256 "$1" | cut -d ' ' -f 1; fi
}
descargar() {  # $1 url, $2 archivo. Reintenta: --retry de curl no cubre una conexión cortada.
  local intento
  for intento in 1 2 3 4 5; do
    if hay curl; then
      if curl --fail --location --silent --show-error --proto '=https' --proto-redir '=https' -o "$2" "$1"; then return 0; fi
    elif hay wget; then
      if wget --quiet -O "$2" "$1"; then return 0; fi
    else
      falla "hace falta curl o wget"
    fi
    if [ "$intento" -lt 5 ]; then nota "falló; reintento en $((3 * intento)) s"; sleep $((3 * intento)); fi
  done
  falla "no se pudo descargar $1"
}

SUDO=""
if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; fi
NUCLEOS="$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)"
# Cada descarga va a una carpeta temporal nueva y vacía; se borra al terminar, también si algo falla.
TRABAJO="$(mktemp -d "${TMPDIR:-/tmp}/batz-voz.XXXXXX")"
trap 'rm -rf "$TRABAJO"' EXIT
mkdir -p "$DESTINO"
DESTINO="$(cd "$DESTINO" && pwd)"
printf 'Voz local de Bat’z en %s\n' "$DESTINO"

paso "1/3 ffmpeg"
if hay ffmpeg; then
  nota "ya está: $(command -v ffmpeg)"
elif hay apt-get; then
  nota "$SUDO apt-get install -y ffmpeg"
  $SUDO apt-get update -qq
  $SUDO apt-get install -y ffmpeg
elif hay brew; then
  nota "brew install ffmpeg"
  brew install ffmpeg
else
  falla "instala ffmpeg con el gestor de paquetes de tu sistema y repite"
fi

paso "2/3 whisper.cpp $WHISPER_TAG (compilado con cmake)"
CLI="$DESTINO/whisper/whisper-cli"
FIRMA="whisper.cpp $WHISPER_TAG $WHISPER_COMMIT"
if [ -x "$CLI" ] && [ "$(cat "$DESTINO/whisper/VERSION.txt" 2>/dev/null || true)" = "$FIRMA" ]; then
  nota "ya está: $CLI"
else
  if ! hay git || ! hay cmake || ! { hay c++ || hay g++ || hay clang++; }; then
    if hay apt-get; then
      nota "$SUDO apt-get install -y build-essential cmake git"
      $SUDO apt-get update -qq
      $SUDO apt-get install -y build-essential cmake git
    elif hay brew; then
      hay c++ || hay clang++ || falla "falta un compilador de C++: ejecuta xcode-select --install y repite"
      nota "brew install cmake git"
      brew install cmake git
    else
      falla "faltan git, cmake o un compilador de C++; instálalos y repite"
    fi
  fi
  nota "git clone --depth 1 --branch $WHISPER_TAG https://github.com/ggml-org/whisper.cpp.git"
  git -c advice.detachedHead=false clone --quiet --depth 1 --branch "$WHISPER_TAG" \
    https://github.com/ggml-org/whisper.cpp.git "$TRABAJO/whisper.cpp"
  COMMIT="$(git -C "$TRABAJO/whisper.cpp" rev-parse HEAD)"
  [ "$COMMIT" = "$WHISPER_COMMIT" ] || falla "la etiqueta $WHISPER_TAG apunta a $COMMIT y no a $WHISPER_COMMIT"
  nota "commit verificado: $COMMIT"
  # Estático: whisper-cli no depende de bibliotecas que queden en la carpeta de compilación.
  cmake -S "$TRABAJO/whisper.cpp" -B "$TRABAJO/build" -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF
  cmake --build "$TRABAJO/build" --config Release --target whisper-cli -j "$NUCLEOS"
  rm -rf "$DESTINO/whisper.nueva"
  mkdir "$DESTINO/whisper.nueva"
  cp "$TRABAJO/build/bin/whisper-cli" "$DESTINO/whisper.nueva/whisper-cli"
  chmod 755 "$DESTINO/whisper.nueva/whisper-cli"
  printf '%s\n' "$FIRMA" > "$DESTINO/whisper.nueva/VERSION.txt"
  rm -rf "$DESTINO/whisper"
  mv "$DESTINO/whisper.nueva" "$DESTINO/whisper"
  nota "instalado en $DESTINO/whisper"
fi

paso "3/3 modelo ggml-$MODELO.bin"
MODELO_DESTINO="$DESTINO/ggml-$MODELO.bin"
if [ -f "$MODELO_DESTINO" ] && [ "$(tamano "$MODELO_DESTINO")" = "$BYTES" ] \
   && [ "$(sha256 "$MODELO_DESTINO")" = "$SHA256" ]; then
  nota "ya está y su SHA-256 es correcto: $MODELO_DESTINO"
else
  mkdir "$TRABAJO/modelo"
  DESCARGA="$TRABAJO/modelo/ggml-$MODELO.bin"
  nota "$((BYTES / 1048576)) MB: puede tardar unos minutos"
  nota "descargando https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-$MODELO.bin"
  descargar "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-$MODELO.bin" "$DESCARGA"
  [ "$(tamano "$DESCARGA")" = "$BYTES" ] || falla "el modelo descargado no tiene el tamaño publicado ($BYTES bytes)"
  HASH="$(sha256 "$DESCARGA")"
  [ "$HASH" = "$SHA256" ] || falla "SHA-256 inesperado en el modelo: $HASH"
  nota "tamaño y SHA-256 correctos: $HASH"
  mv -f "$DESCARGA" "$MODELO_DESTINO"
  nota "instalado en $MODELO_DESTINO"
fi

paso "Comprobación"
VERSION="$("$CLI" --version 2>&1)" || falla "whisper-cli no arranca: $VERSION"
nota "$VERSION"

printf '\nListo. Bat’z usa esta voz local sin variables de entorno y sin reiniciarse.\n'
if [ "$DESTINO" != "$HABITUAL" ]; then
  nota "Esta no es la carpeta habitual: define estas variables antes de abrir Bat’z:"
  nota "  export BATZ_WHISPER_CLI='$CLI'"
  nota "  export BATZ_WHISPER_MODEL='$MODELO_DESTINO'"
fi
if [ -n "${BATZ_WHISPER_CLI:-}${BATZ_WHISPER_MODEL:-}" ]; then
  nota "Aviso: BATZ_WHISPER_CLI o BATZ_WHISPER_MODEL están definidas y mandan sobre esta carpeta."
fi
if hay whisper-cli; then nota "Aviso: el whisper-cli del PATH ($(command -v whisper-cli)) tiene prioridad."; fi
nota "Para quitarla: rm -rf '$DESTINO'"
