"""
test_crypto.py - Pruebas de crypto.py.
Requisitos relacionados: RF-3, RS-1, RS-3, RS-4.
"""
import unittest

import crypto


class TestCrypto(unittest.TestCase):

    def test_keypair_sizes_and_uniqueness(self):
        """Las claves privada y pública tienen 32 bytes y dos llamadas dan pares distintos."""
        sk1, pk1 = crypto.generate_keypair()
        sk2, pk2 = crypto.generate_keypair()

        self.assertEqual(len(sk1), crypto.KEY_SIZE)
        self.assertEqual(len(pk1), crypto.KEY_SIZE)
        self.assertNotEqual(sk1, sk2)
        self.assertNotEqual(pk1, pk2)

    def test_shared_secret_is_symmetric(self):
        """S calculado por Alice (esk, PK_B) y por Bob (SK_B, epk) es idéntico."""
        sk_b, pk_b = crypto.generate_keypair()        # par de Bob
        esk_a, epk_a = crypto.generate_keypair()      # par efímero de Alice

        s_alice = crypto.compute_shared_secret(esk_a, pk_b)
        s_bob = crypto.compute_shared_secret(sk_b, epk_a)

        self.assertEqual(s_alice, s_bob)

    def test_shared_secret_invalid_inputs(self):
        """Claves con longitud incorrecta lanzan ValueError."""
        sk, pk = crypto.generate_keypair()

        with self.assertRaises(ValueError):
            crypto.compute_shared_secret(b"\x01" * 31, pk)   # privada de 31 bytes
        with self.assertRaises(ValueError):
            crypto.compute_shared_secret(sk, b"\x01" * 33)   # pública de 33 bytes

    def test_low_order_public_key_rejected(self):
        """Una clave pública de orden bajo (32 ceros) lanza ValueError."""
        sk, _ = crypto.generate_keypair()

        with self.assertRaises(ValueError):
            crypto.compute_shared_secret(sk, b"\x00" * 32)

    def test_derive_seed_size_and_determinism(self):
        """La semilla tiene SEED_SIZE bytes y es la misma con las mismas entradas."""
        _, pk_b = crypto.generate_keypair()
        esk, epk = crypto.generate_keypair()
        s = crypto.compute_shared_secret(esk, pk_b)

        seed1 = crypto.derive_seed(s, epk, pk_b)
        seed2 = crypto.derive_seed(s, epk, pk_b)

        self.assertEqual(len(seed1), crypto.SEED_SIZE)
        self.assertEqual(seed1, seed2)

    def test_seed_depends_on_context(self):
        """Cambiar epk, pk_b o S cambia la semilla."""
        _, pk_b = crypto.generate_keypair()
        esk, epk = crypto.generate_keypair()
        s = crypto.compute_shared_secret(esk, pk_b)
        _, otra_clave = crypto.generate_keypair()             # una clave pública cualquiera, distinta

        base = crypto.derive_seed(s, epk, pk_b)
        self.assertNotEqual(base, crypto.derive_seed(s, otra_clave, pk_b))       # otro epk
        self.assertNotEqual(base, crypto.derive_seed(s, epk, otra_clave))        # otro pk_b
        self.assertNotEqual(base, crypto.derive_seed(b"\x02" * 32, epk, pk_b))   # otro secreto S

    def test_sender_and_receiver_get_same_seed(self):
        """sender_derive_seed y receiver_derive_seed coinciden (RF-3, RS-3)."""
        sk_b, pk_b = crypto.generate_keypair()

        seed_alice, epk = crypto.sender_derive_seed(pk_b)
        seed_bob = crypto.receiver_derive_seed(sk_b, pk_b, epk)

        self.assertEqual(seed_alice, seed_bob)

    def test_wrong_private_key_gives_different_seed(self):
        """Con una clave privada incorrecta, Bob obtiene otra semilla (base de RS-1)."""
        sk_b, pk_b = crypto.generate_keypair()
        sk_otra, _ = crypto.generate_keypair()                # la clave privada de otra persona

        seed_alice, epk = crypto.sender_derive_seed(pk_b)
        seed_incorrecta = crypto.receiver_derive_seed(sk_otra, pk_b, epk)

        self.assertNotEqual(seed_alice, seed_incorrecta)

    def test_sender_returns_only_seed_and_epk(self):
        """sender_derive_seed devuelve solo (semilla, epk), sin ningún secreto adicional (RS-4)."""
        _, pk_b = crypto.generate_keypair()

        result = crypto.sender_derive_seed(pk_b)
        self.assertEqual(len(result), 2)

        seed, epk = result
        self.assertEqual(len(seed), crypto.SEED_SIZE)
        self.assertEqual(len(epk), crypto.KEY_SIZE)

    def test_keypair_from_private_bytes_is_reproducible(self):
        """La misma clave privada da siempre el mismo par."""
        priv = bytes(range(32))
        a = crypto.generate_keypair(priv)
        b = crypto.generate_keypair(priv)
        self.assertEqual(a, b)
        self.assertEqual(a[0], priv)
        self.assertEqual(len(a[1]), 32)

    def test_keypair_from_private_bytes_invalid_length(self):
        """Una clave privada de longitud incorrecta lanza ValueError."""
        with self.assertRaises(ValueError):
            crypto.generate_keypair(b"corta")

    def test_keypair_without_argument_is_random(self):
        """Sin argumento, dos llamadas dan pares distintos."""
        self.assertNotEqual(crypto.generate_keypair(), crypto.generate_keypair())

if __name__ == "__main__":
    unittest.main()