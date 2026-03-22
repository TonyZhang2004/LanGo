import json
import unittest
from unittest.mock import patch

from hardware import detection_client


class FakeResponse:
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class DetectionClientTests(unittest.TestCase):
    def test_get_history_reads_language_specific_history(self):
        with patch.object(
            detection_client.request,
            "urlopen",
            return_value=FakeResponse(200, {"entries": [{"id": "1", "english": "book"}]}),
        ) as mocked_urlopen:
            status, payload = detection_client.get_history("spanish", server_base="http://127.0.0.1:9000")

        self.assertEqual(status, 200)
        self.assertEqual(payload["entries"][0]["english"], "book")
        requested_url = mocked_urlopen.call_args.args[0]
        self.assertEqual(requested_url, "http://127.0.0.1:9000/api/history?language=spanish")


if __name__ == "__main__":
    unittest.main()
