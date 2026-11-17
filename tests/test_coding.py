"""
test_coding.py - Pruebas unitarias para la codificación y decodificación RS(8,4).
"""
import random
import unittest
from itertools import combinations

from reedsolo import ReedSolomonError
from coding import encode_rs, decode_rs, RS_N


class TestCoding(unittest.TestCase):

    def setUp(self):
        self.raw_data = b"\x01\xAB\xCD\xEF"  # 4 bytes de prueba
        self.encoded_data = encode_rs(self.raw_data)

    def test_encode_length(self):
        """Verifica que la salida codificada tenga exactamente 8 bytes y sea de tipo bytes."""
        self.assertEqual(len(self.encoded_data), RS_N)
        self.assertIsInstance(self.encoded_data, bytes)

    def test_decode_clean(self):
        """Verifica la recuperación sin errores en el canal."""
        self.assertEqual(decode_rs(self.encoded_data), self.raw_data)

    def test_correct_one_byte_error(self):
        """Verifica la corrección de 1 byte corrompido, en cada una de las 8 posiciones."""
        for pos in range(RS_N):
            with self.subTest(pos=pos):
                corrupted = bytearray(self.encoded_data)
                corrupted[pos] ^= 0xFF
                self.assertEqual(decode_rs(bytes(corrupted)), self.raw_data)

    def test_correct_two_byte_errors_all_pairs(self):
        """Verifica la corrección del límite (2 bytes corrompidos) para las 28 parejas de posiciones (RF-4)."""
        for i, j in combinations(range(RS_N), 2):
            with self.subTest(i=i, j=j):
                corrupted = bytearray(self.encoded_data)
                corrupted[i] ^= 0xA5
                corrupted[j] ^= 0x5A
                self.assertEqual(decode_rs(bytes(corrupted)), self.raw_data)

    def test_correct_16_bits_in_two_bytes(self):
        """Verifica que 16 bits alterados concentrados en 2 bytes se corrigen."""
        corrupted = bytearray(self.encoded_data)
        corrupted[1] ^= 0xFF
        corrupted[6] ^= 0xFF
        self.assertEqual(decode_rs(bytes(corrupted)), self.raw_data)

    def test_three_single_bits_in_three_bytes_not_recovered(self):
        """
        Verifica que 3 bits sueltos en 3 bytes distintos superan la capacidad t=2:
        el decodificador lanza ReedSolomonError o devuelve una trama distinta (falsa corrección).
        """
        corrupted = bytearray(self.encoded_data)
        corrupted[0] ^= 0x01
        corrupted[3] ^= 0x01
        corrupted[6] ^= 0x01
        try:
            self.assertNotEqual(decode_rs(bytes(corrupted)), self.raw_data)
        except ReedSolomonError:
            pass

    def test_more_than_two_errors_behavior(self):
        """
        Con más de 2 bytes alterados la trama original NUNCA se recupera:
        o el decodificador lanza ReedSolomonError, o devuelve otra trama (falsa corrección).
        """
        corrupted = bytearray(self.encoded_data)
        corrupted[0] ^= 0x11
        corrupted[3] ^= 0x22
        corrupted[5] ^= 0x33
        try:
            self.assertNotEqual(decode_rs(bytes(corrupted)), self.raw_data)
        except ReedSolomonError:
            pass

    def test_false_correction_rate_on_random_words(self):
        """
        Contrasta la probabilidad teórica de falsa corrección con palabras aleatorias de 8 bytes:
        (1 + 8*255 + 28*255^2) / 2^32 ~ 4,2e-4. Se imprime el resultado para la memoria.
        """
        rng = random.Random(0)
        n, accepted = 100_000, 0
        for _ in range(n):
            word = bytes(rng.getrandbits(8) for _ in range(RS_N))
            try:
                decode_rs(word)
                accepted += 1
            except ReedSolomonError:
                pass
        rate = accepted / n
        print(f"\nFalsas correcciones: {accepted}/{n} = {rate:.2e} (teoría 4.2e-4)")
        self.assertLess(abs(rate - 4.2e-4), 2.5e-4)  # margen amplio: solo detecta errores gruesos

    def test_invalid_lengths(self):
        """Verifica las excepciones de longitud en encode_rs y decode_rs."""
        with self.assertRaises(ValueError):
            encode_rs(b"\x01\x02\x03")          # 3 bytes en lugar de 4
        with self.assertRaises(ValueError):
            decode_rs(b"\x01\x02\x03\x04\x05")  # 5 bytes en lugar de 8


if __name__ == "__main__":
    unittest.main()
