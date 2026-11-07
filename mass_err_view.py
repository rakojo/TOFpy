from __future__ import annotations

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt
from pyqtgraph import PlotWidget

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from tree_items import PeakItem


POINT_STYLE = {'pen': None, 
                'symbolBrush': (0, 0, 255, 100),
                'symbolPen': 'w', 
                'symbol': '+',
                'symbolSize': 14
                }



class MassErrView(QWidget):
# class MassErrPlot(Ui_MassErrPlot, QWidget):
    """
    This is window to to plot calibration peaks mass deviation. 
    """
    def __init__(self, parent=None):
        super().__init__(parent)   # parent is applied to QWidget (inherited)
        # self.setupUi(self)
        
        style = POINT_STYLE
        style['symbolBrush'] = 'w' 
        self.plot = PlotWidget()
        self.scatter = self.plot.plot(**style)
        
        style['symbolBrush'] = 'r' 
        style['symbol'] = 'x'
        self.scatter_calibration = self.plot.plot(**style)

        
        style = {'color': 'gray', 'font-size': '8pt'}
        self.plot.setLabel('left', 'exp. - ref.mass (AMU)', **style)
        self.plot.setLabel('bottom', 'exp. mass (AMU)', **style)
        self.plot.showGrid(x=True, y=True)
        
        
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        layout.addWidget(self.plot)        # add the plot to the main layout
        
        self.connectSignalsSlots()
        

    def connectSignalsSlots(self):
        pass
        # Signal the tree widget (from outside, from another window)
        # self.tree.currentItemChanged.connect(self.update)
        # self.tree.itemChanged.connect(self.update)


    def set_main_plot(self, main_plot):
        self.main_plot = main_plot
        self.main_plot.sigRangeChanged.connect(self.resscale)


    def set_peaks(self, peaks : list[PeakItem]):
        self.peak_list = peaks
        self.update()


    def update(self):
        xs = []
        ys = []
        if len(self.peak_list) > 0:
            for peak in self.peak_list:
                # test if teoretical mass is defined (e.g. by IPmolecule module)
                if peak.peak.get_xy_main_iso():
                    x, _ = peak.peak.get_xy()
                    x_main_iso, _ = peak.peak.get_xy_main_iso()
                    if not x_main_iso:
                        raise ValueError('Theoretical mass is not defined for peak: ', peak.text(0))
                    mol_mass = x - x_main_iso
                    xs.append(x)
                    ys.append(mol_mass)
        
        self.scatter.setData(xs, ys)
        

    def resscale(self):
        '''
        To follow changeing of the range in the plot of 'sepectra_plot'
        '''        
        vb1 = self.plot.plotItem.getViewBox()
        vb2 = self.main_plot.plotItem.getViewBox()       
        vb1.setXRange(*vb2.viewRange()[0], vb2.state['defaultPadding'])        

    
    def show_calibration(self, x, y):
        self.scatter_calibration.setData(x, y)
        
    def hide_calibration(self):
        self.scatter_calibration.setData([], [])