from PyQt5.QtWidgets import QMenu, QAction, QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QClipboard
from spectra import TOF_Spectra
from peak import Peak
from tree_items import ItemType, SpectraItem, PeakItem, FolderItem

from pyqtgraph import TreeWidget as QTreeWidget
from pyqtgraph.Qt import QtWidgets

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from spectra_plot import SpectraPlot

import json
import os

from logging_config import logger


COL_NUMS =      3   # number of columns in the tree 
COL_NUM_NAME =  0   # name column number
NAME_WIDTH =    250 # name column width of the tree
COLOR_WIDTH =   50  # color column width of the tree
SPECTRA_COLOR = 'w' # default color of spectrum

TREE_JSON =  "tree_widget.json"  # session json file, in which the 'tree' structure is saved

# ==============================================================================
# ========================== class SpectrasTree ================================
# ==============================================================================
class SpectrasTree(QTreeWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setColumnCount(COL_NUMS)
        self.setColumnWidth(0, NAME_WIDTH)   
        self.setColumnWidth(1, COLOR_WIDTH)  
        # self.resize(500, self.height())
        self.setEditTriggers(QTreeWidget.DoubleClicked)
        
        self.setSelectionMode(QTreeWidget.ExtendedSelection)
                
        self.plot : SpectraPlot = None     # referenfe to SpectraPlot(PlotWidget) instance

        self.connectSignalsSlots()


    def connectSignalsSlots(self):
        '''
        Connects signal to slots
        '''
        # The signal connetion 'currentItemChanged' is commented out because:
        # The signal is now connected by the 'plot' obj. itself to its 'update()'
        # self.currentItemChanged.connect(self.on_current_changed)
        self.itemChanged.connect(self.on_item_changed)


    def set_plot(self, plot):
        '''
        Set bidirectional references for tree (self) <-> plot objs.
        '''
        self.plot = plot
        self.plot.tree = self


    def load_spectras_ascii(self, files):
        '''
        Load TOF spectra files to the tree
        '''
        self.blockSignals(True)
        for fn in files:
            tof_spectra  = TOF_Spectra()
            tof_spectra.load_ascii(fn)
            
            text = tof_spectra.get_name()
            new_item = self._add_spectra_item(text)
            new_item.spectra = tof_spectra   # remember reference to instance
            new_item.setText(0, tof_spectra.get_name())
            # set color of color button
            color_widget = self.itemWidget(new_item, 1)
            color_widget.setColor(SPECTRA_COLOR)
            logger.info(f"Loaded ascii spectra: '{tof_spectra.get_name()}'")        
        
        self.blockSignals(False)
        # make the last loaded item current in the tree
        self.setCurrentItem(new_item)
    
    
    def load_spectras_bin(self, files):
        '''
        Load TOF spectra files to the tree
        '''
        self.blockSignals(True)
        for fn in files:
            tof_spectra  = TOF_Spectra()
            tof_spectra.load_bin(fn)
            
            text = tof_spectra.get_name()
            new_item = self._add_spectra_item(text)
            new_item.spectra = tof_spectra   # remember reference to instance
            new_item.setText(0, tof_spectra.get_name())
            # set color of color button
            color_widget = self.itemWidget(new_item, 1)
            color_widget.setColor(SPECTRA_COLOR)
            logger.info(f"Loaded binary spectra: '{tof_spectra.get_name()}'")
        
        self.blockSignals(False)
        # make the last loaded item current in the tree
        self.setCurrentItem(new_item) 


    def _add_spectra_item_to_current(self, text):
        '''
        Add spectra item to the folder of current item of the tree
        '''
        folder = self.get_folder_parent(self.currentItem())

        if folder:
            # Add as child if an item is selected
            new_item = SpectraItem(folder, text)
        else:
            # Add as root item if no item is selected
            new_item = SpectraItem(self, text)

        return new_item
    

    def _add_spectra_item(self, text):
        '''
        Add spectra item to the root of the tree
        For adding to current use '_add_spectra_item_to_current'
        '''
        # Add as root item if no item is selected
        new_item = SpectraItem(self, text)

        return new_item
    
    
    def add_peak_item_to_current(self, peak : Peak):
        parent = self.get_spectra_parent(self.currentItem())

        if parent:
            # Add as child if an item is selected
            item = PeakItem(parent, peak.get_name(), check=Qt.Checked)
        else:
            # Add as root item if no item is selected
            item = PeakItem(self, peak.get_name(), check=Qt.Checked)

        item.peak = peak   # remember reference to the peak instance
        logger.info(f"Added peak: '{peak.get_name()}'")
        # connect signal for change of color to update plot
        
        return item
        
        
    def add_folder_to_current(self):
        current = self.currentItem()
        # should it be created in the root?
        if not current:
            # current = self             
            return
        new_item = FolderItem(None, 'folder')
        current.insertChild(0, new_item)
        self.setCurrentItem(new_item)  # Set the new item as the current item
        self.scrollToItem(new_item)    # Scroll to the new item to bring it into view
        logger.info(f"Added folder: '{new_item.text(0)}'")


    def get_folder_parent(self, item):
        '''
        Gets a parent item of FOLDER type upword in the tree
        '''
        current_item = item
        while current_item is not None:
            if current_item.type == ItemType.FOLDER:
                return current_item
            current_item = current_item.parent()
        
        return None     # when it come here it reached the root


    def get_folder_or_spectra_parent(self, item):
        '''
        Gets a parent item of FOLDER or SPECTRA type upword in the tree
        '''
        current_item = item
        while current_item is not None:
            if current_item.type == ItemType.FOLDER or \
               current_item.type == ItemType.SPECTRA:
                return current_item
            
            current_item = current_item.parent()
        
        return None     # when it come here it reached the root


    def get_spectra_parent(self, item=None) -> SpectraItem:
        '''
        Gets parent of SPECTRA type for an 'item' travesing upword in tree
        '''
        if item:
            current_item = item
        else:
            current_item = self.currentItem()   # if item is not specified use current
            
        while current_item:
            if current_item.type == ItemType.SPECTRA:
                return current_item
            current_item = current_item.parent()
        
        return None     # should not come up to here


    def get_all_children(self, item, type = None):
        '''
            Recursively get all children of the given 'item' - QTreeWidgetItem of tree.
        Args:
            item (QTreeWidgetItem): Item of tree for which to get all children
            type (list of ItemType enum): Should be list of ItemType class. Defaults to None.
        Returns:
            QTreeWidgetItem: List of children items 
        '''
        children = []
        def _get_children(item):
            for index in range(item.childCount()):
                child = item.child(index)
                if type:                        # if 'type' is specified in arg
                    if child.type in type:  
                        children.append(child)
                else:
                    children.append(child)       # if type=None
                    
                _get_children(child)
        _get_children(item)
     
        return children

    
    def get_peaks(self, item = None, checked=True):
        '''
        Gets all peaks of the tree. If 'checked' is True only checked peaks are
        returned taking folder structure and check box state into account.
        Parent folder check state has higher priority than the state of the child peaks or folders.
        '''
        items = []
        if not item:
            item = self.currentItem() # get current item if not specified
            
        spectra_item = self.get_spectra_parent(item)
        if spectra_item:
            for peak_item in self.get_all_children(spectra_item, [ItemType.PEAK]):
                # filter based on checkbox state
                if checked:
                    # is the peak item in some folder item? Check if all parent folders are checked
                    i = peak_item
                    is_checked = True
                    while i.parent().type == ItemType.FOLDER:
                        i = i.parent()
                        if i.checkState(0) == Qt.Unchecked:
                            is_checked = False # if any parent folder is unchecked break
                            break
                    # test if the peak item is checked
                    if is_checked:
                        if peak_item.checkState(0) == Qt.Checked:
                            items.append(peak_item) # add only checked peaks

                else: 
                    items.append(peak_item)  # add all items checked is not important
                    
        return items
        
        
    def get_current_type(self) -> ItemType:
        '''
        Returns current type of item selectet in the tree.
        If nothing is selected it returns 'None'
        '''        
        current_item = self.currentItem()
        # if something is selectet in tree is should have a type of 'ItemType'
        if current_item:
            return current_item.type
        
        return None    # if nothing is selected
    
    
    def is_current_peak(self) -> bool:
        '''
        Returns True if selected item in tree is type of peak type, else it retun False
        '''        
        current_item_type = self.get_current_type()
        
        if current_item_type == ItemType.PEAK:
            return True

        return False        

    
    def _get_all_items(self):
        '''
        Returns list of all items of the tree.
        '''        
        def recurse(item):
            items = []
            items.append(item)
            for i in range(item.childCount()):
                items.extend(recurse(item.child(i)))
            return items

        all_items = []
        for i in range(self.topLevelItemCount()):
            all_items.extend(recurse(self.topLevelItem(i)))
        return all_items
        
        
    def get_checked_spectras(self):
        '''
            Returns all checked spectras in the tree.
        '''        
        items = []
        # filter items
        for item in self._get_all_items():
            if item.checkState(0) == Qt.Checked and item.type == ItemType.SPECTRA:
                items.append(item)
                
        return items

        
    def on_item_changed(self, item, column):
        if item.type == ItemType.PEAK:
            if column == COL_NUM_NAME:
                # check if it not empty
                # when tree item is created the event is called before .peak assignment
                if item.peak:
                    old_name = item.peak.get_name()
                    new_name = item.text(column)
                    # check if the name was changed
                    if old_name != new_name:
                        item.peak.set_name(item.text(column))
                        # name changed -> try to update molecule iso pattern
                        item.peak.init_molecule()
                        logger.info(f"Peak name changed: '{old_name}' -> '{new_name}'")
                     
                    # update even name was not changed e.g. check box is changed
                    self.plot.update()
                    
        if item.type == ItemType.FOLDER:
            if column == COL_NUM_NAME:
                # name of the folder was changed
                if item.name_txt != item.text(column):
                    logger.info(f"Folder name changed: '{item.name_txt}' -> '{item.text(column)}'")
                    item.name_txt = item.text(column)
                # based on check box state show/hide children
                self.plot.update()
                    

                    
    def keyPressEvent(self, event):
        current_item = self.currentItem()

        if event.key() == Qt.Key_C and event.modifiers() == Qt.ControlModifier:
            # Ctrl + C pressed
            self.copy_isotopes_to_clipboard()
        
        # to deselect items if Esc is pressed (same as click to the empty place in tree)
        elif (event.key() == Qt.Key_Escape and
            event.modifiers() == Qt.NoModifier):
            self.selectionModel().clear()

        # Check if the F2 key was pressed
        elif event.key() == Qt.Key_F2:
            if current_item:
                # Make the current item editable
                self.editItem(current_item, 0)  # Edit the first column

        elif event.key() == Qt.Key_Delete:
            if current_item:
                self.blockSignals(True)
                self.remove_selected_items()
                self.blockSignals(False)

        elif event.key() == Qt.Key_J:
            if current_item.type == ItemType.PEAK:
                self.scroll_to_peak()

        else:
            super().keyPressEvent(event)
            

    def mousePressEvent(self, event):
        # deselect items when clicking to emty space in tree widget
        # added due to possibitity to put itemes to root of the tree
        if not self.indexAt(event.pos()).isValid():
            self.selectionModel().clear()
        
        super().mousePressEvent(event)
        
        
    def startDrag(self, ev):
        # self.blockSignals(True)
        super().startDrag(ev)
        
    def dropEvent(self, ev):
        # self.blockSignals(False)
        super().dropEvent(ev)

    
        
    # slot evoked by moving of tree items. Used to check it if can be moved,
    # 'item' is moving into its new 'parent' 
    # 'return False' cause ignorig of the drag & drop process
    def itemMoving(self, item, parent, index):
        if parent:
            if not self._is_move_allowed(item, parent):
                return False
        else:
            # root item are moved
            if item.type == ItemType.PEAK or item.type == ItemType.FOLDER:
                return False # not move allowed in root for peaks and folders
                        
        return True

    def _is_move_allowed(self, item, parent):
        # table of allowed moves 1st column is item to move, 2nd column is where to move
        # 3 possibilities for item/parent types are: 'PEAK', 'SPECTRA', 'FOLDER'
        # the third column is True, False whter the move is allowed or not
        allowance_table = [[ItemType.PEAK,      ItemType.PEAK,      False],
                           [ItemType.PEAK,      ItemType.SPECTRA,   True],
                           [ItemType.PEAK,      ItemType.FOLDER,    True],
                           [ItemType.SPECTRA,   ItemType.PEAK,      False],
                           [ItemType.SPECTRA,   ItemType.SPECTRA,   False],
                           [ItemType.SPECTRA,   ItemType.FOLDER,    False],
                           [ItemType.FOLDER,    ItemType.PEAK,      False],
                           [ItemType.FOLDER,    ItemType.SPECTRA,   True],
                           [ItemType.FOLDER,    ItemType.FOLDER,    True]]
        
        for row in allowance_table:
            if item.type == row[0] and parent.type == row[1]:
                return row[2]
            
        raise ValueError('Item type not found in the allowance table')


#-------------------------------------------------------------------------------
# Contex menu & slot functions -------------------------------------------------
# ------------------------------------------------------------------------------
    
    def copy_isotopes_to_clipboard(self):
        current = self.currentItem()
        if current.type == ItemType.PEAK:
            current.peak.copy_to_clipboard()
            
            
    def copy_spectrum_to_clipboard(self):
        spectra = self.currentItem()

        if spectra:
            # compose txt table
            txt = 'mass \t counts\n'              # head
            xs, ys = spectra.spectra.get_xy()     # body data - mass, counts
            for x, y in zip(xs, ys):
                txt += f"{x:.3f} \t {y:.3f}\n"
            
            clipboard = QApplication.clipboard()
            clipboard.setText(txt, QClipboard.Clipboard)


    def _peaks_to_clipboard(self, peak_items):
        '''
        Copy peaks coordinates into clipboard
        '''
        if peak_items:
            # compose txt table
            txt = 'mass \t counts\t name\n'     # head
            for peak in peak_items:             # body with data
                x, y = peak.peak.get_xy()       # mass, counts
                name = peak.peak.get_name()     # name - text
                txt += f"{x:.3f} \t {y:.3f} \t {name} \n"
            
            clipboard = QApplication.clipboard()
            clipboard.setText(txt, QClipboard.Clipboard)
                 
                              
    def copy_peaks_to_clipboard(self, checked=True):
        '''
        Copy coordinates of all or checked peaks withing the selected spectra item 
        to clipboard
        '''        
        peak_items = self.get_peaks(checked=checked)
        self._peaks_to_clipboard(peak_items)        


    def copy_selected_peaks_to_clipboard(self):
        '''
        Copy coordinates of selected peaks to clipboard
        '''        
        selected_items = self.selectedItems()
        self._peaks_to_clipboard(selected_items)
        
        
    def create_folder(self):
        self.add_folder_to_current()


    def remove_selected_items(self):
        selected_items = self.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            # Determine if item is a top-level item or a child
            parent = item.parent()
            if parent is None:
                # Remove top-level item
                index = self.indexOfTopLevelItem(item)
                self.takeTopLevelItem(index)
            else:
                # Remove child item
                index = parent.indexOfChild(item)
                parent.takeChild(index)
                
            logger.info(f"Removed item: '{item.text(0)}', type={item.type}")

        self.plot.update()
    
    
    def move_item(self, item, parent, index):
        '''
        Move 'item' to the 'parent' at the index and preserve the interated widgets
        It slightly modified version of the original method from 
        'pyqtgraph' - 'dropMimeData'. The modification is made due to the fact 
        that the original method is moving just single item and not mutliple items.
        '''        
        p = parent
        #print "drop", item, "->", parent, index
        while True:
            if p is None:
                break
            if p is item:
                return False
                #raise Exception("Can not move item into itself.")
            p = p.parent()
        
        if not self.itemMoving(item, parent, index):
            return False
        
        currentParent = item.parent()
        if currentParent is None:
            currentParent = self.invisibleRootItem()
        if parent is None:
            parent = self.invisibleRootItem()
            
        if currentParent is parent and index > parent.indexOfChild(item):
            index -= 1
            
        self.prepareMove(item)
            
        currentParent.removeChild(item)
        #print "  insert child to index", index
        parent.insertChild(index, item)  ## index will not be correct
        self.setCurrentItem(item)
        
        self.recoverMove(item)
        self.sigItemMoved.emit(item, parent, index)
        logger.info(f"Moved item: '{item.text(0)}' -> '{parent.text(0)}', position={index}")
        return True


    def move_peaks_to_new_folder(self):
        '''
        Move selected peaks and sub folders to new (created) folder
        '''        
        items = self.selectedItems()
        if not items:
            return
        
        self.blockSignals(True)
        
        parent = self.get_folder_or_spectra_parent(items[0])
        new_folder = FolderItem(None, 'folder')
        new_folder.setCheckState(0, Qt.Checked) # set unchecked state to the new folder
        parent.insertChild(0, new_folder)  # add new folder to the parent to the first position
        
        # move all selected peaks to parent
        for idx, item in enumerate(items):
            self.move_item(item, new_folder, idx)
        
        new_folder.setExpanded(False)    # colapse the folder
        self.setCurrentItem(new_folder)  # Set the new item as the current item
        self.scrollToItem(new_folder)    # Scroll to the new item to bring it into view
        self.blockSignals(False)
        self.plot.update()
        
        
    def are_same_parent(self, items):
        '''
        Check if all items are from the same parent
        '''
        parent = items[0].parent()
        for item in items:
            if item.parent() != parent:
                return False
            
        return True
    
    def dropMimeData(self, parent, index, data, action):
        '''
        Modified version of the original method from 'pyqtgraph' and 'pyqt5',
        to work with multiple items
        '''    
        items = self.selectedItems()
        if not items or not self.are_same_parent(items):
            return

        self.blockSignals(True)

        for i, item in enumerate(items):
            # item is moving down to the same parent - do not increment index
            # moving down behaves differently than moving up (or to the new parent)
            if item.parent() == parent and index > parent.indexOfChild(item):
                i = 0
            
            self.move_item(item, parent, index + i)
        
        self.blockSignals(False)
        self.plot.update()
        
        return True
                    
    
    def check_selected_items(self):
        self.blockSignals(True)
        selected_items = self.selectedItems()
        for item in selected_items:
            item.setCheckState(0, Qt.Checked)
        self.blockSignals(False)
        self.plot.update()
            
    def uncheck_selected_items(self):
        self.blockSignals(True)
        selected_items = self.selectedItems()
        for item in selected_items:
            item.setCheckState(0, Qt.Unchecked)
            self.plot.update()
        self.blockSignals(False)
        self.plot.update()
        
        
    def scroll_to_peak(self):
        self.plot.scroll_x_to(self.currentItem().peak.get_xy()[0])
            
            
    def contextMenuEvent(self, event):
        current = self.currentItem()
        current_type = None
        if current:             # in root current is 'None'
            current_type = current.type

        context_menu = QMenu(self)
        
        if current_type == ItemType.PEAK:
            # copy_isotopes_action.setEnabled(False) # make disabled
            copy_isotopes_action = QAction("Copy isotopes", self)
            copy_isotopes_action.triggered.connect(self.copy_isotopes_to_clipboard)
            context_menu.addAction(copy_isotopes_action)

            # copy isotopes coordinates of selected peak items x y to clipboard
            copy_peaks_xy_action = QAction("Copy (x, y)", self)
            copy_peaks_xy_action.triggered.connect(self.copy_selected_peaks_to_clipboard)
            context_menu.addAction(copy_peaks_xy_action)

            context_menu.addSeparator()

            # add to new folder
            move_peaks_to_new_folder_action = QAction("Move to new folder", self)
            move_peaks_to_new_folder_action.triggered.connect(self.move_peaks_to_new_folder)
            context_menu.addAction(move_peaks_to_new_folder_action)

            # check selected peaks
            check_peaks_action = QAction("Check", self)
            check_peaks_action.triggered.connect(self.check_selected_items)
            context_menu.addAction(check_peaks_action)
            
            # uncheck selected peaks
            uncheck_peaks_action = QAction("Uncheck", self)
            uncheck_peaks_action.triggered.connect(self.uncheck_selected_items)
            context_menu.addAction(uncheck_peaks_action)

            context_menu.addSeparator()

            # jump to current peak in the plot
            jump_to_action = QAction("Jump to peak", self)
            jump_to_action.triggered.connect(self.scroll_to_peak)
            context_menu.addAction(jump_to_action)

            context_menu.addSeparator()
            

        if current_type == ItemType.SPECTRA:
            create_folder_action = QAction("Create folder", self)
            create_folder_action.triggered.connect(self.create_folder)
            context_menu.addAction(create_folder_action)
        
            context_menu.addSeparator()
            # copy spectrum
            copy_spectrum_action = QAction("Copy spectrum", self)
            copy_spectrum_action.triggered.connect(self.copy_spectrum_to_clipboard)
            context_menu.addAction(copy_spectrum_action)

            # copy checked out (in tree) peaks 
            copy_peaks_xy_action = QAction("Copy peaks - checked", self)
            copy_peaks_xy_action.triggered.connect(lambda: self.copy_peaks_to_clipboard(True))
            context_menu.addAction(copy_peaks_xy_action)

            # copy all peaks under selected spectra
            copy_all_peaks_action = QAction("Copy peaks - all", self)
            copy_all_peaks_action.triggered.connect(lambda: self.copy_peaks_to_clipboard(False))
            context_menu.addAction(copy_all_peaks_action)

            context_menu.addSeparator()
            
        # delete item
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self.remove_selected_items)
        context_menu.addAction(delete_action)
        
        action = context_menu.exec_(self.mapToGlobal(event.pos()))

