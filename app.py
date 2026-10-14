import argparse
import ast
import json
import math
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STATIC_FILES = {
	"/": (ROOT / "index.html", "text/html; charset=utf-8"),
	"/style.css": (ROOT / "style.css", "text/css; charset=utf-8"),
	"/app.js": (ROOT / "app.js", "text/javascript; charset=utf-8"),
}
MAX_STEPS = 10000
FUNCTIONS = {
	name: getattr(math, name)
	for name in (
		"acos", "asin", "atan", "atan2", "ceil", "cos", "cosh", "exp",
		"fabs", "floor", "log", "log10", "sin", "sinh", "sqrt", "tan",
		"tanh",
	)
}
FUNCTIONS.update({"abs": abs, "max": max, "min": min})
CONSTANTS = {"e": math.e, "pi": math.pi}
ALLOWED_NODES = (
	ast.Expression,
	ast.BinOp,
	ast.UnaryOp,
	ast.Call,
	ast.Name,
	ast.Load,
	ast.Constant,
	ast.Add,
	ast.Sub,
	ast.Mult,
	ast.Div,
	ast.FloorDiv,
	ast.Mod,
	ast.Pow,
	ast.UAdd,
	ast.USub,
)


def compile_expression(expression):
	if not isinstance(expression, str) or not expression.strip() or len(expression) > 256:
		raise ValueError("Expression must contain 1 to 256 characters.")
	try:
		tree = ast.parse(expression, mode="eval")
	except (SyntaxError, TypeError) as error:
		raise ValueError("Enter a valid expression in t and y.") from error

	for node in ast.walk(tree):
		if not isinstance(node, ALLOWED_NODES):
			raise ValueError("Expression contains an unsupported operation.")
		if isinstance(node, ast.Constant):
			if type(node.value) not in (int, float):
				raise ValueError("Only numeric constants are supported.")
			try:
				if not math.isfinite(float(node.value)):
					raise ValueError("Numeric constants must be finite.")
			except OverflowError as error:
				raise ValueError("Numeric constants must be finite.") from error
		if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
			if not isinstance(node.right, ast.Constant) or abs(node.right.value) > 1000:
				raise ValueError("Powers must use a numeric exponent between -1000 and 1000.")
		if isinstance(node, ast.Name) and node.id not in {"t", "y", *FUNCTIONS, *CONSTANTS}:
			raise ValueError(f"Unknown name: {node.id}")
		if isinstance(node, ast.Call) and (
			not isinstance(node.func, ast.Name)
			or node.func.id not in FUNCTIONS
			or node.keywords
		):
			raise ValueError("Only supported math functions can be called.")

	return compile(tree, "<ode-expression>", "eval")


def solve_ode(expression, t0, y0, t_end, steps, method="RK4"):
	"""Solve the scalar initial-value problem y' = f(t, y)."""
	if method not in {"Euler", "Heun", "RK4"}:
		raise ValueError("Choose Euler, Heun, or RK4.")
	if isinstance(steps, bool) or not isinstance(steps, int) or not 1 <= steps <= MAX_STEPS:
		raise ValueError(f"Steps must be an integer from 1 to {MAX_STEPS}.")
	try:
		t0, y0, t_end = float(t0), float(y0), float(t_end)
	except (TypeError, ValueError, OverflowError) as error:
		raise ValueError("Start, initial value, and end must be numbers.") from error
	if not all(math.isfinite(value) for value in (t0, y0, t_end)):
		raise ValueError("Start, initial value, and end must be finite numbers.")

	code = compile_expression(expression)
	function_values = {**FUNCTIONS, **CONSTANTS}

	def derivative(t, y):
		try:
			value = eval(code, {"__builtins__": {}, **function_values}, {"t": t, "y": y})
			if isinstance(value, bool) or not isinstance(value, (int, float)):
				raise ValueError("The derivative must be numeric.")
			value = float(value)
		except (ArithmeticError, ValueError, TypeError, OverflowError) as error:
			raise ValueError(f"Could not evaluate the expression at t = {t:g}.") from error
		if not math.isfinite(value):
			raise ValueError(f"The derivative is not finite at t = {t:g}.")
		return value

	step_size = (t_end - t0) / steps
	points = [{"t": t0, "y": y0}]
	t, y = t0, y0
	for index in range(steps):
		h = step_size
		if method == "Euler":
			next_y = y + h * derivative(t, y)
		elif method == "Heun":
			first = derivative(t, y)
			second = derivative(t + h, y + h * first)
			next_y = y + h * (first + second) / 2
		else:
			first = derivative(t, y)
			second = derivative(t + h / 2, y + h * first / 2)
			third = derivative(t + h / 2, y + h * second / 2)
			fourth = derivative(t + h, y + h * third)
			next_y = y + h * (first + 2 * second + 2 * third + fourth) / 6

		if not math.isfinite(next_y):
			raise ValueError(f"The solution became non-finite at step {index + 1}.")
		t = t_end if index == steps - 1 else t0 + (index + 1) * step_size
		y = next_y
		points.append({"t": t, "y": y})

	return points


class ODEServer(ThreadingHTTPServer):
	daemon_threads = True
	allow_reuse_address = True


class RequestHandler(BaseHTTPRequestHandler):
	def _send(self, status, body, content_type):
		self.send_response(status)
		self.send_header("Content-Type", content_type)
		self.send_header("Content-Length", str(len(body)))
		self.send_header("X-Content-Type-Options", "nosniff")
		self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'")
		self.end_headers()
		self.wfile.write(body)

	def do_GET(self):
		resource = STATIC_FILES.get(self.path)
		if resource is None:
			self._send(404, b"Not found", "text/plain; charset=utf-8")
			return
		path, content_type = resource
		try:
			self._send(200, path.read_bytes(), content_type)
		except OSError:
			self._send(500, b"The application files could not be read.", "text/plain; charset=utf-8")

	def do_POST(self):
		if self.path != "/api/solve":
			self._send(404, b'{"error":"Not found."}', "application/json; charset=utf-8")
			return
		try:
			length = int(self.headers.get("Content-Length", "0"))
			if not 0 < length <= 16384:
				raise ValueError("Request body must be between 1 and 16384 bytes.")
			data = json.loads(self.rfile.read(length))
			if not isinstance(data, dict):
				raise ValueError("Request body must be a JSON object.")
			points = solve_ode(
				data.get("expression"), data.get("t0"), data.get("y0"),
				data.get("t_end"), data.get("steps"), data.get("method", "RK4"),
			)
			body = json.dumps({"points": points}, allow_nan=False).encode("utf-8")
			self._send(200, body, "application/json; charset=utf-8")
		except (ValueError, TypeError, json.JSONDecodeError) as error:
			body = json.dumps({"error": str(error)}).encode("utf-8")
			self._send(400, body, "application/json; charset=utf-8")

	def log_message(self, format, *args):
		print(f"{self.address_string()} - {format % args}")


def main():
	parser = argparse.ArgumentParser(description="Run the browser-based ODE solver.")
	parser.add_argument("--host", default="127.0.0.1", help="Interface to bind (default: 127.0.0.1)")
	parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
	args = parser.parse_args()
	server = ODEServer((args.host, args.port), RequestHandler)
	print(f"ODE solver ready at http://{args.host}:{args.port}")
	try:
		server.serve_forever()
	except KeyboardInterrupt:
		print("\nStopping ODE solver.")
	finally:
		server.server_close()


if __name__ == "__main__":
	main()
