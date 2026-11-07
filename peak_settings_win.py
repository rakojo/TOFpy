from __future__ import annotations

from peak_settings_ui import Ui_PeakSettings
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt
from peak import Peak

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    # from peak import Peak
    from tree import SpectrasTree
    from peak import Peak

class PeakSettingsWin(Ui_PeakSettings, QWidget):
    """
    This is window contor paek settings - select iso peak from pattern ...
    """
    def __init__(self, tree : SpectrasTree, parent=None):
        super().__init__(parent)   # parent is applied to QWidget (inherited)
        self.setupUi(self)
        self.win_position = None    # used to remember change in windoww position
        # Set the window flag to keep it always on top
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Window \
                            | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

        self.is_closing = False     # to prevent from updating when closing window
        self.tree : SpectrasTree = tree
        self.peak : Peak = None     # Peak class object
        
        self.connectSignalsSlots()
        

    def connectSignalsSlots(self):
        self.pushButton_apply.pressed.connect(self.on_apply)
        # Signal the tree widget (from outside, from another window)
        self.tree.currentItemChanged.connect(self.on_tree_current_changed)
        self.tree.itemChanged.connect(self.on_tree_current_changed)

    
    def on_tree_current_changed(self):
        current = self.tree.currentItem()
        if self.tree.is_current_peak():
            self.peak = current.peak
            self._update_iso_pattern_view()
            return
            
        self.bars.set_data([], [])


    def _update_iso_pattern_view(self):
        """
        This method updates the bar graph with the isotopic pattern of the selected peak.
        """        
        # is molecule name defined?
        if self.peak.is_iso_not_empty():
            x, y = self.peak.get_xy_iso()
            main_x_iso, _ = self.peak.get_xy_main_iso() # the bar is highlighted
            self.bars.set_data(x, y)
            self.bars.set_selected(main_x_iso)
            return
        else:
            self.bars.set_data([], [])
            
            
    def on_apply(self):
        mass = self.bars.get_selected_mass()
        if mass is not None:
            self.peak.set_x_main_iso(mass)
            self._update_iso_pattern_view()
            self.tree.plot.update()
            

    # Window is shown - open
    def showEvent(self, event):
        if self.win_position:
            self.setGeometry(self.win_position) # move window to the position on screen
        self.is_closing = False
        event.accept()
        

    # Window is closed - not visible    
    def closeEvent(self, event):
        self.win_position = self.geometry()   # to rember position for next show
        # self.tree.plot.offset_view.clear()
        self.is_closing = True  # to prevent from updating by some other 
        event.accept()
        