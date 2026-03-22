import json
import tempfile
import unittest
from pathlib import Path
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
    def test_submit_detection_can_omit_language_key(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "book.png"
            image_path.write_bytes(b"png-bytes")

            with patch.object(
                detection_client.request,
                "urlopen",
                return_value=FakeResponse(201, {"entry": {"english": "book", "translated": "libro"}, "created": True}),
            ) as mocked_urlopen:
                status, payload = detection_client.submit_detection(
                    "book",
                    image=str(image_path),
                    server_base="http://127.0.0.1:9000",
                )

        self.assertEqual(status, 201)
        self.assertEqual(payload["entry"]["translated"], "libro")
        request_object = mocked_urlopen.call_args.args[0]
        body = json.loads(request_object.data.decode("utf-8"))
        self.assertEqual(body["english"], "book")
        self.assertEqual(body["imageFilename"], "book.png")
        self.assertTrue(body["imageBase64"])
        self.assertNotIn("languageKey", body)

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

    def test_get_selected_mode_reads_mode_payload(self):
        with patch.object(
            detection_client.request,
            "urlopen",
            return_value=FakeResponse(200, {"selectedMode": "game", "modes": ["learn", "game"]}),
        ) as mocked_urlopen:
            status, payload = detection_client.get_selected_mode(server_base="http://127.0.0.1:9000")

        self.assertEqual(status, 200)
        self.assertEqual(payload["selectedMode"], "game")
        requested_url = mocked_urlopen.call_args.args[0]
        self.assertEqual(requested_url, "http://127.0.0.1:9000/api/device/mode")

    def test_set_selected_mode_posts_mode_key(self):
        with patch.object(
            detection_client.request,
            "urlopen",
            return_value=FakeResponse(200, {"selectedMode": "game", "modes": ["learn", "game"]}),
        ) as mocked_urlopen:
            status, payload = detection_client.set_selected_mode("game", server_base="http://127.0.0.1:9000")

        self.assertEqual(status, 200)
        self.assertEqual(payload["selectedMode"], "game")
        request_object = mocked_urlopen.call_args.args[0]
        self.assertEqual(request_object.full_url, "http://127.0.0.1:9000/api/device/mode")
        self.assertEqual(json.loads(request_object.data.decode("utf-8")), {"modeKey": "game"})


if __name__ == "__main__":
    unittest.main()
