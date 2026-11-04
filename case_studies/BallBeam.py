import numpy as np
def dynamics(t, x, u):
    g = 9.8
    r, dr = x[0], x[1]
    alpha = u[0] if isinstance(u, (list, np.ndarray)) else u
    ddr = (5/7) * g * np.sin(alpha)
    return np.array([dr, ddr])
