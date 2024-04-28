import numpy as np
import matplotlib.pyplot as plt


points = np.subtract(1, np.power(np.arange(0.0, 1.0, 1/100, dtype=float), 8))

plt.subplot(311)
plt.plot(points)
plt.title("hei")



# linear_curve = curve_gen.generate_linear_curve()
# logarithmic_curve = curve_gen.generate_logarithmic_curve()
# geometric_curve = curve_gen.generate_geometric_curve()
#
# plt.figure(figsize=(12, 8))
#
# plt.subplot(311)
# plt.plot(linear_curve)
# plt.title('Linear Curve')
#
# plt.subplot(312)
# plt.plot(logarithmic_curve)
# plt.title('Logarithmic Curve')
#
# plt.subplot(313)
# plt.plot(geometric_curve)
# plt.title('Geometric Curve')

plt.tight_layout()
plt.show()