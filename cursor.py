from pyqtgraph import InfiniteLine
import numpy as np
from common import get_main_window, get_max_within_mass_range, get_nearest_idx


LAYER_CURSOR =   10     # cursor layer
CURSOR_OPTS = {'color': (200,0,0),
               'movable': True,
               'fill': (255, 255, 127, 200)
               }
CURSOR_SNAP_RANGE_TO_MAX = 10 # +/- range (points num.) to search for maximum to snap to
CURSOR_SNAP_RANGE_MASS_TO_MAX = 0.5 # +/- range (mass units) to search for maximum to snap to


class Cursor():
    def __init__(self, plot) -> None:
        """
        Args:
            plot: class SpectraPlot
        """        
        self.plot = plot
        # create cross cursor lines - vertical and horizontal
        self.v_line = InfiniteLine(angle=90, movable=True, label="x={value:0.2f}",
                                   labelOpts=CURSOR_OPTS)
        self.h_line = InfiniteLine(angle=0, movable=False, label="y={value:0.2g}",
                                   labelOpts=CURSOR_OPTS)

        self.plot.addItem(self.v_line)
        self.plot.addItem(self.h_line)
        
        # change z-layer to be always on top
        self.v_line.setZValue(LAYER_CURSOR)
        self.h_line.setZValue(LAYER_CURSOR)

        self.v_line.sigPositionChangeFinished.connect(self.on_xpos_changed)


    def set_position(self, x_pos, y_pos):
        self.v_line.setPos(x_pos)
        self.h_line.setPos(y_pos)
        
        
    def get_position(self):
        ''' Returns position to actual cursor location
        '''
        return self.v_line.getPos()[0], self.h_line.getPos()[1]
        
    def set_position_and_snap(self, x_pos, y_pos):
        ''' Set position of cursor and then correct it if needed in 
            accordance of the snap settings
        '''
        self.set_position(x_pos, y_pos)
        self.correct_position_for_snap()
        
   
    def snap_to_nearest(self, x_pos):
        ''' Move cursor to the data point of spectra which is closest to x_pos
        '''
        # is there plot line to snap to?
        if self.plot.line:
            xs, ys  = self.plot.line.getData()
            idx = get_nearest_idx(xs, x_pos)
            self.set_position(xs[idx], ys[idx])
            

    def snap_to_maximum(self, x_pos):
        # is there plot line to snap to maximum?
        if self.plot.line:
            xs, ys  = self.plot.line.getData()
            idx = get_nearest_idx(xs, x_pos)
            idx = get_max_within_mass_range(xs, ys, idx,
                                            CURSOR_SNAP_RANGE_MASS_TO_MAX)
            self.set_position(xs[idx], ys[idx])

            
    def correct_position_for_snap(self):
        ''' Correct the position to snap in accordance of the snap settings in the 
            window menu.
        '''
        x_pos, _ = self.v_line.getPos()  # get current cursor possition
        
        # check settings of menu to decide the way to snap cursor - or not at all
        win = get_main_window(self.plot) # get top most qt win parent to access menu
        
        if win.actionSnap_to_nearest.isChecked():
            self.snap_to_nearest(x_pos)
        
        elif win.actionSnap_to_maximum.isChecked():
            self.snap_to_maximum(x_pos)

        else:
            pass # possition does not need to be corrected


    def get_snap_y_from_xy(self, xs, ys):
        x_pos, _ = self.v_line.getPos()  # get current cursor possition
        
        # check settings of menu to decide the way to snap cursor - or not at all
        win = get_main_window(self.plot) # get top most qt win parent to access menu

        if win.actionSnap_to_nearest.isChecked():
            idx = get_nearest_idx(xs, x_pos)
            y_ret = ys[idx]
        
        elif win.actionSnap_to_maximum.isChecked():
            idx = get_max_within_mass_range(xs, ys, 
                                            get_nearest_idx(xs, x_pos),
                                            CURSOR_SNAP_RANGE_MASS_TO_MAX)
            y_ret = ys[idx]
        
        else: # no snap
            pass
                
        return y_ret
        
        
    def on_xpos_changed(self):
        ''' Position of cursor changed by draging it
        '''
        self.correct_position_for_snap()


    def move_to(self, direction='left'):
        x_pos, _ = self.get_position()
        xs, ys = self.plot.line.getData()
        idx = get_nearest_idx(xs, x_pos)
        if direction == 'left':
            if idx > 0: # is there a point to move to?
                self.set_position(xs[idx - 1], ys[idx - 1])
        if direction == 'right':
            if idx < len(xs) - 1: # is there a point to move to?
                self.set_position(xs[idx + 1], ys[idx + 1])