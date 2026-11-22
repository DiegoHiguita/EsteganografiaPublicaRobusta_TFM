# Prototipo: esteganografía de clave pública sobre JPEG (TFM)

## Estructura
| Módulo | Función | Estado |
|---|---|---|
| frame.py | Trama de 32 bits y conversión bytes <-> bits | hecho |
| coding.py | Reed-Solomon RS(8,4) | hecho |
| crypto.py | X25519 y HKDF | hecho |
| positions.py | Mapa pseudoaleatorio de posiciones y dither | hecho |
| stego.py | Inserción y extracción QIM-DCT | hecho |
| channel.py | Recompresión JPEG | hecho |
| metrics.py | BER, PSNR, SSIM | hecho |
| main.py | Flujo completo de una imagen | pendiente |

## Pruebas
    pip install -r requirements.txt
    pytest -v

Sin pytest: `PYTHONPATH=. python -m unittest discover -s tests -v`

## Convenciones
- Trama M = V || T, V en el primer byte, big-endian.
- Bits de cada byte: del más al menos significativo.
- Ningún secreto (claves privadas, secreto compartido, semilla) se escribe en registros.
