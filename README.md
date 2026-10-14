# ODE Studio

A browser-based solver for scalar initial-value problems of the form `y' = f(t, y)`. It supports the explicit Euler, Heun, and classical fourth-order Runge–Kutta (RK4) methods, and displays the solution curve and computed values.

## Run

Requires Python 3.10 or newer. No third-party packages are needed.

```bash
python app.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Choose a method, enter the initial conditions and time interval, then select **Compute solution**. Stop the server with `Ctrl+C`.

To use a different port or network interface, pass `--port` or `--host`, for example `python app.py --host 0.0.0.0 --port 8080`.

## Equation syntax

Expressions can use `t`, `y`, the constants `pi` and `e`, arithmetic (`+`, `-`, `*`, `/`, `//`, `%`, `**`), and the functions `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2`, `sinh`, `cosh`, `tanh`, `exp`, `log`, `log10`, `sqrt`, `abs`, `fabs`, `floor`, `ceil`, `min`, and `max`. The expression is validated and evaluated with a restricted set of Python syntax; built-ins and arbitrary code are unavailable.

The step count is the number of equal intervals, so the result contains `n + 1` sample points, including both interval endpoints. Maximum step count is 10,000.

## Tests

```bash
python -m unittest
```
