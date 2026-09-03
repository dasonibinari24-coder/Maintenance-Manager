"""Local HTTP endpoint for the embedded portal Q&A widget."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

from qa_backend import QAConfigurationError, ask


class QAHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if self.path != "/qa/ask":
            self.send_error(404)
            return
        try:
            raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            question = str(json.loads(raw).get("question", "")).strip()
            if not question:
                self.respond(400, {"error": "질문을 입력해 주세요."})
                return
            answer, sources = ask(question)
            self.respond(200, {"answer": answer, "sources": sources})
        except QAConfigurationError as error:
            self.respond(503, {"error": str(error)})
        except Exception:
            self.respond(500, {"error": "답변 처리 중 오류가 발생했습니다."})

    def respond(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8092), QAHandler).serve_forever()
