import base64
import hashlib
import hmac
import multiprocessing

try:
    import cPickle as pickle
except ImportError:
    import pickle

import socket
import unittest

from rope.base.oi import doa


def cve_2014_3539_attacker(data_port, payload):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", data_port))
    s_file = s.makefile("wb")
    s_file.write(payload)
    s.close()


class DOATest(unittest.TestCase):
    def try_CVE_2014_3539_exploit(self, receiver, payload):
        # Simulated attacker writing to the socket
        # Assume the attacker guesses the port correctly; 3037 is used by
        # default if it is available.
        attacker_proc = multiprocessing.Process(
            target=cve_2014_3539_attacker, args=(receiver.data_port, payload)
        )

        attacker_proc.start()
        received_objs = list(receiver.receive_data())
        attacker_proc.join()
        return received_objs

    def test_CVE_2014_3539_no_encoding(self):
        # Attacker sends pickled data to the receiver socket.
        receiver = doa._SocketReceiver()

        payload = pickle.dumps("def foo():\n    return 123\n")
        received_objs = self.try_CVE_2014_3539_exploit(receiver, payload)

        # Make sure the exploit did not run
        self.assertEqual(0, len(received_objs))

    def test_CVE_2014_3539_signature_mismatch(self):
        # Attacker sends well-formed data with an incorrect signature.
        receiver = doa._SocketReceiver()

        pickled_data = pickle.dumps(
            "def foo():\n    return 123\n", pickle.HIGHEST_PROTOCOL
        )
        digest = hmac.new(b"invalid-key", pickled_data, hashlib.sha256).digest()
        payload = (
            base64.b64encode(digest) + b":" + base64.b64encode(pickled_data) + b"\n"
        )
        received_objs = self.try_CVE_2014_3539_exploit(receiver, payload)

        # Make sure the exploit did not run
        self.assertEqual(0, len(received_objs))

    def test_CVE_2014_3539_sanity(self):
        # Tests that sending valid, signed data on the socket does work.
        receiver = doa._SocketReceiver()

        pickled_data = base64.b64encode(
            pickle.dumps("def foo():\n    return 123\n", pickle.HIGHEST_PROTOCOL)
        )
        digest = hmac.new(receiver.key, pickled_data, hashlib.sha256).digest()
        payload = base64.b64encode(digest) + b":" + pickled_data + b"\n"
        received_objs = self.try_CVE_2014_3539_exploit(receiver, payload)

        # Make sure the exploit did not run
        self.assertEqual(1, len(received_objs))

    def test_compare_digest_compat(self):
        self.assertTrue(doa._compat_compare_digest("", ""))
        self.assertTrue(doa._compat_compare_digest("abc", "abc"))
        self.assertFalse(doa._compat_compare_digest("abc", "abd"))
        self.assertFalse(doa._compat_compare_digest("abc", "abcd"))
