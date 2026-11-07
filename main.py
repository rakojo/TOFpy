import sys
from PyQt5.QtWidgets import QApplication, QFileDialog, QMainWindow, QMessageBox
from PyQt5.QtGui import QIcon, QKeyEvent
from PyQt5.QtCore import Qt
from main_ui import Ui_MainWindow
from find_fragments_win import FindFragmentsWin
from calibrate_spectra_win import CalibrateSpectraWin
from peak_settings_win import PeakSettingsWin
from common import CFG
import os

from pythoms.molecule import logger as logger_mol
from logging import ERROR

import time_profiler as tp

from logging_config import logger, get_last_log, save_logs_after    


logger_mol.setLevel(ERROR)  # to turn off warnning messages from pythom - IPMolecule

# to start splash screen
if getattr(sys, 'frozen', False):
    import pyi_splash   # dynamic import
    pyi_splash.update_text("Loading...")
    
    
class Window(Ui_MainWindow, QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon("icon.png"))
        self.actionSnap_to_maximum.setChecked(True) # initialize peak menu check box

        # plot <-> tree - bidirectional relationship the two objs
        self.tree.set_plot(self.plot)
        self.plot.set_offset_view(self.offset_view)  #TODO all integration of 'PeaksView'
                                                   # should be done inside of 'plot'
        self.plot.set_mass_error_view(self.mass_error_view)
        
        self.win_find_clusters = FindFragmentsWin(self.tree, self)
        self.win_calibrate_spectra = CalibrateSpectraWin(self.tree, self)
        self.win_calibrate_spectra.set_err_view(self.mass_error_view)
        self.win_peak_settings = PeakSettingsWin(self.tree)
        
        self.session_folder = '' # the session folder currently loaded
        
        logger.info('Application started')
        logger.info("Session started: 'unnamed'")
        self.session_log_start = get_last_log()  # to where the session log starts for later session log save

        CFG.load()
        if 'session' in CFG.values:
            session_folder = CFG.values['session']
            if session_folder:
                # profiler.enable()
                self.load_session(session_folder)
                # disable_profiler()
        
                
        self.connectSignalsSlots()
        # tp.start()
        
    
    def connectSignalsSlots(self):
        # File menu
        self.actionOpenFiles.triggered.connect(self.open_files_ascii)
        self.actionOpenFilesBin.triggered.connect(self.open_files_bin)
        self.actionSave_Session.triggered.connect(self.on_save_session)
        self.actionSave_Session_As.triggered.connect(self.on_save_session_as)
        self.actionLoad_Session.triggered.connect(self.load_session)
        self.actionNew_Session.triggered.connect(self.new_session)
        self.actionExit.triggered.connect(self.on_exit)

        # Cursor menu
        self.actionSnap_to_nearest.triggered.connect(self.snap_to_nearest)
        self.actionSnap_to_maximum.triggered.connect(self.snap_to_maximum)

        # Spectrum menu
        self.actionon_calibrate.triggered.connect(self.calibrate_spectra)

        # Peak menu
        self.actionFind_fragments.triggered.connect(self.find_fragments)
        self.actionAdd_peak.triggered.connect(self.on_add_peak)
        self.actionMove_peak.triggered.connect(self.on_move_peak)
        self.actionSettings.triggered.connect(self.on_peak_settings)

        # Make connection of to 'plot' slots.
        # Note: this should be called after the instantiance of the 'plot'
        self.plot.connectSignalsSlots()

    def open_files_ascii(self):
        files = QFileDialog.getOpenFileNames(self, filter='*.asc',
                                            caption = "Select one or more files ASCII to open")[0] 
                                            # ^ [0] is list of files ([1] is file types str)
        if files:
            self.tree.load_spectras_ascii(files)
        

    def open_files_bin(self):
        files = QFileDialog.getOpenFileNames(self, filter='*.tfb',
                                            caption = "Select one or more binary files to open")[0]
                                            # ^ [0] is list of files ([1] is file types str)
        if files:
            self.tree.load_spectras_bin(files)


    def new_session(self):
        self.tree.clear()
        self.plot.update() # clear plot
        self.plot.update_lines() # clear lines
        self.session_folder = ''
        self.setWindowTitle("TOFpy - session:")
        CFG.values['session'] = ''
        CFG.save()
        logger.info("Session started: 'unnamed'")
        self.session_log_start = get_last_log() # remember log session start for later save



    def load_session(self, folder_rel_path=None):
        app_dir = os.path.dirname(os.path.abspath(__file__))
        if not folder_rel_path:
            # path to session is not given, ask for the file to get foleder path by a dialog
            # the file is used just to get the name of session folder it has no other purpouse
            # tuple(file, selected file types filter)
            file, _ = QFileDialog.getOpenFileName(self, filter='*.tfs',
                                                  caption = "Select session to open")
            if not file:
                return

            folder_abs_path = os.path.splitext(file)[0] # [path+file, file extension]
            # Get the relative path of the target path with respect to the current file's directory
            # Just for safety not to save absolute paths
            folder_rel_path = os.path.relpath(folder_abs_path, app_dir)

        folder_abs_path = os.path.join(app_dir, folder_rel_path)

        if self.tree.load_tree(folder_abs_path):
            # loading passed succesfully 
            CFG.values['session'] = folder_rel_path
            CFG.save()
            self.session_folder = folder_abs_path
            self.setWindowTitle(f"TOFpy - session: '{folder_abs_path}'")
            logger.info(f"Session loaded: '{folder_rel_path}'")
            self.session_log_start = get_last_log() # remember log session start for later save
        else:
            self.dlg = QMessageBox(text=f"Session '{folder_abs_path}' is missing!")
            self.dlg.show()
            self.session_folder = ''
            self.setWindowTitle(f"TOFpy - session:")
            

    def save_session(self, folder):
        self.tree.save_session(folder)

        # update config file for last saved session
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        rel_path = os.path.relpath(folder, current_file_dir)
        CFG.values['session'] = rel_path
        self.session_folder = folder
        self.setWindowTitle(f"TOFpy - session: '{folder}'")
        logger.info(f"Session saved: '{rel_path}'")
        save_logs_after(self.session_log_start, os.path.join(folder, 'log.txt'))
        self.session_log_start = get_last_log() # remember log session start for later save


    def on_save_session_as(self):  #TODO to save to one bin file
        file, _ = QFileDialog.getSaveFileName(self, filter='*.tfs',
                                              caption = "Save session ")
        if not file:
            return
        
        folder, _ = os.path.splitext(file)   # [path+file, file extension]
        if os.path.exists(file) and folder:
            self.dlg = QMessageBox(text="It is not possible to rewrite the session - use unique name!")
            self.dlg.show()
            return
            
        else:
            os.mkdir(folder)            # create session folder
        
        open(file, 'a').close()     # create session identifing file
        
        self.setWindowTitle(f"TOFpy - session: '{folder}'")
        self.save_session(folder)


    def on_save_session(self):  #TODO to save to one bin file
        if self.session_folder:
            # session was saved or loaded before
            folder = self.session_folder
            # TODO is commended I do not like deleting before saving
            # self.tree.delete_session_files(folder) # clear folder
        else:
            # there is no active session
            # the file is used just to get the name of session folder it has no other purpouse
            # the folder name is same as the file name without extension
            file, _ = QFileDialog.getSaveFileName(self, filter='*.tfs',
                                                  caption = "Save session ")
            if not file:
                return
            
            folder, _ = os.path.splitext(file)     # [path+file, file extension]
            os.mkdir(folder)            # create session folder
            open(file, 'a').close()     # create session identifing file

        self.save_session(folder)
        
        
    def snap_to_nearest(self):
        self.actionSnap_to_maximum.setChecked(False)


    def snap_to_maximum(self):
        self.actionSnap_to_nearest.setChecked(False)



    def calibrate_spectra(self):
        if self.win_calibrate_spectra.isVisible():
            self.win_calibrate_spectra.hide()

        else:
            self.win_calibrate_spectra.show()



    def find_fragments(self):
        if self.win_find_clusters.isVisible():
            self.win_find_clusters.hide()

        else:
            self.win_find_clusters.show()


    def on_add_peak(self):
         # Create a key press event
        event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_A, Qt.NoModifier)
        # Send the event to the widget
        QApplication.postEvent(self.plot, event)


    def on_move_peak(self):
        # Create a key press event
        event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_M, Qt.NoModifier)
        # Send the event to the widget
        QApplication.postEvent(self.plot, event)

    def on_peak_settings(self):
        if self.win_peak_settings.isVisible():
            self.win_peak_settings.hide()
        else:
            self.win_peak_settings.show()

        

    def on_exit(self):
        self.close()

    # Window is closed
    def closeEvent(self, event):
        # tp.stop()
        # tp.save()
        CFG.save()
        logger.info('Application closed')



if __name__ == "__main__":
    # profiler.enable()

    app = QApplication(sys.argv)    # Create an application instance
    win = Window()                  # Create the main window 'class Window(Ui_MainWindow, QMainWindow):'
                                    # or it can be QtWidgets.QMainWindow() or QtWidgets.QWidget()
    win.show()                      # Show the main window

    # app.aboutToQuit.connect(disable_profiler)

    if getattr(sys, 'frozen', False):
        pyi_splash.close()

    sys.exit(app.exec())   # 'exec()' starts even the event loop, 
                            # The application remains running as long as the event loop is active


