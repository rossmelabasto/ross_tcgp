# Cambios

Los cambios importantes del proyecto. Las versiones siguen [SemVer](https://semver.org/lang/es/).

## [0.2.2] - 2026-11-26

### Corregido
- pacman ya no avisa "directory permissions differ" al instalar o actualizar: las carpetas del
  paquete ahora quedan registradas como un 755 normal.

## [0.2.1] - 2026-11-26

### Corregido
- `scan` comprueba que la grilla de cartas esté en pantalla antes de tocar el teléfono; en
  cualquier otra pantalla (una batalla, la tienda…) se detiene sin hacer scroll.
- Un escaneo que no lee ninguna carta ya no guarda un archivo.

## [0.2.0] - 2026-11-26

### Agregado
- Paquetes para Linux en [repo.rossmel.com](https://repo.rossmel.com/tcgp/): `ross-tcgp` para
  pacman, APT y DNF, independiente de la arquitectura, que usa el Python, Pillow, NumPy y adb del sistema.
- Flujo de release que instala y ejecuta cada paquete en Arch, CachyOS, Ubuntu 22.04 y 24.04,
  Debian 13 y Fedora antes de publicar.

## [0.1.0] - 2026-11-25

### Agregado
- `ross-tcgp scan`: lee toda la grilla de "My Cards" por adb, identifica cada carta contra
  ~4.600 imágenes de referencia y lee cuántas copias tienes; `--quick` lee solo lo nuevo.
- Comandos `show`, `diff` y `update`; capturas de la colección en JSON en `~/.local/share/ross_tcgp`.
- `scan --save-pages` / `--from-pages` para guardar las capturas y volver a leerlas sin el teléfono.
