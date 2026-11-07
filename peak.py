from pythoms.molecule import IPMolecule
from PyQt5.QtWidgets import QMessageBox, QApplication
from PyQt5.QtGui import QClipboard
import json
import os
import numpy as np
from common import get_nearest_idx, ISO_TRESHOLD


def is_formula_OK(formula):
    '''
    Fast check 'formula' for containing only allowed chars - 'A-Za-z0-9()[]{}'
    It is here, as the checking inside of 'IPMolecule' modul is not perfect e.g.
    when there is '.' it stucks in newer ending while loop (mass.py line=69)
    note: '-' is not accepted here even it is accepted by the module as a charge sign
    '''    
    def isparentheses(ch):
        if ch in '()[]{}':
            return True
        return False
    
    if not formula:
        return False # empty formula
    
    for ch in formula:
        if not (ch.isdigit() or ch.isalpha() or isparentheses(ch)):
            return False
        
    return True
    

class Peak():
    def __init__(self) -> None:
        self.name = ''          # name of the molecule or peak
        self.x = 0              # experimental mass value
        self.y = 0              # experimental intensity or counts value
        self.t = 0              # time of fly
        self.mol = None         # instance of IPMolecule class
        self.x_iso = []         # isotopes pattern mass values
        self.y_iso = []         # isotopes pattern intensity or counts values
        self.x_iso_main = None     # considered to be main isotope mass
    
    
    def set_name(self, name):
        self.name = name
        
    
    def get_name(self):
        return self.name
    
    
    def set_xy(self, x, y):
        self.x = x
        self.y = y
        

    def set_t(self, t):
        self.t = t
        

    def get_xy(self):
        """
        Return experimental x - mass and y - counts (intensity)
        """
        return self.x, self.y
    
    def get_t(self):
        return self.t


    def get_xy_iso(self):
        return self.x_iso, self.y_iso

    
    def _get_nearest_xy_iso(self, mass):
        idx = get_nearest_idx(self.x_iso, mass) # get index of iso pattern peak with 'mass'
        return self.x_iso[idx], self.y_iso[idx] # and get its mass and intensity
        
        
    def set_x_main_iso(self, x):
        self.x_iso_main = x


    def get_xy_main_iso(self):
        '''
        Return the mass and intensity of the main isotope peak.
        and None if not defined.
        '''    
        if not self.x_iso_main:
            return None
        return self._get_nearest_xy_iso(self.x_iso_main)
        

    def scale_iso_pattern_to(self, mass, intensity):
        '''
        Change the self.y_iso related to mass 'mass' to 'intensity' 
        and rescale all other pattern peaks properly.
        '''        
        _, y = self._get_nearest_xy_iso(mass)   # get intensity of mass in isos pattern
        self.y_iso = [i/y*intensity for i in self.y_iso] # rescale all peaks in the iso pattern
        
    
    def is_iso_not_empty(self):
        if isinstance(self.x_iso, list):
            return len(self.x_iso) > 0
        return False


    def init_molecule(self):
        self.x_iso = []
        self.y_iso = []
        self.set_x_main_iso(None)

        if not is_formula_OK(self.name):
            return
        
        try:
            # ipmethod="hybrid" is used because of folloowing:
            # there are following possibilities: 
            # 'isospec' - does not accept isotops in formula e.g. '(35Cl)'
            # 'multiplication' - not accept combined isotopes e.g. '(35Cl)(37Cl)'
            # 'combinatorics' - is slower (but more accureate) then following
            # 'hybrid' - it accept complite isotopic formula and is fast
            self.mol = IPMolecule(self.name, ipmethod="isospec",
                                  dropmethod="threshold",
                                  threshold=ISO_TRESHOLD)
            
            self.x_iso, self.y_iso = self.mol.bar_isotope_pattern
            self.set_x_main_iso(self.mol.monoisotopic_mass)    # initiate using monoiso mass 
            # scale the pattrens matching monoisotopic mass to related 'peak' intenstity
            if self.y == 0:
                pass
            else:
                self.scale_iso_pattern_to(self.x_iso_main, self.y)

        except Exception as e:
            pass
        

    def copy_to_clipboard(self):
        if self.is_iso_not_empty():
            # compose txt table
            txt = 'mass \t counts\n'
            for x, y in zip(self.x_iso, self.y_iso):
                txt += f'{x:.2f} \t {y:.3f} \n' 
            
            clipboard = QApplication.clipboard()
            clipboard.setText(txt, QClipboard.Clipboard)
        else:
            self.dialog = QMessageBox(text="""Define the molecula\'s formula first !
To edit the formula double click the peak 'name' cell.""")
            # error_dialog = QtWidgets.QErrorMessage()
            self.dialog.show()

    
    
    
    def save_session(self, fn):
        fn += '.json'
        # make dict. of all of class parameters defined by me
        # i.e. members not starting with '__' and not methods
        params = {key:value for key, value in self.__dict__.items() 
                  if not key.startswith('__') and not callable(key)
                  and not key == 'mol'}
        
        with open(fn, "w") as file:
            json.dump(params, file)
            
        file.close()
        

    def load_session(self, fn):
        with open(fn + '.json') as json_file:
            params = json.load(json_file)

        self.set_params(params)


    def set_params(self, params):
        for key, value in params.items():
            setattr(self, key, value)

        # try to instatiate molecule object if there was mass info
        # commented out as it is not wanted to rewrite self.main_iso_mass loaded from file
        # if self.x_iso:
        #     self.init_molecule()
            
            
    @classmethod
    def delete_session_files(cls, fn):
        os.remove(fn + '.json')        
