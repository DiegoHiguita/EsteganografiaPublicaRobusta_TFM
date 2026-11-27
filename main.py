"""
main.py - Flujo completo del experimento: un ensayo (insertar, canal, extraer, medir) y el registro JSON.

ESQUELETO: implementa las funciones marcadas con TODO. Orden sugerido:
  1) derive_test_key_bytes    2) image_sha256    3) write_record    4) run_trial    5) main (línea de comandos)


Tipos de ensayo (parámetro control):
  - "normal":      inserción con la clave correcta.
  - "wrong_key":   Bob usa otra clave privada (comprueba RS-1).
  - "clean_image": no se inserta nada; Bob intenta extraer de la imagen original (comprueba RS-2).

El registro de cada ensayo es un diccionario con tipos básicos de Python (nada de NumPy, ni inf, ni NaN).
NUNCA se incluyen en él claves privadas, el secreto compartido ni la semilla (RS-4).
"""

import argparse
import hashlib
import json
import random
import time
from pathlib import Path

import cv2

import channel
import coding
import crypto
import frame
import imgutils
import metrics
import positions
import stego

CODE_VERSION = "pec3-0.1"
CONTROLS = ("normal", "wrong_key", "clean_image")


def derive_test_key_bytes(master_seed: bytes, label: str) -> bytes:
    """
    Deriva 32 bytes reproducibles a partir de la semilla maestra y una etiqueta (para claves privadas de prueba
    y para la semilla de la trama).

    Args:
        master_seed (bytes): semilla maestra de la que salen todas las claves y tramas de prueba.
        label (str): etiqueta legible para distinguir claves y tramas."""
    private_key = hashlib.sha256(master_seed + b"|" + label.encode()).digest()
    return private_key


def image_sha256(path) -> str:
    """
    Hash SHA-256 (en hexadecimal) del fichero de imagen, para identificarla en el registro.
    Args:
        path (str): ruta al fichero de imagen.
    Returns:
        str: hash SHA-256 de la imagen.
    """

    image_hash = hashlib.sha256(Path(path).read_bytes()).hexdigest()

    return image_hash



