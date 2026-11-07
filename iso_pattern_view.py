import sys
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget
import pyqtgraph as pg
import numpy as np
import peak as Peak
from common import get_nearest_idx

COLOR_HIGH  = 'y'
COLOR_HOVER = (167, 0, 0)
COLOR_NORM  = (102, 0, 0)
BAR_WIDHT =   0.6

class IsoPatternView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, )
        self.setWindowTitle("Isotops Pattern View")

        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Create a PlotWidget
        self.plot_widget = pg.PlotWidget()
        layout.addWidget(self.plot_widget)        

        # Initialize data storage for bars
        self.bars = []
        self.xs = []
        self.ys = []
        self.hovered_bar_idx = None
        self.selected_bar_idx = None

        self.connectSignalSlots()


    def connectSignalSlots(self):
        self.plot_widget.scene().sigMouseClicked.connect(self.on_bar_clicked)
        self.plot_widget.scene().sigMouseMoved.connect(self.on_mouse_hover)


    def set_data(self, xs, ys):
        """Sets the data for the bar graph with custom x and y coordinates."""
        self.xs = np.array(xs)
        self.ys = np.array(ys)
        
        # Clear any existing bars
        for bar in self.bars:
            self.plot_widget.removeItem(bar)
        self.bars = []
        self.selected_bar_idx = None
        self.hovered_bar_idx = None

        # Create and plot the bars individually with initial color blue
        for x, y in zip(self.xs, self.ys):
            bar = pg.BarGraphItem(x=[x], height=[y], width=BAR_WIDHT, brush=COLOR_NORM)
            self.bars.append(bar)
            self.plot_widget.addItem(bar)
            
            
    def set_selected(self, mass, color=COLOR_HIGH):
        '''Select higlighted bar by selected 'mass'.'''
        if mass:        
            self.selected_bar_idx = get_nearest_idx(self.xs, mass)
            self.bars[self.selected_bar_idx].setOpts(brush=color)
        

    def on_bar_clicked(self, event):
        """Handles the bar click event."""
        # if there are no bars, return
        if len(self.bars) <= 0:
            return

        pos = event.scenePos()
        if self.plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
            clicked_x = mouse_point.x()
            clicked_y = mouse_point.y()

            # Ignore clicks outside the plotting bars area
            if (clicked_x < (min(self.xs) - BAR_WIDHT/2) or 
                clicked_x > (max(self.xs) + BAR_WIDHT/2) or
                clicked_y < 0):
                return

            # Determine which bar was clicked
            bar_idx = np.argmin(np.abs(self.xs - clicked_x))
            if 0 <= bar_idx < len(self.ys):
                # Deselect the previously selected bar, if any
                if self.selected_bar_idx is not None:
                    # set color to deselected bar
                    self.bars[self.selected_bar_idx].setOpts(brush=COLOR_NORM)
                # Select the clicked bar - set color
                self.selected_bar_idx = bar_idx
                self.bars[self.selected_bar_idx].setOpts(brush=COLOR_HIGH)
                

    def on_mouse_hover(self, event):
        """Handles the mouse hover event."""
        # if there are no bars, return
        if len(self.bars) <= 0:
            return

        pos = event
        if self.plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
            hovered_x = mouse_point.x()
            hovered_y = mouse_point.y()


            # Ignore clicks outside the plotting bars area
            if (hovered_x < (min(self.xs) - BAR_WIDHT/2) or 
                hovered_x > (max(self.xs) + BAR_WIDHT/2) or
                hovered_y < 0):
                self._reset_hovered_bar()
                return

            # Determine which bar is hovered over
            bar_index = np.argmin(np.abs(self.xs - hovered_x))
            if 0 <= bar_index < len(self.ys):
                if self.hovered_bar_idx != bar_index:
                    # Reset the previously hovered bar, if any
                    if self.hovered_bar_idx is not None and self.hovered_bar_idx != self.selected_bar_idx:
                        self.bars[self.hovered_bar_idx].setOpts(brush=COLOR_NORM)
                        
                    # Highlight the currently hovered bar if it's not selected
                    if bar_index != self.selected_bar_idx:
                        self.bars[bar_index].setOpts(brush=COLOR_HOVER)

                    self.hovered_bar_idx = bar_index
            else:
                # If the mouse is not hovering over any bar, reset the previously hovered bar
                self._reset_hovered_bar()


    def _reset_hovered_bar(self):
        if len(self.bars) <= 0:
            return
        if self.hovered_bar_idx is not None and self.hovered_bar_idx != self.selected_bar_idx:
            self.bars[self.hovered_bar_idx].setOpts(brush=COLOR_NORM)
            self.hovered_bar_idx = None
    
    
    def enterEvent(self, event):
        # Reset the previously hovered bar when the mouse enters the widget area
        self._reset_hovered_bar()


    def leaveEvent(self, event):
        # Reset the previously hovered bar when the mouse leaves the widget area
        self._reset_hovered_bar()

    
    def get_selected_mass(self):
        if self.selected_bar_idx is not None:
            return self.xs[self.selected_bar_idx]
        return None


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = IsoPatternView()
    win.set_data([0, 1.8, 2.2, 5.5, 7, 9.2], [1, 5, 3, 7, 9, 4])  # Example x and y data
    win.show()
    
    sys.exit(app.exec_())
