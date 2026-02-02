"""
Módulo de animaciones Manim
Cada tipo de animación está en su propio archivo
"""
# Importar todas las animaciones para que se registren automáticamente
from .quote import QuoteAnimation  # noqa: F401
from .bar_chart import BarChartAnimation  # noqa: F401
from .modern_bar_chart import ModernBarChartAnimation  # noqa: F401

# Futuras animaciones (comentadas hasta que se implementen):
# from .line_chart import LineChartAnimation
# from .histogram import HistogramAnimation
# from .scatter_plot import ScatterPlotAnimation
# from .pie_chart import PieChartAnimation
# from .xy_chart import XYChartAnimation

__all__ = [
    'QuoteAnimation',
    'BarChartAnimation',
    'ModernBarChartAnimation',
    # 'LineChartAnimation',
    # 'HistogramAnimation',
    # 'ScatterPlotAnimation',
    # 'PieChartAnimation',
    # 'XYChartAnimation',
]