def write_record(path, record: dict) -> None:
    """
    Añade el registro al final del fichero como UNA línea JSON (formato JSON Lines, .jsonl).

    Args:
        path (str): ruta al fichero de registro.
        record (dict): registro a añadir.
    """
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def run_trial(bgr, image_id: str, image_hash: str, quality: int, alpha: float,
              master_seed: bytes, control: str = "normal") -> dict:
    """
    Ejecuta un ensayo completo y devuelve su registro.
    Args:
        bgr: imagen original en color (uint8, alto x ancho x 3).
        image_id (str): identificador legible de la imagen (por ejemplo, el nombre del fichero).
        image_hash (str): SHA-256 de la imagen.
        quality (int): calidad JPEG del canal (50-100).
        alpha (float): factor del paso Delta.
        master_seed (bytes): semilla de la que salen todas las claves y tramas de prueba.
        control (str): uno de CONTROLS.
    Returns:
        dict con exactamente estos campos: trial_id, image_id, image_sha256, code_version, control, quality,
        jpeg_codec, alpha, rs_config, seed_id, frame_hex, psnr, ssim, ber_raw, ber_rs, status, accepted,
        aletheia, aletheia_status, time_s.
    Raises:
        ValueError: Si control no es válido.

    TODO (en este orden):
      1. Validar control. t0 = time.perf_counter().
      2. trial_id = f"{image_id}|Q{quality}|a{alpha}|{control}"
      3. Trama: rng = random.Random(int.from_bytes(derive_test_key_bytes(master_seed, "frame|" + trial_id), "big"))
         sent_frame = frame.build_frame(frame.PROTOCOL_VERSION, frame.make_test_id(rng))
         coded_bits = frame.bytes_to_bits(coding.encode_rs(sent_frame))
      4. Claves: sk_b, pk_b = crypto.generate_keypair(derive_test_key_bytes(master_seed, "bob"))
                 esk, epk = crypto.generate_keypair(derive_test_key_bytes(master_seed, "esk|" + trial_id))
         seed_tx = crypto.derive_seed(crypto.compute_shared_secret(esk, pk_b), epk, pk_b)
         emap_tx = positions.generate_map(seed_tx, positions.blocks_count(alto, ancho))
      5. Inserción: si control == "clean_image": stego_bgr = bgr, psnr y ssim = None.
         Si no: stego_luma = stego.embed(imgutils.get_luma(bgr), coded_bits, emap_tx, alpha)
                stego_bgr = imgutils.replace_luma(bgr, stego_luma)
                psnr y ssim con metrics (bgr frente a stego_bgr). Si el PSNR es infinito, guarda None
                (JSON estándar no admite inf).
      6. Canal: received = channel.jpeg_recompress(stego_bgr, quality)
      7. Receptor: sk_rx = sk_b, salvo en "wrong_key", donde sk_rx sale de otra etiqueta ("bob-wrong").
         seed_rx = crypto.receiver_derive_seed(sk_rx, pk_b, epk)
         emap_rx = positions.generate_map(seed_rx, ...)
         received_bits = stego.extract(imgutils.get_luma(received), emap_rx, alpha)
      8. result = metrics.classify_decoding(sent_frame, received_bits)
      9. Devolver el diccionario con los campos de arriba:
           jpeg_codec = f"opencv-{cv2.__version__}", rs_config = "RS(8,4)", seed_id = trial_id,
           frame_hex = sent_frame.hex(), aletheia = None, aletheia_status = "no_disponible",
           ber_raw/ber_rs/status/accepted de result, time_s = time.perf_counter() - t0.
         psnr y ssim deben ser float de Python (usa float(...)).
    """
    if control not in CONTROLS:
        raise ValueError(f"control debe ser uno de {CONTROLS}, pero se recibió {control!r}")

    t0 = time.perf_counter() #control de tiempo para medir la duración del ensayo
    trialDict_id = f"{image_id}|Q{quality}|a{alpha}|{control}" #diccionario con los datos del ensayo

    #definimos la trama a enviar
    rng = random.Random(int.from_bytes(derive_test_key_bytes(master_seed, "frame|" + trialDict_id), "big"))
    sent_frame = frame.build_frame(frame.PROTOCOL_VERSION, frame.make_test_id(rng))
    #pasamos a bits la trama codificada con RS
    coded_bits = frame.bytes_to_bits(coding.encode_rs(sent_frame))
    #------------------------------------------#
    #generamos las claves de Bob y de Alice
    sk_b, pk_b = crypto.generate_keypair(derive_test_key_bytes(master_seed, "bob"))
    esk, epk = crypto.generate_keypair(derive_test_key_bytes(master_seed, "esk|" + trialDict_id))
    #derivamos la semilla de transmisión y el mapa de posiciones
    seed_tx = crypto.derive_seed(crypto.compute_shared_secret(esk, pk_b), epk, pk_b)
    emap_tx = positions.generate_map(seed_tx, positions.blocks_count(bgr.shape[0], bgr.shape[1]))
    #------------------------------------------#    
    if control == "clean_image":
        stego_bgr = bgr
        psnr = None
        ssim = None
    else:
        #generamos los datos de la imagen esteganografiada
        stego_luma = stego.embed(imgutils.get_luma(bgr), coded_bits, emap_tx, alpha)
        stego_bgr = imgutils.replace_luma(bgr, stego_luma)
        psnr = float(metrics.psnr(bgr, stego_bgr))
        ssim = float(metrics.ssim(bgr, stego_bgr))
        if psnr == float("inf"):
            psnr = None
    #------------------------------------------#
    #canal de transmisión
    channel_bgr = channel.jpeg_recompress(stego_bgr, quality)
    #------------------------------------------#
    #receptor
    if control == "wrong_key": #esto simula que Bob tiene una clave privada incorrecta, derivada de otra etiqueta
        sk_rx, _ = crypto.generate_keypair(derive_test_key_bytes(master_seed, "bob-wrong"))
    else:
        sk_rx = sk_b

    #obtenemos la semilla de recepción y el mapa de posiciones
    seed_rx = crypto.receiver_derive_seed(sk_rx, pk_b, epk)
    emap_rx = positions.generate_map(seed_rx, positions.blocks_count(bgr.shape[0], bgr.shape[1]))
    #extraemos los bits recibidos
    received_bits = stego.extract(imgutils.get_luma(channel_bgr), emap_rx, alpha)
    #------------------------------------------#
    #clasificamos la decodificación
    result = metrics.classify_decoding(sent_frame, received_bits) 
    
    jpeg_codec = f"opencv-{cv2.__version__}"
    rs_config = "RS(8,4)"
    seed_id = trialDict_id
    frame_hex = sent_frame.hex()
    aletheia = None
    aletheia_status = "no_disponible"


    time_s = time.perf_counter() - t0
    
    return {
        "trial_id": trialDict_id,
        "image_id": image_id,
        "image_sha256": image_hash,
        "code_version": CODE_VERSION,
        "control": control,
        "quality": quality,
        "jpeg_codec": jpeg_codec,
        "alpha": alpha,
        "rs_config": rs_config,
        "seed_id": seed_id,
        "frame_hex": frame_hex,
        "psnr": psnr,
        "ssim": ssim,
        "ber_raw": result.ber_raw,
        "ber_rs": result.ber_rs,
        "status": result.status,
        "accepted": result.accepted,
        "aletheia": aletheia,
        "aletheia_status": aletheia_status,
        "time_s": time_s,
    }