#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# Contex menu & slot functions -------------------------------------------------
# ------------------------------------------------------------------------------

    def _color_to_dict(self, color):
        """Convert QColor to a dictionary and save to JSON"""
        color_dict = {
            'r': color.red(),
            'g': color.green(),
            'b': color.blue(),
            'a': color.alpha()
        }
        return color_dict
        
    def _color_from_dict(self, color_dict):
        """Load color from JSON and convert to QColor"""
        color = QColor(color_dict['r'], color_dict['g'], color_dict['b'], color_dict['a'])
        return color
   
   
    def _get_struct_to_save(self, folder):
        """
        Recursively save the structure of the QTreeWidget.
        """
        self.counter = 0
        
        def traverse_item(item, folder=folder):
            self.counter += 1
            fn_base = str(self.counter)     # to automaticaly name files for session
            fn = folder + '/' + fn_base     
            
            item.save_session(fn)           # save tree item to the file 'fn'
            if item.type == ItemType.SPECTRA:
                item_info = {
                    'text': item.text(0),
                    'check' : item.checkState(0),
                    'color' : self._color_to_dict(self.itemWidget(item, 1).color()),
                    'tags': item.text(2),
                    'type': item.type,
                    'fn' :  fn_base,
                    'children': [traverse_item(item.child(i), folder) for i in range(item.childCount())]
                }
            
            if item.type == ItemType.PEAK:
                item_info = {
                    'text': item.text(0),
                    'check' : item.checkState(0),
                    'color' : self._color_to_dict(self.itemWidget(item, 1).color()),
                    'tags': item.text(2),
                    'type': item.type,
                    'fn' : fn_base,
                    'children': [traverse_item(item.child(i), folder) for i in range(item.childCount())]
                }

            if item.type == ItemType.FOLDER:
                item_info = {
                    'text': item.text(0),
                    'check' : item.checkState(0),
                    'tags': item.text(2),
                    # 'check' : item.checkState(0),
                    # 'color' : self._color_to_dict(self.itemWidget(item, 1).color()),
                    'type': item.type,
                    'fn' : fn_base,
                    'children': [traverse_item(item.child(i), folder) for i in range(item.childCount())]
                }

            return item_info
        

        tree_structure = [traverse_item(self.topLevelItem(i), folder) for i in range(self.topLevelItemCount())]
        
        return tree_structure


    def save_session(self, folder):
        filename = os.path.join(folder, TREE_JSON)
        tree_structure = self._get_struct_to_save(folder)
        with open(filename, 'w') as file:
            json.dump(tree_structure, file, indent=4)

 
    def load_tree(self, folder):
        """
        Load the structure of the QTreeWidget from a file.
        Returns False when loading fails, otherwise returns True.
        """
        def add_items(parent, item_info):
            # check if tags key exists - backward compatibility  
            # if tags key exists in the dict, use it, otherwise use empty string
            if 'tags' in item_info:
                tags = item_info['tags']
            else:
                tags = ''   # default value if does not exist
            if 'check' in item_info:
                check = item_info['check']
            else:
                check = 0   # default value if does not exist
            
            # make item instance dependent on type
            if item_info['type'] == ItemType.SPECTRA:
                color = self._color_from_dict(item_info['color'])
                    
                item = SpectraItem(parent, item_info['text'], 
                                   check,
                                   color, 
                                   tags=tags)
                                   

            elif item_info['type'] == ItemType.PEAK:
                color = self._color_from_dict(item_info['color'])
                item = PeakItem(parent, item_info['text'], 
                                check,
                                color,
                                tags=tags)
                
            elif item_info['type'] == ItemType.FOLDER:
                # color = self._color_from_dict(item_info['color'])
                item = FolderItem(parent, item_info['text'],
                                  check,
                                  tags=tags)
                                # color)

            # load session for items 
            item.load_session(folder + '/' + item_info['fn'])            

            for child_info in item_info['children']:
                add_items(item, child_info)
            return item

        json_path = os.path.join(folder, TREE_JSON)

        if not os.path.exists(json_path):
            return False    # loading failed
                
        with open(json_path, 'r') as file:
            tree_structure = json.load(file)

        self.blockSignals(True)
        self.clear()
        
        for item_info in tree_structure:
            add_items(self, item_info)

            
        self.setEditTriggers(QTreeWidget.DoubleClicked)
        
        first_item = self.topLevelItem(0)
        if first_item is not None:
            self.setCurrentItem(first_item)
        
        self.blockSignals(False)
        self.plot.update()
        self.plot.update_lines()
        
        return True     # loading finished succesfully


    def delete_session_files(self, folder):
        """
        Delete all item tree related files - session
        """
        def del_items_files(item_info):
            file_base = item_info['fn']             # without extension 
            file_base_path = os.path.join(folder, file_base)
            if item_info['type'] == ItemType.SPECTRA:
                SpectraItem.delete_session_files(file_base_path) 

            elif item_info['type'] == ItemType.PEAK:
                Peak.delete_session_files(file_base_path) 
                
            elif item_info['type'] == ItemType.FOLDER:
                FolderItem.delete_session_files(file_base_path) 

            for child_info in item_info['children']:
                del_items_files(child_info)

        os.co
        json_file = os.path.join(folder, TREE_JSON)
        
        with open(json_file, 'r') as file:
            tree_structure = json.load(file)

        for item_info in tree_structure:
            del_items_files(item_info)

        os.remove(json_file)
        
        

            