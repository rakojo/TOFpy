from __future__ import annotations
from pyqtgraph import PlotWidget, BarGraphItem, TextItem, PlotDataItem, mkPen
from cursor import Cursor
import numpy as np
from PyQt5.QtGui import QFont, QBrush, QColor, QKeyEvent
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtWidgets import QApplication
from peak import Peak
from tree import SpectrasTree
from common import get_main_window
from logging_config import logger

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from offset_view import OffsetView
    from mass_err_view import MassErrView
    from tree_items import PeakItem

LAYER_BAR =     1     # layer number for bar plot - isotopes of the current peak
LAYER_LINE =    3     # plot layer for line plot - current spectra
LAYER_LINES =   2     # multiple plots layer
LAYER_ANNOT =   4     # annotation layer

PEAK_COLOR = 'b'      # peak item color of the color button

class SpectraPlot(PlotWidget):
    def __init__(self, parent=None, background='default', plotItem=None, **kargs):
        super().__init__(parent, background, plotItem, **kargs)

        self.tree : SpectrasTree = None    
                            # reference to tree obj. (class SpectrasTree)
                            # NOTE.: Tree and plot objs. have bidirectional 
                            # relationship. Tree obj. has also reference to 
                            # plot obj and so they point to each other.
                            
        
        # self.setBackground('w')
        self.pen=({'color': 'w', 'width': 1})
        self.line = self.plot(pen=self.pen)
        self.line.setZValue(LAYER_LINE)

        self.bar = BarGraphItem(x=0, height=0, width=0.3, brush=(102, 0, 0))
        self.addItem(self.bar)
        self.bar.setZValue(LAYER_BAR)
        # main isotope highlight - usually it will be monoisotopic mass
        self.bar_main = BarGraphItem(x=0, height=0, width=0.3, brush=(102, 0, 0),
                                     pen=mkPen('y', width=1.5))
        self.bar_main.setOpts()
        self.addItem(self.bar_main)
        self.bar_main.setZValue(LAYER_BAR)
        
        self.peaks_anno = AnnotatePlot(self, 'b')    # annotation for peaks
        self.clusters_anno = AnnotatePlot(self, 'r') # annotation for cluster peaks search window
        
        self.cursor = Cursor(self)
        
        self.lines = []     # plots for multiploting
                
        style = {'color': 'gray', 'font-size': '8pt'}
        self.setLabel('left', 'counts', **style)
        self.setLabel('bottom', 'mass (AMU)', **style)
        self.showGrid(x=True, y=True)
        
        self.resize(700, 900)
        self.main_win = get_main_window(self)

        
    # Note: This method it is called from 'main.py' (after finish instantiation
    # of the all needed clases and init. of references in '__init__' of the 'main.py')
    def connectSignalsSlots(self):
        # Detect signal of the 'tree' widget
        self.tree.currentItemChanged.connect(self.update)
        self.tree.itemChanged.connect(self.update_lines)
        self.tree.itemSelectionChanged.connect(self.update_peaks_anno_selection)


    def set_offset_view(self, offser_view : OffsetView):
        self.offset_view = offser_view


    def set_mass_error_view(self, mass_err_view : MassErrView):
        self.mass_err_view = mass_err_view
        mass_err_view.set_main_plot(self)


    def normalize(self):
        currrent = self.tree.currentItem()
        current_spectra = self.tree.get_spectra_parent(currrent)
        if current_spectra:
            x, y = current_spectra.spectra.get_xy()
            self.cur

    def update_lines(self):
        for line in self.lines:
            self.removeItem(line)
            
        self.lines.clear()

        # show all which are checked in check box
        for item in self.tree.get_checked_spectras():
            color_widget = self.tree.itemWidget(item, 1)
            line = self.plot(pen={'color': color_widget.color()})
            xs, ys = item.spectra.get_xy()
            print(self.cursor.get_snap_y_from_xy(xs, ys))
            line.setData(xs, ys)          
            line.setZValue(LAYER_LINES)
            self.lines.append(line) 
            

    def update(self):
        """
        Update plot based on the currently selected item in the tree widget.
        """
        current = self.tree.currentItem()   # get current item of tree widget
        # if current is None: return        # eg. there is nothing in the list and 'update' is called 
        self.update_peaks_anno(current)
        self.update_line(current)
        self.update_bar(current)
        
        
    def update_line(self, current : PeakItem):
        current_spectra = self.tree.get_spectra_parent(current)
        
        if current_spectra:
            x, y = current_spectra.spectra.get_xy()
            # normalize if menu option is checked in main window menu bar
            if self.main_win.actionCursorNormalize.isChecked():
                # y = y / self.cursor.get_position()[1]
                pass
                                
            self.line.setData(x, y)                  # update bar plot data
            self.cursor.correct_position_for_snap()  # to snap to new line data
            self.offset_view.set_xy(x, y)            # update offset_view
        else:
            self.line.setData([], [])               # clear plot
            self.offset_view.set_xy([], [])         # clear offset_view
     
     
    # For bars for isotopes pattern update
    def update_bar(self, current : PeakItem):
        if self.tree.is_current_peak() and current.peak.is_iso_not_empty():
            # rescale iso pattern to main peak intensity - it can be selected from pattern by user
            current.peak.scale_iso_pattern_to(current.peak.get_xy_main_iso()[0],
                                              current.peak.get_xy()[1])
            x, y = current.peak.get_xy_iso()         # get iso pattern
            xm, ym = current.peak.get_xy_main_iso()  # main iso peak - usually monoisotopic mass 
        else:
            x, y = (0, 0)        # bar plot not visible
            xm, ym, = (0, 0)

        self.bar.setOpts(x=x, height=y) # update data set of the bar plot it needs to be
                                        # done by 'setOpts' as there is no 'setData'
        self.bar_main.setOpts(x=xm, height=ym) # update data set 
    
    
    def update_peaks_anno(self, current : PeakItem = None):
        if not current:
            current = self.tree.currentItem()   # get current item of tree widget
        peaks = self.tree.get_peaks(current)

        if peaks:
            self.peaks_anno.add_peaks(peaks)    # add annotation of peaks to plot
            x, _, names = self.peaks_anno.get_peaks()
            self.offset_view.set_peaks(x, names)
            self.mass_err_view.set_peaks(peaks)
        else:
            self.peaks_anno.clear()             # there are no peaks to show
            self.offset_view.set_peaks([], [])
            self.mass_err_view.set_peaks([])
            
        self.offset_view.update()
            

    def update_peaks_anno_selection(self):
        current = self.tree.currentItem()   # get current item of tree widget
        peaks = self.tree.get_peaks(current)

        if peaks:
            self.peaks_anno.add_peaks(peaks)    # add annotation of peaks to plot
        else:
            self.peaks_anno.clear()             # there are no peaks to show
            

    # scroll plot to the new x for the center of view, value keeping the same range 
    def scroll_x_to(self, x):
        x_min, x_max = self.viewRange()[0]       # current x range
        relative_move = x - (x_min + x_max) / 2  # move to the center (x) of the view
        self.plotItem.vb.translateBy(x = relative_move)


    def mouseDoubleClickEvent(self, ev):
        pos = ev.pos()
        scene_pos = self.plotItem.vb.mapSceneToView(pos)
        x_pos, y_pos = scene_pos.x(), scene_pos.y()
        
        # get current item of tree widget and then the top most pareten type of spectra
        current = self.tree.get_spectra_parent(self.tree.currentItem())

        # move cursor
        self.cursor.set_position_and_snap(x_pos, y_pos)     # move to new pos_x
        
        super().mouseDoubleClickEvent(ev)


    def mousePressEvent(self, ev):
        # if mouse clicked outside of the annotation text items
        for item in self.peaks_anno.peaks_text_items:
            if item.pos() == ev.pos():
                # print("Mouse press event for text item")
                pass
            else:
                # print("Mouse press event outside of anno text")
                pass
            
        return super().mousePressEvent(ev)


    def keyPressEvent(self, event):
            # add peak to plot and tree
            if event.key() == Qt.Key_A:
                self.tree.blockSignals(True)
                x, y = self.cursor.get_position()
                peak = Peak()
                peak.set_xy(x, y)
                peak.set_name(f'{x:.2f}')
                
                spectra = self.tree.get_spectra_parent()
                if spectra:
                    t = spectra.spectra.get_nearest_t_by_x(x)
                    peak.set_t(t)

                item = self.tree.add_peak_item_to_current(peak)
                # set peak item color button
                color_widget = self.tree.itemWidget(item, 1)
                color_widget.setColor(PEAK_COLOR)

                self.tree.blockSignals(False)
                self.update()
            
            # move peak to the cursor position - read new position to peak
            if event.key() == Qt.Key_M:
                self.tree.blockSignals(True)
                if not self.tree.is_current_peak():
                    return
                x, y = self.cursor.get_position()
                peak = self.tree.currentItem().peak
                x_old, y_old = peak.get_xy()
                peak.set_xy(x, y)
                
                spectra = self.tree.get_spectra_parent()
                if spectra:
                    t = spectra.spectra.get_nearest_t_by_x(x)
                    peak.set_t(t)

                logger.info(f"Moved peak '{peak.name}' ({x_old:.2f}, {y_old:.2f}) -> ({x:.2f}, {y:.2f})")
                self.tree.blockSignals(False)
                self.update()

            # when left or right arrow key is pressed
            elif event.key() == Qt.Key_Left:
                self.cursor.move_to('left')
            elif event.key() == Qt.Key_Right:
                self.cursor.move_to('right')
                
            elif event.key() == Qt.Key_Delete:
                key_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Delete, Qt.NoModifier)
                QApplication.postEvent(self.tree, key_event)                
                
            else:
                super().keyPressEvent(event)



