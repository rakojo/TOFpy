import numpy as np
import os
import json
import struct
from PyQt5.QtWidgets import QMessageBox
from common import get_time, get_mass, get_nearest_idx



ALPHA = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L',
         'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']


class TOF_Spectra():
    def __init__(self):
        self.y_scale = 1.0
    
    def _load_tfa_file(self, fn):
        '''
        Load '.tfa' file related to the 'fn' binary file, containing information 
        about TOF aquisition settings ('bin width', various voltages ...)
        Returns dictionary with key: name of parameters and value as 'float'
        '''        
        tfa = {}
        folder = os.path.dirname(fn)
        fname, _ = os.path.basename(fn).split('.')

        # read parameters of TOF aquisition from '.tfa' file 
        fn = os.path.join(folder, fname + '.tfa')
        if not os.path.exists(fn):
            return {}

        with open(fn) as file:
            content = file.read()

        lines = []
        for line in  content.split('\n')[1:]:  # skip fist line it is time
            if line != '':
                lines.append(line)

        tfa_date_time = content.split('\n')[0] # date and timeis fist line of the file

        for line in lines:
            param, val = line.split('=')
            tfa[param] = float(val)     # all parameters are float numbers

        return tfa
            
    def _load_mas_file(self, fn):
        '''
        Load '.mas' file related to the 'fn' binary file, containing calibration 
        coeficients
        Returns dictionary with A, B, C as keys and relating values ('float')
        '''       
        mas = {} 
        folder = os.path.dirname(fn)
        fname, _ = os.path.basename(fn).split('.')
        # read calibration coeficients '.mas' file 
        fn = os.path.join(folder, fname + '.mas')
        if not os.path.exists(fn):
            return {}

        with open(fn) as file:
            content = file.read()

        lines = []
        for line in content.split('\n'):
            if line != '':
                lines.append(float(line.split()[1]))

        mas = {}
        for idx, val in enumerate(reversed(lines)):
            coef = chr(idx + 65) # 'A','B','C' generate automaticaly coef. names 
            mas[coef] = val
            
        return mas
            

    def load_bin(self, fn):
        self.path = fn     # remember the path with file name
        # read binary content of the file
        file = open(fn, mode='rb')
        # Get raw TOF instrument data from the file. It is 1D array of 32-bit float,
        # big-endian, values - representing counts (intensity) of TOF spectrum
        buff = file.read()       # read all content
        count = len(buff) // 4   # number of values, 4 -> size of float
        data = struct.unpack('>' + count*'f', buff)
        raw = np.array(data, dtype=float) # 1D array np with the values 
        file.close()
        
        self.tfa_file_info = self._load_tfa_file(fn)
        if not self.tfa_file_info:
            self.dialog = QMessageBox(text="I can not locate '.tfa file'")
            self.dialog.show()
            return 
        
        self.aq_info = {"time resolution" :  self.tfa_file_info["time resolution (ps)"],
                        "binwidth" : self.tfa_file_info["bin width"],
                        "offset" : self.tfa_file_info["offset (channels)"]
                        }

        self.mas_file_info = self._load_mas_file(fn)
        if not self.mas_file_info:
            self.dialog = QMessageBox(text="I can not locate '.mas file'")
            self.dialog.show()
            return
        
        self.calibration_coefs = self.mas_file_info.copy()
        
        # self.t = raw*self.tfa_info["time resolution (ps)"]*1e6 # to micro seconds
        arr = np.arange(start = 1, stop = raw.size+1)   # [1, 2, ...]
        delta_time = float(self.aq_info["time resolution"]) * float(self.aq_info['binwidth'])
        # self.t = arr*2000*1e-6 # to micro seconds
        self.t = arr*delta_time*1e-6 # to micro seconds
        self.x = get_mass(self.t, self.get_coeficients())
        self.y = raw
        
        
    def load_ascii(self, fn):
        # parse the head of the file to get calibration coefs. and some info
        HEAD_LINES = 20    # I am not sure if num. of poly.coef. can change, so it is more than needed
        self.path = fn     # remember the path with file name
        
        with open(fn) as file:
            head = [next(file) for _ in range(HEAD_LINES)]

        line_num = head.index('\n')     # find end of calibration coef. section
        self.calibration_coefs = {x.split('=')[0]: float(x.split('=')[1]) 
                                for x in head[1:line_num]}
        self.aq_info = {x.split('=')[0]: float(x.split('=')[1]) 
                        for x in head[line_num+1:line_num+4]}
        
        # read head data of the file
        line_num += 6           # line number where data part starts
        data = np.loadtxt(fn, skiprows=line_num)
        self.x = data[:, 0]
        self.y = data[:, 1]
        self.t = get_time(self.x, self.get_coeficients())

        
    def get_coeficients(self):
        '''
        Returns list of polynomial coeficients. Order should be from higher to lower.
        '''        
        coefs = list([v for k, v in self.calibration_coefs.items()])
        return coefs
        
    
    def set_coeficients_and_recalibrate(self, coefs):
        self.calibration_coefs.clear()
        for idx, coef in enumerate(coefs):
            self.calibration_coefs[ALPHA[idx]] = coef
        
        # recalibrate mass values
        self.x = get_mass(self.t, coefs)


    def get_nearest_t_by_x(self, mass):
        return self.t[get_nearest_idx(self.x, mass)]
    

    def get_name(self):
        return os.path.basename(self.path)  # file name with extension
    

    def get_xy(self):
        return self.x, self.y_scale*self.y
    
    
    def get_ty(self):
        return self.t, self.y_scale*self.yself.y
    
    
    def set_y_scale(self, scale):
        self.y_scale = scale
        
    def get_y_scale(self):
        return self.y_scale
        
        
    def save_session(self, fn):
        np.save(fn + '.npy', np.array([self.x, self.y, self.t]))

        # make dict. of all of class parameters defined by me
        # i.e. members not starting with '__' and not methods and 
        # not 'x','y','t' (they are np arrays)
        params = {key:value for key, value in self.__dict__.items() 
                  if not key.startswith('__') and not callable(key)
                  and key not in ['x', 'y', 't']}
        
        with open(fn + '.json', "w") as file:
            json.dump(params, file)
            
        file.close()
        

    def set_params(self, dictionary):
        for k, v in dictionary.items():
            setattr(self, k, v)

    def load_session(self, fn):
        data = np.load(fn + '.npy')
        self.x = data[0, :]     # load mass values
        self.y = data[1, :]     # load counts - intensity
        self.t = data[2, :]     # load time (of fly) values

        with open(fn + '.json') as json_file:
            data = json.load(json_file)

        json_file.close()

        self.set_params(data)
        
    @classmethod
    def delete_session_files(cls, fn):
        os.remove(fn + '.npy')        
        os.remove(fn + '.json')        
