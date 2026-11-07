from PyQt5.QtWidgets import QTreeWidgetItem
from PyQt5.QtCore import Qt
from pyqtgraph import ColorButton
from spectra import TOF_Spectra
from peak import Peak
from enum import IntFlag



# ==============================================================================
# ========================== class ItemType == =================================
# ==============================================================================
class ItemType(IntFlag):
    SPECTRA     = 1
    FOLDER      = 2
    PEAK        = 4 


# ==============================================================================
# ========================== class SpectraItem =================================
# ==============================================================================
class  SpectraItem(QTreeWidgetItem):
    def __init__(self, parent, text, check=None, color=None, **kwargs):
        super().__init__(parent)
        self.setFlags(self.flags() | Qt.ItemIsEditable) # to be editable in place
        self.setFlags(self.flags() | Qt.ItemIsUserCheckable) # add check box

        self.type = ItemType.SPECTRA
        self.spectra : TOF_Spectra  = None
        
        
       
        if not check:
            self.setCheckState(0, Qt.Unchecked)
        else: 
            self.setCheckState(0, check)
        
        self.setText(0, text)
        self._add_color_button(color)
        
        for key, value in kwargs.items():
            if key == "tags":
                self.setText(2, value)


    def _add_color_button(self, color=None):
        color_button = ColorButton(padding=1)
        color_button.setFixedSize(20, 20)
        if color:
            color_button.setColor(color)
        
        tree = self.treeWidget()    # get tree obj. of this item 
        # connect event to react to color change by color button
        color_button.sigColorChanged.connect(tree.plot.update_lines)
        # set color button to 1 col of tree item
        tree.setItemWidget(self, 1, color_button) 


    def save_session(self, fn):
        self.spectra.save_session(fn)


    def load_session(self, fn):
        self.spectra = TOF_Spectra()
        self.spectra.load_session(fn)
        
    @classmethod
    def delete_session_files(cls, fn):
        TOF_Spectra.delete_session_files(fn)
        



# ==============================================================================
# ========================== class PeakItem ====================================
# ==============================================================================
class PeakItem(QTreeWidgetItem):
    def __init__(self, parent, text, check=0, color=None,  **kwargs):
        super().__init__(parent)
        self.setFlags(self.flags() | Qt.ItemIsEditable) # to be editable in place
        self.setFlags(self.flags() | Qt.ItemIsUserCheckable) # add check box

        self.type = ItemType.PEAK
        self.peak : Peak = None
        self.anno_text = None    # annotation text in plot

       
        self.setText(0, text)
        self.setCheckState(0, check)
        self._add_color_button(color)
        
        for key, value in kwargs.items():
            if key == "tags":
                self.setText(2, value)



    def _add_color_button(self, color=None):
        color_button = ColorButton(padding=1)
        color_button.setFixedSize(20, 12) 
        if color:
            color_button.setColor(color)
        
        tree = self.treeWidget()    # get tree obj. of this item 
        # connect event to react to color change by color button
        color_button.sigColorChanged.connect(tree.plot.update)
        # set color button to 1 col of tree item
        tree.setItemWidget(self, 1, color_button) 


    def save_session(self, fn):
        self.peak.save_session(fn)

    def load_session(self, fn):
        self.peak = Peak()
        self.peak.load_session(fn)
        
    @classmethod
    def delete_session_files(cls, fn):
        Peak.delete_session_files(fn)



# ==============================================================================
# ========================== class FolderItem ==================================
# ==============================================================================
class FolderItem(QTreeWidgetItem):
    def __init__(self, parent, text, check=0, **kwargs):
        super().__init__(parent)
        self.setFlags(self.flags() | Qt.ItemIsEditable) # to be editable in place
        self.setFlags(self.flags() | Qt.ItemIsUserCheckable) # add check box

        self.type = ItemType.FOLDER

        self.setText(0, text)
        self.setCheckState(0, check)
        self.name_txt = text    # to remember and compare - to be able to log renaming of folder
        # self._add_color_button(color)
        
        for key, value in kwargs.items():
            if key == "tags":
                self.setText(2, value)

    def save_session(self, fn):
        pass

    def load_session(self, fn):
        pass

    @classmethod
    def delete_session_files(cls, fn):
        pass