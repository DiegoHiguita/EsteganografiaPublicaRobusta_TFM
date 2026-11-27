# Prototipo: esteganografía de clave pública sobre JPEG (TFM)

Prototipo del Trabajo Final de Máster *Diseño y evaluación experimental de un esquema de esteganografía de clave pública resistente a compresión JPEG* (UOC, Máster en Ciberseguridad y Privacidad).

Inserta una trama de 32 bits en la luminancia de una imagen mediante QIM sobre la DCT, con un mapa de posiciones derivado de una clave pública (X25519 + HKDF), la protege con Reed-Solomon RS(8,4) y mide su recuperación tras recomprimir la imagen en JPEG.

Limitaciones declaradas: la clave pública efímera `epk_A` se transmite por un canal auxiliar (no va dentro de la imagen) y el prototipo no incluye autenticación ni integridad del emisor.

## Estructura

| Módulo | Función |
|---|---|
| `frame.py` | Trama de 32 bits y conversión bytes <-> bits |
| `coding.py` | Reed-Solomon RS(8,4) |
| `crypto.py` | X25519 y HKDF |
| `positions.py` | Mapa pseudoaleatorio de posiciones y dither |
| `stego.py` | Inserción y extracción QIM-DCT |
| `imgutils.py` | Conversión de color y sustitución de la luminancia |
| `channel.py` | Recompresión JPEG |
| `metrics.py` | BER, PSNR, SSIM y clasificación del resultado |
| `main.py` | Flujo completo de una imagen y registro de resultados |
| `analyze.py` | Figuras y tablas a partir del registro de resultados |
| `tests/` | Pruebas unitarias de cada módulo |

## Instalación

Python 3.11.

    pip install -r requirements.txt

## Pruebas

    python -m unittest discover -s tests -v

## Imágenes

No se incluyen las imágenes. El corpus es el conjunto ALASKA2, que se descarga de la fuente oficial: https://alaska.utt.fr (consulta allí las condiciones de uso). Coloca las imágenes en la carpeta que indique `main.py` (ver abajo).

## Uso

Ejecución de los ensayos (por ejemplo, el piloto con 20 imágenes):

    python main.py --images imagenes --out piloto.jsonl --limit 20

Opciones:

| Opción | Significado |
|---|---|
| `--images` | Carpeta con las imágenes (obligatorio) |
| `--out` | Fichero `.jsonl` de salida (obligatorio) |
| `--limit` | Número máximo de imágenes (por defecto, todas) |
| `--qualities` | Calidades JPEG, por defecto 50 60 70 75 80 85 90 95 100 |
| `--alphas` | Valores de α, por defecto 1.5 2 3 4 |
| `--seed` | Semilla maestra (texto), por defecto `"tfm-piloto"` |

Análisis de resultados (figuras `.png`/`.pdf` y tablas `.tex`):

    python analyze.py --input piloto.jsonl --outdir resultados

## Convenciones

- Trama M = V || T, con V en el primer byte, big-endian.
- Bits de cada byte: del más al menos significativo.
- Registro de resultados: JSON Lines, un ensayo por línea.
- Ningún secreto (claves privadas, secreto compartido, semilla) se escribe en los registros.