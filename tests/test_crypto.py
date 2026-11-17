"""
test_crypto.py - Pruebas de crypto.py (ESQUELETO).

Cuando implementes crypto.py, quita el decorador @unittest.skip y rellena cada prueba.
Requisitos relacionados: RF-3, RS-1, RS-3, RS-4.
"""
import unittest

import crypto


@unittest.skip("Pendiente: implementar crypto.py")
class TestCrypto(unittest.TestCase):

    def test_keypair_sizes_and_uniqueness(self):
        """Las claves privada y pública tienen 32 bytes y dos llamadas dan pares distintos."""
        # TODO: sk1, pk1 = crypto.generate_keypair(); sk2, pk2 = crypto.generate_keypair()
        # TODO: comprobar len == crypto.KEY_SIZE y que sk1 != sk2
        pass

    def test_shared_secret_is_symmetric(self):
        """S calculado por Alice (esk, PK_B) y por Bob (SK_B, epk) es idéntico."""
        # TODO: generar par de Bob y par efímero de Alice; comparar ambos secretos
        pass

    def test_shared_secret_invalid_inputs(self):
        """Claves con longitud incorrecta lanzan ValueError."""
        # TODO: compute_shared_secret(b"\x01" * 31, <pública válida>) -> ValueError
        pass

    def test_low_order_public_key_rejected(self):
        """Una clave pública de orden bajo (32 ceros) lanza ValueError."""
        # TODO: compute_shared_secret(<privada válida>, b"\x00" * 32) -> ValueError
        pass

    def test_derive_seed_size_and_determinism(self):
        """La semilla tiene SEED_SIZE bytes y es la misma con las mismas entradas."""
        # TODO: derive_seed(S, epk, pk_b) dos veces; comprobar longitud e igualdad
        pass

    def test_seed_depends_on_context(self):
        """Cambiar epk o pk_b (o S) cambia la semilla."""
        # TODO: tres variantes de entrada -> tres semillas distintas
        pass

    def test_sender_and_receiver_get_same_seed(self):
        """sender_derive_seed y receiver_derive_seed coinciden (RF-3, RS-3)."""
        # TODO: sk_b, pk_b = generate_keypair(); seed_a, epk = sender_derive_seed(pk_b)
        # TODO: seed_b = receiver_derive_seed(sk_b, pk_b, epk); assertEqual
        pass

    def test_wrong_private_key_gives_different_seed(self):
        """Con una clave privada incorrecta, Bob obtiene otra semilla (base de RS-1)."""
        # TODO: usar la privada de otro par en receiver_derive_seed y comprobar que difiere
        pass

    def test_sender_does_not_return_private_key(self):
        """sender_derive_seed devuelve solo (semilla, epk) y ningún secreto adicional (RS-4)."""
        # TODO: comprobar len(resultado) == 2 y que la privada efímera no aparece en el resultado
        pass


if __name__ == "__main__":
    unittest.main()
