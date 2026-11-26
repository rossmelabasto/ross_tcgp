# ross_tcgp

[English](README.md) · **Español**

Lee tu colección de **Pokémon TCG Pocket** directamente desde tu teléfono
Android y la guarda en un archivo JSON, desde la terminal, gratis y sin escribir
una sola carta a mano.

```
$ ross-tcgp scan
Scanning… (don't touch the phone)
  page 69: 393 cards read
  stopped: end of the list
Saved 393 different cards (937 copies) to ~/.local/share/ross_tcgp/collection-20261125-232730.json
```

> Proyecto de fans. Sin relación con Nintendo, The Pokémon Company, Creatures,
> GAME FREAK ni DeNA. Pokémon y sus nombres son marcas de sus dueños. Este
> repositorio **no contiene recursos del juego**: las imágenes de las cartas se
> descargan en tu propia máquina la primera vez que lo usas.

## Por qué

El juego no tiene exportación ni API. Los trackers que existen te hacen cargar
las cartas a mano o subir capturas una por una en el navegador. `ross_tcgp`
maneja el teléfono por `adb`: recorre la pantalla **My Cards**, toma capturas,
reconoce cada carta y lee cuántas copias tienes.

Después de un escaneo completo, `ross-tcgp scan --quick` lee solo lo nuevo
(ordena antes la lista del juego por **Recent cards**): revisar tus sobres nuevos
toma unos 15 segundos.

## Cómo funciona

| Paso | Qué pasa |
| --- | --- |
| Manejar el teléfono | Capturas en crudo por `adb exec-out screencap` (~1 s) y arrastres con `input motionevent` que se detienen en seco, sin inercia |
| Encontrar las cartas | El fondo es celeste pálido; las líneas de fondo entre cartas dan la grilla en cualquier resolución |
| Identificar cada carta | Cada carta se reduce a una "huella" de color de 16×22 y se compara con las de las ~4.600 imágenes oficiales (una multiplicación de matrices) |
| Leer las copias | El número blanco del recuadro oscuro se corta en dígitos y se compara con plantillas de la fuente del juego, sin OCR |
| Recorrer la lista | Cada arrastre deja una fila repetida para unir las páginas por las cartas, no por píxeles; el juego oculta los números mientras se mueve, así que cada página se repite hasta que está quieta |

El detalle de cada decisión está en [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Instalar

Desde [repo.rossmel.com](https://repo.rossmel.com/tcgp/) (paquetes firmados;
agrega el [repositorio](https://repo.rossmel.com/repository/) una vez):

```bash
sudo pacman -Syu ross-tcgp                          # Arch, CachyOS
sudo apt update && sudo apt install ross-tcgp       # Ubuntu, Debian
sudo dnf install ross-tcgp                          # Fedora
ross-tcgp update   # descarga datos e imágenes de las cartas (~70 MB, una vez)
```

Necesitas un teléfono Android con **depuración USB** y el juego abierto en **My Cards**.

## Uso

```bash
ross-tcgp scan             # toda la colección (~5 min para ~900 cartas)
ross-tcgp scan --quick     # solo lo nuevo (ordena por "Recent cards" en el juego)
ross-tcgp show --name pika # lista lo que tienes
ross-tcgp show --json      # el JSON crudo, para otras herramientas
ross-tcgp diff VIEJO.json  # qué cambió desde un escaneo anterior
ross-tcgp export           # CSV para PackProphet o una planilla
ross-tcgp export -f tcg-tracker   # CSV para tcgpocketcollectiontracker.com
```

### Usarla en otros trackers

- **[PackProphet](https://packprophet.spibane.com)** (qué sobre abrir, progreso
  por set): `ross-tcgp export` y luego *Collection → Import*. Corre en tu
  navegador, sin cuenta, con vista previa antes de guardar.
- **[TCG Pocket Collection Tracker](https://tcgpocketcollectiontracker.com)**
  (intercambios, amigos): `ross-tcgp export -f tcg-tracker` y luego inicia sesión →
  *Import*. Ese sitio usa sus propios ids, así que su lista de cartas se descarga
  en cada exportación, y el archivo trae todas las cartas (tuyas o no) porque **su
  importación reemplaza tu colección allá**.

No toques el teléfono mientras escanea. Los escaneos quedan en
`~/.local/share/ross_tcgp`; la caché de imágenes en `~/.cache/ross_tcgp`.

## ¿Está permitido?

Solo hace scroll en la pantalla de colección y toma capturas, como lo harías a
mano. No juega, no abre sobres, no lee la memoria del juego ni habla con sus
servidores. Aun así, automatizar toques es tu responsabilidad: lee los términos
de servicio del juego.

## Licencia

[MIT](LICENSE) © 2026 Rossmel Abasto
