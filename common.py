from __future__ import annotations

from PyQt5.QtWidgets import QMainWindow
import numpy as np
import json

# from typing import TYPE_CHECKING
# if TYPE_CHECKING:
#     # from spectra import TOF_Spectra
#     from peak import Peak

ISO_TRESHOLD = 0.01



def get_main_window(src_widget) -> QMainWindow:
    ''' Returns the first top most window as a qt parent of the src_widget widget
    '''
        # Traverse up the widget hierarchy to find the main window
    widget = src_widget
    while widget:
        if isinstance(widget, QMainWindow):
            return widget
        widget = widget.parentWidget()
    return None


def get_nearest_idx(x_arr, x_val):
    '''
    Returns index of the nearest value in the array to the given value.
    '''    
    if isinstance(x_arr, list):
        x_arr = np.array(x_arr)
    diff = np.abs(x_arr - x_val)
    return np.argmin(diff)


def max_within_range(array, index, range_size):
    """
    Finds the index of the maximum value within a specified range around a given index in a NumPy array.

    Parameters:
    - array: NumPy array to search within.
    - index: Index around which to search for the maximum value.
    - range_size: Size of the range on either side of the index.

    Returns:
    - Index of the maximum value within the specified range.
    """
    # Ensure the index is within bounds
    if index < 0 or index >= len(array):
        raise IndexError("Index out of bounds")

    # Calculate the start and end indices for the range
    start_index = max(0, index - range_size)
    end_index = min(len(array), index + range_size + 1)

    # Extract the subarray
    subarray = array[start_index:end_index]

    # Find the index of the maximum value in the subarray
    subarray_max_index = np.argmax(subarray)

    # Convert subarray index to the original array index
    max_index = start_index + subarray_max_index
    return max_index


def get_max_within_mass_range(xs, ys, index, mass_range):
    '''
    Returns the maximum value around ys(index) of the ys array within 
    the specified mass range. This function improves "max_within_range" fuction. 
    It is not sensitive to number of points which are changing by mass value 
    (sampling rate is decreasing with mass increasing).
    x_mass - array of mass values
    '''
    # calculate the range in the index units from the mass range and x_mass array
    if index == len(xs) - 1:
        delta_x = xs[index] - xs[index-1]   # index is the last one, not to go out of bounds
    else:
        delta_x = xs[index+1] - xs[index]
        
    range_size = int(mass_range / delta_x)
    return max_within_range(ys, index, range_size)

    
def get_mass(time, coefs):
    """ 
    Time to mass conversion for TOF using polynom with coeficients 
    'coefs' - [a,b,c,...] ax^(n-1) + ax(n-2) ... where n is number coefs. 
    """        
    return np.polyval(coefs, time)

def get_time(mass, coefs):
    """
    Calculates back the original time of TOF spectra from mass by using 
    the calibration coeficients m = at2 + bt + c.  The solution is root 
    of the quadratic equation with corrected 'c' by 'mass' (c-mass).
    'coefs' : [a,b,c] at^2 + at + c.
    """        
    a, b, c = coefs
    c -= mass       # mass = ax^2 + bx + c => 0 = ax^2 + bx + (c - mass)
    return (-1*b + np.sqrt(b**2 - 4*a*c)) / (2*a)


class CFG():
    '''
    Class for saving and loading configuretion values to CFG_FILE
    '''    
    CFG_FILE = 'config.json'
  
    values = {}

    @classmethod
    def save(cls):
        with open(cls.CFG_FILE, 'w') as file:
            json.dump(cls.values, file, indent=4)


    @classmethod
    def load(cls):
        with open(cls.CFG_FILE, 'r') as file:
            cls.values = json.load(file)



