import sys
import numpy as np

import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QGraphicsItemGroup

from common import get_nearest_idx, max_within_range

from offset_view_settings_ui import Ui_OffsetViewSettings


# import timer for time measurement ============================================
from timeit import default_timer as timer


class OffsetView(QWidget):
    def __init__(self, parent = None) -> None:
        super().__init__(parent)
       
        self.plot = pg.PlotWidget()
        self.plot.setLabel('bottom', 'mass', units='centered AMU')
        # Create a parent QGraphicsItem to hold curve items
        self.curve_parent = QGraphicsItemGroup()
        self.plot.addItem(self.curve_parent)

        self.curves = []
        self.set_xy([], [])
        self.set_peaks([])

        # self.plot.setTitle('Peaks preview')
        # self.plot.getAxis('left').setTicks([])  # make tick labels invisible
        self.plot.enableAutoRange(axis='y')     # autoscale of y axis
        self.plot.setAutoVisible(y=True)        # to take into acount only visible part
        self.plot.showGrid(x=True, y=True)
        self.legend = self.plot.addLegend()

        # Load the form created by Qt Designer
        form_widget = QWidget()         # an widget instance to hold the form
        self.form = Ui_OffsetViewSettings()           # generate the form               
        self.form.setupUi(form_widget)  # sets up the 'form' inside of the widget 

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        layout.addWidget(self.plot)        # add the plot to the main layout
        layout.addWidget(form_widget)      # add the form to the main layout

        self.is_visible = True
        
        self.connectSignalsSlots()


    def connectSignalsSlots(self):
        self.form.doubleSpinBox_range.valueChanged.connect(self.update)
        self.form.doubleSpinBox_offset.valueChanged.connect(self.update)
        self.form.checkBox_normalize.stateChanged.connect(self.update)
        
    
    def clear(self):
        for i, curve in enumerate(self.curves):
            if i == 0:
                self.plot.plotItem.vb.removeItem(curve)
            elif i == len(self.curves) - 1:
                self.plot.plotItem.vb.removeItem(curve)
            else:
                curve.setParentItem(None)
        self.legend.clear()
        self.curves = []

        
    def _there_are_data(self):
        return len(self.x_mass) > 0 and len(self.y_counts) > 0 and len(self.peak_list) > 0
        
        
    def update(self):
        if not self.is_visible:
            return
     
        self.clear()
        # if there are data to plot
        if self._there_are_data():
            n_peaks = len(self.peak_list)
            normalize = self.form.checkBox_normalize.isChecked()
            range_width = self.form.doubleSpinBox_range.value()
            plot_y_offset = self.form.doubleSpinBox_offset.value()
            
            for i, (peak_mass, peak_name) in enumerate(zip(self.peak_list, self.peak_names)):
                x = self.x_mass - peak_mass
                nearest = get_nearest_idx(self.x_mass, peak_mass)
                y_max = max_within_range(self.y_counts, nearest, 5)
                if normalize:
                    # to avoid zero division
                    if self.y_counts[y_max] != 0:
                        y = self.y_counts / self.y_counts[y_max]
                else:
                    y = self.y_counts            

                # y = self.y_counts            
                    
                curve = pg.PlotCurveItem(pen=({'color': (i, n_peaks*1.3), 'width': 1}),
                                        skipFiniteCheck=True, name=peak_name)
                curve.setData(x, y)
                curve.setPos(0, i*plot_y_offset)
                
                # to speed up the plotting operation the first and the last curve
                # are added directly to the plot, the rest are added to the parent item
                if i == 0:
                    self.plot.addItem(curve)
                elif i == len(self.peak_list) - 1:
                    self.plot.addItem(curve)
                else:
                    curve.setParentItem(self.curve_parent)  # Set the parent item for the curve
                    # self.plot.addItem(curve)              # time consuming operation to use it for all curves
                    self.legend.addItem(curve, name=peak_name) # need to be added to the legend
                    
                self.curves.append(curve)

            self.plot.setXRange(-range_width/2, +range_width/2)
            self.plot.enableAutoRange(axis='y')     # autoscale of y axis


    def set_xy(self, x, y):
        self.x_mass = x
        self.y_counts = y


    def set_peaks(self, peaks, names=None):
        self.peak_list = peaks
        if names:
            self.peak_names = names     # names filled to have legend   
        else: 
            # if names are not defined take ones from 'peaks'
            self.peak_names = [str(x) for x in peaks]
            

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.size().width() < 55:
            self.is_visible = False # hide the plot
        else:
            if not self.is_visible:
                self.is_visible = True
                self.update()
        


# to test this module
if __name__ == "__main__":
    app = QApplication(sys.argv)

    win = OffsetView()
    data = np.loadtxt(r'data\231012_1m0001.asc', skiprows=10)
    win.set_xy(data[:, 0], data[:, 1])
    win.set_peaks([128.08, 256.15, 384.2, 512.2])

    win.show()

    sys.exit(app.exec_())