def main(argv=None) -> None:
    """
    Línea de comandos: recorre las imágenes de una carpeta y escribe un registro por ensayo.

    Argumentos sugeridos (argparse):
      --images  carpeta con las imágenes (obligatorio)
      --out     fichero .jsonl de salida (obligatorio)
      --limit   número máximo de imágenes (por defecto, todas)
      --qualities  lista, por defecto 50 60 70 75 80 85 90 95 100
      --alphas     lista, por defecto 1.5 2 3 4
      --seed    semilla maestra (texto), por defecto "tfm-piloto"

    TODO:
      - Listar las imágenes (.jpg, .jpeg, .png) de la carpeta, ordenadas, y quedarse con las primeras --limit.
      - Para cada imagen: cargarla (imgutils.load_bgr) y calcular su hash UNA vez.
      - Para cada calidad y cada alpha: run_trial con control "normal" y write_record.
      - Además, para cada imagen, un ensayo "wrong_key" y otro "clean_image" por calidad (con un alpha fijo, p. ej. 2).
      - Mostrar el progreso cada N ensayos.
    """
    parser = argparse.ArgumentParser(description="Ejecuta los ensayos y escribe un registro JSON por ensayo.")
    parser.add_argument("--images", required=True, help="carpeta con las imágenes")
    parser.add_argument("--out", required=True, help="fichero .jsonl de salida")
    parser.add_argument("--limit", type=int, default=None, help="número máximo de imágenes")
    parser.add_argument("--qualities", type=int, nargs="+", default=[50, 60, 70, 75, 80, 85, 90, 95, 100])
    parser.add_argument("--alphas", type=float, nargs="+", default=[1.5, 2, 3, 4])
    parser.add_argument("--control-alpha", type=float, default=2.0, help="alpha de los ensayos de control")
    parser.add_argument("--seed", default="tfm-piloto", help="semilla maestra (texto)")
    parser.add_argument("--overwrite", action="store_true", help="borrar el fichero de salida si ya existe")
    args = parser.parse_args(argv)

    out_path = Path(args.out)
    if out_path.exists():
        if not args.overwrite:
            raise SystemExit(f"{out_path} ya existe. Usa --overwrite para borrarlo o elige otro nombre.")
        out_path.unlink()

    extensions = (".jpg", ".jpeg", ".png")
    image_paths = sorted(p for p in Path(args.images).iterdir() if p.suffix.lower() in extensions)
    if args.limit is not None:
        image_paths = image_paths[:args.limit]
    if not image_paths:
        raise SystemExit(f"No se encontraron imágenes en {args.images}")

    master_seed = args.seed.encode()
    trials_per_image = len(args.qualities) * (len(args.alphas) + 2)   # +2: wrong_key y clean_image por calidad
    total = len(image_paths) * trials_per_image
    done = 0

    for path in image_paths:
        bgr = imgutils.load_bgr(path)
        image_hash = image_sha256(path)          # una sola vez por imagen
        for quality in args.qualities:
            for alpha in args.alphas:
                write_record(out_path, run_trial(bgr, path.name, image_hash, quality, alpha, master_seed, "normal"))
                done += 1
            for control in ("wrong_key", "clean_image"):
                write_record(out_path, run_trial(bgr, path.name, image_hash, quality, args.control_alpha,
                                                 master_seed, control))
                done += 1
        print(f"[{done}/{total}] {path.name}")



if __name__ == "__main__":
    main()