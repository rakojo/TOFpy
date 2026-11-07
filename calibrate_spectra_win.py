from __future__ import annotations

from calibrate_spectra_ui import Ui_CalibrateSpectra
from PyQt5.QtWidgets import QWidget, QMessageBox, QAction, QMenu, QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QClipboard
from numpy.polynomial import Polynomial as P
import numpy as np

from common import get_mass
from logging_config import logger

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from peak import Peak
    from tree_items import SpectraItem
    from tree import SpectrasTree


POINT_STYLE = {'pen': None, 
                'symbolPen': 'r', 
                'symbol': 'x',
                'symbolSize': 10
                }


class CalibrateSpectraWin(Ui_CalibrateSpectra, QWidget):
    """
    This is window to contorl calibration of spectra procedure. 
    Parameter 'tree' is the reference to 'class SpectrasTree' widget.
    """
    def __init__(self, tree : SpectrasTree, parent=None):
        super().__init__(parent)   # parent is applied to QWidget (inherited)
        self.setupUi(self)
        self.win_position = None    # used to remember change in windoww position
        # Set the window flag to keep it always on top
        # self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Window \
        #                     | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

        self.tree : SpectrasTree = tree
        self.peaks : list[Peak] = None
        self.coefs = []
        self.new_coefs = []
        self.item_spectra : SpectraItem = None
        self.peaks = []
        self.exp_masses = None
        self.teo_masses = None
        self.exp_times = None
        
        self.line = self.plot.plot(pen={'color': 'r', 'width': 1})

        style = POINT_STYLE
        style['symbolBrush'] = 'r'            # set fill color of symbols
        self.scatter = self.plot.plot(**style)  # create scatter item for marking peaks
        
        style = {'color': '#FFF', 'font-size': '10pt'}
        self.plot.setLabel('left', 'mass (AMU)', **style)
        self.plot.setLabel('bottom', 'time (us)', **style)
        self.plot.showGrid(x=True, y=True)


        self.connectSignalsSlots()
        

    def connectSignalsSlots(self):
        self.push_button_fit.pressed.connect(self.on_fit)
        self.push_button_apply.pressed.connect(self.on_apply)
        self.spin_box_order.valueChanged.connect(self.on_change_order)
        
        # Signal the tree widget (from outside, from another window)
        self.tree.currentItemChanged.connect(self.on_tree_current_changed)
        self.tree.itemChanged.connect(self.on_tree_itemChanged)
        
        
    def set_err_view(self, err_view):
        self.err_view = err_view
            
            
    def fetch_and_filter_peaks(self):
        peaks = self.tree.get_peaks(checked=True)   # include only checked peaks
        self.peaks = []
        # filter out the ones without the teoretical mass value
        for peak in peaks:
            if peak.peak.get_xy_main_iso():
                self.peaks.append(peak)


    def read_tree_peaks_data(self):
        self.exp_masses = None
        self.teo_masses = None
        self.exp_times = None
        self.fetch_and_filter_peaks()
        #  are there some relevant peaks after filtering?
        if self.peaks:        
            exp_masses = []
            teo_masses = []
            exp_times = []
            for peak in self.peaks:
                exp_masses.append(peak.peak.get_xy()[0])  # [0] mass componet (x-axis)
                teo_masses.append(peak.peak.get_xy_main_iso()[0])
                exp_times.append(peak.peak.get_t())
                
            self.exp_masses = np.array(exp_masses)
            self.teo_masses = np.array(teo_masses)
            self.exp_times = np.array(exp_times)

    
    def read_tree_spectra_data(self):
        self.item_spectra = self.tree.get_spectra_parent()
        self.tof = self.item_spectra.spectra
        self.coefs = []
        self.coefs = self.tof.get_coeficients()
        self.new_coefs = self.coefs
        # self.spin_box_order.setValue(len(self.coefs)-1)
            
        
    def update(self):
        # missing some information - it is not possible to show
        if not len(self.new_coefs) or not self.isVisible() or not self.peaks: 
            self.tree.plot.mass_err_view.hide_calibration()
            self.label_coefs.setText('')
            self.line.setData([], [])
            self.scatter.setData([], [])
            return
        
        # fill polynom label text
        p = P(list(reversed(self.new_coefs))) # the numpy.polynomial.Polynomial is reversed
        print_coefs = f"{p:unicode}"
        self.label_coefs.setText(print_coefs)

        self.scatter.setData(self.exp_times, self.teo_masses)

        xs = np.linspace(min(self.exp_times), max(self.exp_times), 100)
        self.line.setData(xs, get_mass(xs, self.new_coefs))
        
        x = p(self.exp_times)
        y = x - self.teo_masses
        self.tree.plot.mass_err_view.show_calibration(x, y)


    def on_fit(self):
        order = self.spin_box_order.value() # order of pylynom to use for the fit
        points_num = len(self.teo_masses)   # fitting points number
        if order < points_num:
            self.new_coefs = np.polyfit(self.exp_times, self.teo_masses, order)
            self.update()
        else:
            self.dlg = QMessageBox(text=f"At least {order + 1 } poins are needed to perform the fit!")
            self.dlg.show()


    def on_apply(self):
        self.coefs = self.new_coefs

        # calibrate all checked or just the current spectra        
        if self.check_box_to_checked.isChecked():
            items = self.tree.get_checked_spectras()    # all checked
        else:
            items = [self.item_spectra]                 # just current

        for item in items:
            item.spectra.set_coeficients_and_recalibrate(self.new_coefs)
            peaks = self.tree.get_peaks(item, False)
            # recalibrate all peaks under this spectra in the tree
            for peak in peaks:
                x, y = peak.peak.get_xy()
                t = peak.peak.get_t()
                x = get_mass(t, self.new_coefs)
                peak.peak.set_xy(x, y)
                
            logger.info(f"Calibrated spectra: '{item.text(0)}', {self.label_coefs.text()}")

        
        self.update()
        self.tree.plot.update()
        self.tree.plot.update_lines()


    def on_change_order(self):
        pass
        
    
    # Slot for tree widget item chanaged signal
    def on_tree_current_changed(self):
        if self.isVisible(): 
            # when currently selected spectra in tree is changes
            if self.item_spectra != self.tree.get_spectra_parent():
                self.read_tree_spectra_data()
                self.read_tree_peaks_data()

        self.update()
        
        
    def on_tree_itemChanged(self):
        if self.isVisible(): 
            self.read_tree_peaks_data()
            self.update()


    def copy_expression_to_cliboard(self):
        '''
        Copy the expression of the polynomial to the clipboard
        '''    
        txt = self.label_coefs.text()
        clipboard = QApplication.clipboard()
        clipboard.setText(txt, QClipboard.Clipboard)


    def contextMenuEvent(self, event):
        context_menu = QMenu(self)
        
        copy_expresion_action = QAction("Copy expression", self)
        copy_expresion_action.triggered.connect(self.copy_expression_to_cliboard)
        context_menu.addAction(copy_expresion_action)

        action = context_menu.exec_(self.mapToGlobal(event.pos()))


    # Window is shown - open
    def showEvent(self, event):
        if self.win_position:
            self.setGeometry(self.win_position) # move window to the position on screen
            
        self.read_tree_spectra_data()
        self.read_tree_peaks_data()
        self.update()
        event.accept()


    # Window is closed - not visible    
    def closeEvent(self, event):
        self.win_position = self.geometry()   # to rember position for next show
        self.tree.plot.mass_err_view.hide_calibration()
        event.accept()
        