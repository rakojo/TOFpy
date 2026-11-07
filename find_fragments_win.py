from __future__ import annotations

from find_fragments_ui import Ui_FindFragments 
from PyQt5.QtWidgets import QWidget, QDialog, QPushButton, QHBoxLayout, QVBoxLayout, QMessageBox
from PyQt5.QtCore import Qt, QPoint
from common import get_nearest_idx, ISO_TRESHOLD, get_max_within_mass_range
from pythoms.molecule import IPMolecule
from peak import Peak, is_formula_OK
# from iso_pattern_view import IsoPatternView

from iso_pattern_settings_ui import Ui_Iso_Pattern_Settings
import numpy as np

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    # from peak import Peak
    from tree import SpectrasTree


class FindFragmentsWin(Ui_FindFragments, QWidget):
    """
    This is window to contorl cluster finding parameters and finding procedure. 
    Parameter 'tree' is the reference to 'class SpectrasTree' widget.
    """
    def __init__(self, tree : SpectrasTree, parent=None):
        super().__init__(parent)   # parent is applied to QWidget (inherited)
        self.setupUi(self)
        self.win_position = None    # used to remember change in windoww position
        # Set the window flag to keep it always on top
        self.setWindowFlags(Qt.Window \
                            | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        # self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Window \
        #                     | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

        self.message_box_active = False # to prevent re-entering if the message box is active
        self.is_closing = False         # to prevent from updating when closing window
        self.fragment_mass = None       # mass used to find fragments from the formula
        self.fragment_mass_iso = None   # to remember the selected mass from isotop pattern
        self.fragment_name = None       # name of the fragment from the mass or formula
        self.iso_x, self.iso_y = [], [] # isotop pattern data
        
        self.formula = ''               # to remember the formula
        self.edit_formula.setText('')   # initiate with hydrogene
        self.spin_box_to_n.setValue(0)
        self.spin_box_tolerance.setValue(0.5)
        
        self.tree : SpectrasTree = tree
        self.peak : Peak = None         # Peak class object
        
        self.iso_pattern_view_xy = QPoint(400, 400) # to remember window position 
        self.connectSignalsSlots()
        

    def connectSignalsSlots(self):
        self.edit_formula.editingFinished.connect(self.on_formula_change)
        self.double_spin_box_mass.valueChanged.connect(self.on_mass_change)
        self.spin_box_to_n.valueChanged.connect(self.on_fragment_change)
        self.spin_box_from_n.valueChanged.connect(self.on_fragment_change)
        self.spin_box_tolerance.valueChanged.connect(self.on_fragment_change)
        self.check_box_lock.stateChanged.connect(self.on_fragment_change)
        self.push_button_add.pressed.connect(self.on_add)
        self.push_button_iso.pressed.connect(self.on_iso)
        self.radioButton_maximum.toggled.connect(self.on_fragment_change)
        self.radioButton_monoiso.toggled.connect(self.on_fragment_change)
        
        # tab change signal
        self.tabWidget.currentChanged.connect(self.on_tab_change)
        
        # Signal the tree widget (from outside, from another window)
        self.tree.currentItemChanged.connect(self.on_tree_current_changed)


    def find_next_fragment(self, from_mass, fragment_mass):
        '''
        Finds the peak located approx. at the mass 'from_mass' + 'self.fragment_mass'
        and return its position and value (mass, counts)
        The position is determined as a closest point or a maximum within the range 
        specified by the 'spin_box_tolerance' dependent on the 'check_box_lock'.
        '''        
        
        # Get current spectra of the tree
        spectra = self.tree.get_spectra_parent().spectra  
        x_mass, y_counts = spectra.get_xy()

        next_mass = from_mass + fragment_mass
        
        idx = get_nearest_idx(x_mass, next_mass)
        
        # find index of the maximum within 'tolerance' and update idx to it
        if self.check_box_lock.isChecked():
            tolerance = self.spin_box_tolerance.value()
            idx = get_max_within_mass_range(x_mass, y_counts, idx, tolerance)
            # idx = max_within_range(y_counts, idx, tolerance)
                 
        return x_mass[idx], y_counts[idx]
    

    def find_all_fragments(self):
        '''Find all fragments for the selected 'peak' in the 'tree'. 
        Returns:
            _type_: x, y, texts - parent peak is not in the list !!!
        '''        
        xs = []     # list of clustes peak positions (mass)
        ys = []     # list of the peak's hights (counts - intensity)
        texts = []  # text e.g for annotation
        main_isos = [] # due to compatibility with the isotop pattern find function
        
        if not self.peak:
            return    # If peak item is not selected in the tree then exit 
        
        fragment_mass = self.fragment_mass
        ns = [self.spin_box_to_n.value(), self.spin_box_from_n.value()]
        signs = [1, -1]
        
        # find in posite and negative (left-right)direct. in resp. to parent
        for n, s in zip(ns, signs):
            # for possitive fragments - addition of positive fragment_mass
            x_mass = self.peak.x        # initiate mass to the parent peak
            for i in range(0, n, s):
                x_mass, y_counts = self.find_next_fragment(x_mass, s*fragment_mass)
                xs.append(x_mass)
                ys.append(y_counts)
                # text = f'{self.peak.name} + ({self.fragment_name}){i+s}'
                text = f'({self.fragment_name}){i+s}'
                texts.append(text)
                main_isos.append(None) # to be compatible with the isotop pattern find function
        
        return xs, ys, texts, main_isos
        
        
    def find_iso_pattern(self, molecule, mass_error):
        '''
        Function to find the isotopic pattern of 'molecule' to the experimental mass spectrum.
        Returns the mass and intensity - x,y and shift - sx  of the pattern best matching possition of the pattern.
        'molecule' is the IPMolecule object.
        '''
        
        if self.message_box_active:
            return  # Prevent re-entering if the message box is active

        pattern_range = self.spin_box_tolerance.value()   # half range to search in the pattern in the spectrum 
        RANGE_SAMPLES_NUM = 100 # number of samples in the range
        
        # Get current spectra of the tree
        spectra = self.tree.get_spectra_parent().spectra  
        xs, ys = spectra.get_xy()

        px, py = np.array(molecule.bar_isotope_pattern)
        if mass_error:      # error can be 'None' if previos iteration was out of range
            px += mass_error # include mass error
        
        
        if px[-1] > xs[-1] + pattern_range or px[0] < xs[0] - pattern_range:
            self.message_box_active = True  # to prevent re-entering
            dlg = QMessageBox(parent=self, text=f"Out of range of TOF spectra!")
            dlg.exec_()
            self.message_box_active = False # to allow re-entering
            return None, None, None, None # out of range do not find the pattern
        
        # cut the axis to the range in where to search
        x_cut = xs[(xs > px[0] - pattern_range) & (xs < px[-1] + pattern_range)]
        y_cut = ys[(xs > px[0] - pattern_range) & (xs < px[-1] + pattern_range)]
        
        py = py/max(py)*max(y_cut)  # normalize the pattern to maximum

        residuums = []
        shifts = [] 
        # print('Fitting ...')
        for sx in np.linspace(-pattern_range, pattern_range, RANGE_SAMPLES_NUM):
            # get interpolated values of for px + sx in x_cut from the y_cut
            yis = np.interp(px + sx, x_cut, y_cut) 
            residuums.append(sum(np.abs(yis - py)))
            shifts.append(sx + mass_error)   
            
        idx = np.argmin(residuums)
        sx = shifts[idx]    # shift of the pattern best matching - add toexperimental to match
        
        if self.radioButton_monoiso.isChecked():
            # closest index in exp. masses to monoisotopic mass of the matched iso pattern
            main_iso = molecule.monoisotopic_mass
        else:
            max_idx = np.argmax(py) # maximum of the pattern
            main_iso = np.array(molecule.bar_isotope_pattern)[0][max_idx] # maximum of the pattern
        
        idx = get_nearest_idx(xs, main_iso + sx)        
        # print('end.')
        
        return xs[idx], ys[idx], sx, main_iso


    def find_all_iso_patterns(self):
        xs = []     # list of clustes peak positions (mass)
        ys = []     # list of the peak's hights (counts - intensity)
        texts = []  # text e.g for annotation
        main_isos = [] # list of main isotope masses - maximum or mono isotopic mass
        
        if not self.peak:
            return

        mol_base = self.peak.name   # base molecule name used to compose the fragments
        err = self.peak.get_xy()[0] - self.peak.get_xy_main_iso()[0] # initial mass error
        ns = [self.spin_box_to_n.value(), self.spin_box_from_n.value()]
        signs = [1, -1]

        # find in posite and negative (left-right)direct. in resp. to parent
        for n, s in zip(ns, signs):
            # for possitive fragments - addition of positive fragment_mass
            for i in range(0, n, s):
                frag_text = f'({self.fragment_name}){i+s}'
                cluster = IPMolecule(mol_base + frag_text, ipmethod="hybrid", 
                                     dropmethod="threshold",
                                     threshold=ISO_TRESHOLD)
                

                x_mass, y_counts, err, main_iso = self.find_iso_pattern(cluster, err)
                # if the pattern is found (is not out of TOF range) add it to the list
                if x_mass and y_counts:
                    xs.append(x_mass)
                    ys.append(y_counts)
                    texts.append(frag_text)
                    main_isos.append(main_iso)
        
        return xs, ys, texts, main_isos

        

    def update_single(self, need_visible=True):
        COLOR_FRAG = 'r'  # color of the fragments annotation in the plot
        if self.is_closing:
            return
        
        # check or ignore visibility of the window based on 'need_visible'
        if (need_visible and self.isVisible()) or (not need_visible):
            # is peak item type selected in the tree?
            if self.tree.is_current_peak():
                self.peak = self.tree.currentItem().peak
                self.label_message.setText(f'parent: {self.peak.name}')
                self.label_message.setStyleSheet("color: black")
            else:
                # if not selected set peak to None and show message
                self.peak = None
                self.label_message.setText('Select peak from the tree !!!')
                self.label_message.setStyleSheet("color: red; background-color: yellow;")

            # is peak selected and fragment mass ready and correct?
            if self.peak and self.fragment_mass:
                self.xs, self.ys, txts, self.main_isos = self.find_all_fragments()
                # texts to be used for adding to tree
                self.txts = [f'{self.peak.name}' + txt for txt in txts]
                # for plot annotation add parent name to the peak text - label
                anno_txts = [f'{self.peak.name} + ' + txt for txt in txts]
                colors = len(anno_txts)*[COLOR_FRAG]
                self.tree.plot.clusters_anno.add_list(anno_txts, self.xs,
                                                      self.ys, colors)
                
                # set the offset view plot and its legend
                spectra = self.tree.get_spectra_parent().spectra  
                xp, yp = [], []
                if spectra:
                    xs, ys = spectra.get_xy()
                    self.offset_view.set_xy(xs, ys) # set spectra plot
                    xp = [self.peak.x]            # add parent to the list
                    txtp = ['parent ']            # add parent to legend list
                
                txts = [f"+{xs}" for xs in txts]    # add '+' to fragments for legend
                self.offset_view.set_peaks(xp + self.xs, txtp + txts)
           
            else:
                self.tree.plot.clusters_anno.clear()
                self.offset_view.clear()
                self.xs, self.ys, self.txts = [], [], []
                
            self.offset_view.update()


    def update_pattern(self, need_visible=True):
        # clear the offset view plot and its legend
        self.offset_view.clear()
        COLOR_FRAG = 'r'  # color of the fragments annotation in the plot
        if self.is_closing:
            return
        
        # check or ignore visibility of the window based on 'need_visible'
        if (need_visible and self.isVisible()) or (not need_visible):
            # is peak item type selected in the tree?
            if self.tree.is_current_peak():
                self.peak = self.tree.currentItem().peak
                self.label_message.setText(f'parent: {self.peak.name}')
                self.label_message.setStyleSheet("color: black")
            else:
                # if not selected set peak to None and show message
                self.peak = None
                self.label_message.setText('Select peak from the tree !!!')
                self.label_message.setStyleSheet("color: red; background-color: yellow;")

            # is peak selected and fragment mass formula ready and correct?
            if self.peak and self.fragment_mass_iso:
                self.xs, self.ys, txts, self.main_isos = self.find_all_iso_patterns()
                # texts to be used for adding to tree
                self.txts = [f'{self.peak.name}' + txt for txt in txts]
                # for plot annotation add parent name to the peak text - label
                anno_txts = [f'{self.peak.name} + ' + txt for txt in txts]
                colors = len(anno_txts)*[COLOR_FRAG]
                self.tree.plot.clusters_anno.add_list(anno_txts, self.xs,
                                                      self.ys, colors)
                
                # set the offset view plot and its legend
                spectra = self.tree.get_spectra_parent().spectra  
                xp, yp = [], []
                if spectra:
                    xs, ys = spectra.get_xy()
                    self.offset_view.set_xy(xs, ys) # set spectra plot
                    xp = [self.peak.x]            # add parent to the list
                    txtp = ['parent ']            # add parent to legend list
                
                txts = [f"+{xs}" for xs in txts]    # add '+' to fragments for legend
                self.offset_view.set_peaks(xp + self.xs, txtp + txts)
           
            else:
                self.tree.plot.clusters_anno.clear()
                self.offset_view.clear()
                self.xs, self.ys, self.txts, self.main_isos = [], [], [], []
                
            self.offset_view.update()


    def update(self, need_visible=True):
        if self.tabWidget.currentIndex() == 0:
            self.update_single(need_visible)
        elif self.tabWidget.currentIndex() == 1:
            self.update_pattern(need_visible)


    def on_fragment_change(self):
        self.update()
        
    
    def _shade_formula(self):
        '''
        Shades the formula or mass input widget based on the 'use_formula' flag.
        '''
        if self.use_formula:
            self.edit_formula.setStyleSheet("color: black")
            self.label_formula.setStyleSheet("color: black")
            self.double_spin_box_mass.setStyleSheet("color: gray")
            self.label_mass.setStyleSheet("color: gray")
            self.push_button_iso.setEnabled(True)
        else:
            self.edit_formula.setStyleSheet("color: gray")
            self.label_formula.setStyleSheet("color: gray")
            self.double_spin_box_mass.setStyleSheet("color: black")
            self.label_mass.setStyleSheet("color: black")
            self.push_button_iso.setEnabled(False)
                 
                    
    def on_mass_change(self):
        self.use_formula = False
        self._shade_formula()
        self.fragment_mass = self.double_spin_box_mass.value()
        self.fragment_name = f'{self.fragment_mass}'
        
        self.update()
        
        
    def on_formula_change(self):
        if self.message_box_active:
            return  # Prevent re-entering if the message box is active

        self.use_formula = True
        self._shade_formula()
        new_formula = self.edit_formula.text()
        self.fragment_name = new_formula
        if new_formula != self.formula or not self.fragment_mass_iso:
            self.formula = new_formula
        
            mol = None
            if is_formula_OK(self.formula):
                # TODO IPMolecule setting shouls be at one place in the code
                # you can find it also in the 'Peak' class
                try:
                    mol = IPMolecule(self.formula, ipmethod="hybrid", 
                                        dropmethod="threshold",
                                        threshold=ISO_TRESHOLD)
                except:
                    pass    # 'mol' is None
                
            # is the formula correct?
            if mol:
                self.fragment_mass_iso = mol.monoisotopic_mass
                # implictly set the fragment mass to the monoisotopic mass at the beginning
                self.fragment_mass = mol.monoisotopic_mass
                self.iso_x, self.iso_y = mol.bar_isotope_pattern
            else:
                self.message_box_active = True  # to prevent re-entering
                dlg = QMessageBox(parent=self, text=f"Error in the formula '{self.formula}'!")
                dlg.exec_()
                self.message_box_active = False # to allow re-entering
                self.fragment_mass_iso = None
                self.fragment_mass = None
                self.iso_x, self.iso_y = [], []
        
        else:
            self.fragment_mass = self.fragment_mass_iso

        self.update()

    
    # Slot for tree widget item chanaged signal
    def on_tree_current_changed(self):
        self.update()
    
    
    def on_tab_change(self, idx):
        print(f'Tab changed to {idx}')    
        if idx == 0:
            self.double_spin_box_mass.setDisabled(False)
            self.spin_box_from_n.setDisabled(False)
            self.check_box_lock.setDisabled(False)
            
        elif idx == 1:
            self.double_spin_box_mass.setDisabled(True)
            self.spin_box_from_n.setDisabled(True)
            self.check_box_lock.setDisabled(True)
        self.update()
        
    def on_add(self):
        '''
        Add the found fragments to the tree as peaks.
        '''        
        self.tree.blockSignals(True) # to prevent from updating
        color_widgets = []           # to remember color widgets to block signals
        
        if self.xs and self.ys and self.txts:
            # get color of current peak to use it also for the finded peaks 
            peak_color = self.tree.itemWidget(self.tree.currentItem(), 1).color()
            for xs, ys, txt, main_iso in zip(self.xs, self.ys, self.txts, self.main_isos):
                peak = Peak()
                peak.set_xy(xs, ys)
                peak.set_name(txt)
                peak.init_molecule()
                # main_iso == None when it is searched as single peak (not isotop pattern)
                if main_iso:
                    peak.set_x_main_iso(main_iso)
                
                spectra = self.tree.get_spectra_parent()
                if spectra:
                    t = spectra.spectra.get_nearest_t_by_x(xs)
                    peak.set_t(t)
                    
                item = self.tree.add_peak_item_to_current(peak)

                color_widget = self.tree.itemWidget(item, 1)
                color_widgets.append(color_widget)
                color_widget.blockSignals(True)     # to prevent from updating
                color_widget.setColor(peak_color)   # when setting color

        # unblock signals and update the tree and plot
        self.tree.blockSignals(False)
        for color_widget in color_widgets:
            color_widget.blockSignals(False)
        self.tree.plot.update()
        
                
    def on_iso(self):
        '''
        Show the isotop pattern dialog with the current isotop pattern data.
        '''
        self.iso_pattern_dialog = IsoPatternDialog(self)
        self.iso_pattern_dialog.move(self.iso_pattern_view_xy)
        self.iso_pattern_dialog.set_data(self.iso_x, self.iso_y)
        self.iso_pattern_dialog.set_selected(self.fragment_mass)
        self.iso_pattern_dialog.exec_()
        self.iso_pattern_view_xy = self.iso_pattern_dialog.pos()
        # get the selected mass from the dialog
        self.fragment_mass = self.iso_pattern_dialog.iso_pattern_view.get_selected_mass()
        self.fragment_mass_iso = self.fragment_mass # to remember the selected mass from pattren
       
        self.update()
       
                
    # Window is shown - open
    def showEvent(self, event):
        if self.win_position:
            self.setGeometry(self.win_position) # move window to the position on screen
        self.is_closing = False
        self.update(need_visible=False)
        event.accept()


    # Window is closed - not visible    
    def closeEvent(self, event):
        self.win_position = self.geometry()   # to rember position for next show
        self.tree.plot.clusters_anno.clear()
        # self.tree.plot.offset_view.clear()
        self.tree.plot.update()
        self.is_closing = True  # to prevent from updating by some other 
                                # e.g. when you edit 'edit_formula' it envoke 
                                # the 'on_formula_change' after the close
        event.accept()
        
        
        
class IsoPatternDialog(Ui_Iso_Pattern_Settings, QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.setWindowTitle("Isotop Pattern Dialog")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        
    def set_data(self, x, y):
        self.iso_pattern_view.set_data(x, y)
        
        
    def set_selected(self, mass):
        self.iso_pattern_view.set_selected(mass)
        self.selected = mass # to remember the selected mass
        
        
    def get_selected(self):
        return self.iso_pattern_view.get_selected_mass()
    
    
    # if cancel or cros button is pressed reset selected mass before the dialog was opened
    def reject(self):
        self.iso_pattern_view.set_selected(self.selected)
        super().reject()
    