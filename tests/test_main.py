"""
test_main.py - Pruebas de main.py: un ensayo completo y el registro JSON.

Requisitos relacionados: RF-1 (aceptación), RF-2 (trama), RF-3 (mapa desde las claves), RF-5 (registro
reproducible), RS-1 (clave incorrecta), RS-2 (imagen sin señal), RS-4 (sin secretos en el registro).
Usa una imagen sintética en color; no necesita ficheros externos.
"""
import json
import os
import tempfile
import unittest

import cv2
import numpy as np

import crypto
import main

MASTER_SEED = b"semilla-maestra-de-pruebas"
REQUIRED_FIELDS = {
    "trial_id", "image_id", "image_sha256", "code_version", "control", "quality", "jpeg_codec", "alpha",
    "rs_config", "seed_id", "frame_hex", "psnr", "ssim", "ber_raw", "ber_rs", "status", "accepted",
    "aletheia", "aletheia_status", "time_s",
}


def make_bgr(seed=0, height=256, width=256):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:height, 0:width]
    base = 100 + 60 * np.sin(x / 37.0) + 40 * np.cos(y / 23.0)
    img = np.stack([base + rng.normal(0, 6, (height, width)) + k * 10 for k in range(3)], axis=-1)
    img = cv2.GaussianBlur(img.astype(np.float32), (0, 0), 1.2)
    return np.clip(img, 20, 235).astype(np.uint8)


def trial(**kw):
    args = dict(bgr=make_bgr(), image_id="img0", image_hash="0" * 64, quality=100, alpha=4.0,
                master_seed=MASTER_SEED)
    args.update(kw)
    return main.run_trial(**args)


class TestRunTrial(unittest.TestCase):

    def test_record_has_all_fields(self):
        """El registro contiene todos los campos prometidos en el capítulo 3."""
        self.assertEqual(set(trial().keys()), REQUIRED_FIELDS)

    def test_record_is_json_serializable(self):
        """Sin enteros ni floats de NumPy: json.dumps no falla (y no hay inf/NaN)."""
        text = json.dumps(trial(), allow_nan=False)
        self.assertIsInstance(json.loads(text), dict)

    def test_clean_channel_recovers_frame(self):
        """Con Q=100 y alpha=4 la trama se recupera y se acepta (RF-1)."""
        r = trial(quality=100, alpha=4.0)
        self.assertEqual(r["status"], "correcta")
        self.assertTrue(r["accepted"])
        self.assertEqual(r["ber_rs"], 0.0)
        self.assertGreater(r["psnr"], 38.0)
        self.assertGreater(r["ssim"], 0.95)

    def test_survives_moderate_jpeg(self):
        """Con Q=90 y alpha=2 también se recupera."""
        self.assertEqual(trial(quality=90, alpha=2.0)["status"], "correcta")

    def test_same_inputs_same_record(self):
        """Mismos parámetros y semillas, mismo registro (RF-5), salvo el tiempo."""
        a, b = trial(), trial()
        a.pop("time_s"), b.pop("time_s")
        self.assertEqual(a, b)

    def test_different_trials_use_different_frames(self):
        """Ensayos distintos usan tramas T distintas (cada uno su semilla)."""
        frames = {trial(image_id=f"img{i}")["frame_hex"] for i in range(5)}
        self.assertEqual(len(frames), 5)

    def test_frame_starts_with_expected_version(self):
        """El primer byte de la trama enviada es V_esp = 0x01 (RF-2)."""
        self.assertEqual(trial()["frame_hex"][:2], "01")

    def test_wrong_key_control_is_never_accepted_correctly(self):
        """Con una clave incorrecta no se recupera la trama (RS-1), en 30 imágenes distintas."""
        bers = []
        for i in range(30):
            r = trial(bgr=make_bgr(i), image_id=f"img{i}", control="wrong_key")
            self.assertNotEqual(r["status"], "correcta")
            bers.append(r["ber_raw"])
        self.assertGreater(np.mean(bers), 0.4)
        self.assertLess(np.mean(bers), 0.6)

    def test_clean_image_control_is_not_accepted(self):
        """Una imagen sin señal, con la clave correcta, no se recupera (RS-2), en 30 imágenes."""
        for i in range(30):
            r = trial(bgr=make_bgr(i), image_id=f"img{i}", control="clean_image")
            self.assertNotEqual(r["status"], "correcta")
            self.assertIsNone(r["psnr"])

    def test_no_secrets_in_record(self):
        """RS-4: ni claves privadas, ni secreto compartido, ni semilla aparecen en el registro."""
        r = trial()
        text = json.dumps(r).lower()
        trial_id = r["trial_id"]
        sk_b, pk_b = crypto.generate_keypair(main.derive_test_key_bytes(MASTER_SEED, "bob"))
        esk, epk = crypto.generate_keypair(main.derive_test_key_bytes(MASTER_SEED, "esk|" + trial_id))
        shared = crypto.compute_shared_secret(esk, pk_b)
        seed = crypto.derive_seed(shared, epk, pk_b)
        for name, secret in (("sk_b", sk_b), ("esk", esk), ("secreto", shared), ("semilla", seed)):
            with self.subTest(secret=name):
                self.assertNotIn(secret.hex(), text)

    def test_invalid_control(self):
        with self.assertRaises(ValueError):
            trial(control="otro")


class TestWriteRecord(unittest.TestCase):

    def test_one_json_per_line(self):
        """Cada ensayo se añade como una línea JSON independiente (formato JSON Lines)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registro.jsonl")
            main.write_record(path, trial(image_id="a"))
            main.write_record(path, trial(image_id="b"))
            with open(path, encoding="utf-8") as f:
                lines = f.read().splitlines()
            self.assertEqual(len(lines), 2)
            self.assertEqual([json.loads(l)["image_id"] for l in lines], ["a", "b"])


if __name__ == "__main__":
    unittest.main()