class MyTextItem(TextItem):
    def __init__(self, text, peak_item, **kargs):
        super().__init__(text, **kargs)
        self.setAcceptHoverEvents(True)
        self.setFlag(self.ItemIsSelectable)
        # self.setFlag(self.ItemIsMovable)  # Optional: allows the item to be moved

        self.tree = peak_item.treeWidget()  # get tree widget of the peak item
        self.peak_item = peak_item           # set reference to related peak item
        self.peak_item.anno_text = self # set back reference to this TextItem

        self.normal_fill_color = kargs.get('fill')
        self.normal_border_color = kargs.get('border')
        self.update()
        

    def update(self):
        color = "#cde8ff" # selection color
        lighter = self.normal_fill_color.lighter(150) # set color lighter by 50%

        if self.peak_item:
            if self.peak_item.isSelected():
                self.fill = QBrush(lighter)
                self.border = mkPen(color, width=5)
                self.setColor('k')
                self.setZValue(LAYER_ANNOT+1)
            else:
                self.fill = QBrush(QColor(self.normal_fill_color))
                self.border =  mkPen(self.normal_border_color, width=1)
                self.setZValue(LAYER_ANNOT)


    def mousePressEvent(self, ev):
        self.tree.setCurrentItem(self.peak_item)
        super().mousePressEvent(ev)
    

    def hoverEnterEvent(self, ev):
        self.normal_fill_color = self.fill.color()
        lighter = self.normal_fill_color.lighter(150) # set color lighter by 50%
        self.fill = QBrush(lighter) 
        super().hoverEnterEvent(ev)
        

    def hoverLeaveEvent(self, ev):
        self.fill = QBrush(self.normal_fill_color) # set color back to default
        super().hoverLeaveEvent(ev)
        
        

