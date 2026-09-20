import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from kutarya_cascade.runtime import GenerationSettings, LlamaCppRuntime


class FakeLlamaHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/health":
            self._json({"status": "ok"})
        elif self.path == "/props":
            self._json({"model": "fake-qwen"})
        else:
            self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/apply-template":
            self._json({"prompt": "<user> " + payload["messages"][-1]["content"]})
        elif self.path == "/tokenize":
            self._json({"tokens": list(range(len(payload.get("content", "").split())))})
        elif self.path == "/v1/chat/completions":
            events = [
                {"choices": [{"delta": {"content": "SA"}}]},
                {"choices": [{"delta": {"content": "FE"}}]},
                {
                    "choices": [],
                    "usage": {"completion_tokens": 1},
                    "timings": {"prompt_ms": 4.0, "predicted_ms": 2.0, "predicted_per_second": 50.0},
                },
            ]
            body = "".join("data: " + json.dumps(event) + "\n\n" for event in events) + "data: [DONE]\n\n"
            encoded = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
        else:
            self.send_error(404)

    def _json(self, value):
        encoded = json.dumps(value).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class RuntimeIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeLlamaHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.runtime = LlamaCppRuntime(f"http://127.0.0.1:{cls.server.server_port}")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_health_props_template_tokenize_and_stream(self):
        self.assertTrue(self.runtime.health())
        self.assertEqual(self.runtime.props()["model"], "fake-qwen")
        messages = [{"role": "user", "content": "hello world"}]
        self.assertEqual(self.runtime.count_chat_tokens(messages), 3)
        result = self.runtime.generate(messages, GenerationSettings(max_tokens=4))
        self.assertEqual(result.text, "SAFE")
        self.assertIsNotNone(result.ttft_ms)
        self.assertEqual(result.prefill_ms, 4.0)
        self.assertEqual(result.output_tokens, 1)
        self.assertEqual(result.output_tokens_per_second, 50.0)


if __name__ == "__main__":
    unittest.main()