class AnnotatePlot():
    '''
    The class used for an annotation of plot peaks i.e. mark position 
    and label it with a text. It creates list of 'TextItem' and 
    '''    
    def __init__(self, plot: PlotWidget, color='w') -> None:
        self.plot = plot
        self.color = color
        self.peak_items = []          # list of peak items
        self.peaks_text_items = []    # text items for labeling peaks
       
        style = POINT_STYLE
        style['symbolBrush'] = color            # set fill color of symbols
        self.scatter : PlotDataItem = self.plot.plot(**style)  # create scatter item for marking peaks
        self.scatter.setZValue(LAYER_ANNOT)
        
        
    def clear_texts(self):
        for i in self.peaks_text_items:
            i.scene().removeItem(i)
        self.peaks_text_items = []
        
        
    def add_text(self, text, pos_x, pos_y, color = None, peak_item = None):
        font = QFont()
        font.setPixelSize(18)       # TODO
        style = TEXT_STYLE
        if color:
            style['fill'] = color
        else:
            style['fill'] = self.color
        
        if peak_item:
            item = MyTextItem(text, peak_item, **style)
        else:
            item = TextItem(text, **style)
            
        self.peaks_text_items.append(item)
        # self.plot.addItem(item)           # slow and time consuming operation
        item.setParentItem(self.scatter)    # faster way to add item to the plot
        item.setPos(pos_x, pos_y)
        item.setFont(font)


    def clear(self):
        self.clear_texts()
        self.scatter.setData([], [])             


    def add_list(self, texts, pos_xs, pos_ys, colors, peak_items = []):

        self.clear_texts()
        
        if peak_items:
            for txt, x, y, color, peak_item in zip(texts, pos_xs, pos_ys, 
                                                   colors, peak_items):
                self.add_text(txt, x, y, color, peak_item)
        else:
            for txt, x, y, color in zip(texts, pos_xs, pos_ys, colors):
                self.add_text(txt, x, y, color)
                
        # set symbol positions and there colors equal to text color
        # some other param. for future pen, symbolBrush, symbolPen='w', symbol='s', 
        self.scatter.setData(pos_xs, pos_ys, symbolBrush = colors)
    

    def add_peaks(self, peak_items):
        '''
        Reads informations form the list of peaks to annotate them
        on the plot.

        Args:
            peaks ([PeakItem]): list of peaks items of the tree
        '''    
        pos_xs = []
        pos_ys = []
        texts = []
        colors = []
        # prepare list used for annotation
        for item in peak_items:
            texts.append(item.peak.get_name())      # get peak text
            x, y = item.peak.get_xy()               # get peak position
            pos_xs.append(x)
            pos_ys.append(y)
            color_widget = self.plot.tree.itemWidget(item, 1)
            # print(item, color_widget)  # TODO error 'None' when moving item from 
            colors.append(color_widget.color())

        # apply list for annotation 
        self.add_list(texts, pos_xs, pos_ys, colors, peak_items)
        
        
    def get_peaks(self):
        names = [i.toPlainText() for i in self.peaks_text_items]
        x, y = self.scatter.getData()
        return x, y, names
        
        
        
TEXT_STYLE = {'color': (200, 200, 200),
                'html': None,
                'anchor': (-0.4, 0.5),
                'border': 'w',
                'fill': None,
                'angle': 90,
                'rotateAxis': None
                }

POINT_STYLE = {'pen': None, 
                'symbolBrush': (0, 0, 255, 100),
                'symbolPen': 'w', 
                'symbol': 'arrow_down',
                'symbolSize': 44
                }



   
