# -*- coding: utf-8 -*-
"""
Created in 2018

@author: Shekoufeh Gorgi Zadeh
"""


import time
import numpy as np
import scipy as sc
import os, sys, inspect
import qimage2ndarray as q2np

from PyQt4 import QtGui
from bresenham import bresenham
from skimage.filters import threshold_otsu


viewPath=os.path.realpath(os.path.abspath(os.path.split(inspect.\
         getfile( inspect.currentframe() ))[0]))[:-10]+"view"
modelPath=os.path.realpath(os.path.abspath(os.path.split(inspect.\
         getfile( inspect.currentframe() ))[0]))[:-10]+"model"

if viewPath not in sys.path:
     sys.path.insert(0, viewPath)
     
if modelPath not in sys.path:
     sys.path.insert(0, modelPath)     
     
import edited_main_window as mw
import enface_drusen_controller as edc
from oct import OCT

#==============================================================================
# Main controller class of the OCT Editor. 
#==============================================================================
class OCTController:
    def __init__(self,app):
        self.oct=OCT(self)
        self.mainWindow=None
        
        self.currentScanNumber=1
        self.currentLayerNumber=1
        self.currentHRFNumber=1
        self.currentGANumber=1
        self.currentDrusenNumber=1
        self.currentEnfaceNumber=1
        self.currentEnfaceDrusenNumber=1
        self.linkViewers=False
        self.activaViewerSet=set()
        self.enfaceDrusenController=None
        
        self.scanCoeff=0.0
        self.layerCoeff=0.0
        self.drusenCoeff=1.0
        self.enfaceCoeff=0.0
        self.drusenEnfaceCoeff=1.0
        self.all_threshold=1
        self.max_threshold=2
        
        self.drusenEditted=False
        self.layerEditted=False
        self.hrfEditted=False
        self.gaEditted=False
        self.enfaceEditted=False
        self.enfaceDrusenEditted=False
        self.applyThresholdImmediately=False
        
        self.editBM=False
        self.editRPE=False
        
        self.logFile=os.path.join(os.path.realpath(os.path.abspath(os.path.\
                     split(inspect.getfile( inspect.currentframe() ))[0])),\
                     'log.txt')
        
        MainWindow=mw.MainWindow(self)
        ui = mw.Ui_MainWindow()
        ui.setupUi(MainWindow)
        self.mainWindowUi=ui
        self.mainWindow=MainWindow
        self.mainWindowUi.oct_controller=self
        
        self.enfaceDrusenViewOpen=False
        self.mainWindow
        self.lastScanPath=''
        
        self.lineS=[]
        self.lineY=[]
        self.lineX=[]
        self.linePrevValues=[]
        self.lineRedoValues=[]
        self.seenPoints=set()
        
        self.app=app
        
    def delete_previous(self):
        """
        When a scan is completely closed. Cleans up the views and values.
        """
        self.currentScanNumber=1
        self.currentLayerNumber=1
        self.currentHRFNumber=1
        self.currentGANumber=1
        self.currentDrusenNumber=1
        self.currentEnfaceNumber=1
        self.currentEnfaceDrusenNumber=1
        self.linkViewers=False
        self.activaViewerSet=set()
        
        self.scanCoeff=0.0
        self.layerCoeff=0.0
        self.drusenCoeff=1.0
        self.enfaceCoeff=0.0
        self.drusenEnfaceCoeff=1.0
        
        self.all_threshold=1
        self.max_threshold=2
        
        self.drusenEditted=False
        self.layerEditted=False
        self.hrfEditted=False
        self.gaEditted=False
        self.enfaceEditted=False
        self.enfaceDrusenEditted=False
        self.mainWindowUi.delete_previous()
        
        self.enfaceDrusenViewOpen=False
        self.applyThresholdImmediately=False
        
        self.editBM=False
        self.editRPE=False
        
        if(not self.enfaceDrusenController is None):
            del self.enfaceDrusenController
            self.enfaceDrusenController=None
            
        self.lineS=[]
        self.lineY=[]
        self.lineX=[]
        self.linePrevValues=[]
        self.lineRedoValues=[]
        self.seenPoints=set()
        del self.oct
        self.oct=OCT(self)
      
    def open_scan(self):
        """
        Opens an OCT volume.
        """
        debug=False
        if(debug):
            scanPath="..."
            self.lastScanPath=scanPath
        else:
            scanPath=self.mainWindowUi.get_scan_path(self.lastScanPath)
            self.lastScanPath=scanPath
        if(scanPath!=''):
            self.delete_previous()
            self.oct.set_scan_path(scanPath)
            self.oct.read_scan_from(scanPath)
            npimg=self.oct.get_scan()[:,:,self.currentScanNumber-1]
            self.mainWindowUi.show_scan(npimg,self.oct.numSlices)
            self.activaViewerSet.add('scanViewer')
            self.mainWindowUi.set_status_bar(self.lastScanPath)
            return 0
        else:
            return 1  
            
            
    def get_current_active_window(self):
        return self.mainWindowUi.get_current_active_window()
        
    def get_scan_path(self):
        return self.lastScanPath
        
    def get_time(self):
        lt=time.localtime()
        return str(lt.tm_yday)+':'+str(lt.tm_hour)+':'+str(lt.tm_min)+':'+str(lt.tm_sec)
    
    def get_progress_var_value(self):
        return self.mainWindowUi.get_progress_var_value()
        
    def get_layers(self):
        """
        Apply retinal layer segmentation and visualize it.
        """
        layers=self.oct.get_layers()
        probmapsExist=self.oct.probmaps_does_exist()
        
        if(probmapsExist):
            self.enable_probability_related_tools()
            self.compute_probability_maps()
            
        else:
            self.disable_probability_related_tools()
            
        self.currentLayerNumber=1
        npimg=layers[:,:,self.currentLayerNumber-1]
        self.mainWindowUi.show_viewer(npimg,'layerViewer',self.oct.numSlices,\
                                      self.oct.layerSegmenter.uncertaintyValues,\
                                      self.oct.layerSegmenter.entropyVals,\
                                      self.oct.layerSegmenter.probabilityVals)
        
        npimg=self.oct.get_scan()[:,:,self.currentLayerNumber-1]
        overlay=np.copy(npimg)
        self.mainWindowUi.add_overlay([overlay],'layerViewer',self.scanCoeff)
        self.activaViewerSet.add('layerViewer')
        if(probmapsExist):
            self.visualize_uncertainties()
            
    def get_hrf_bounding_boxes(self):
        return self.mainWindowUi.get_hrf_bounding_boxes()
        
    def get_enface_bounding_boxes(self):
        return self.mainWindowUi.get_enface_bounding_boxes() 
    
    def get_hrfs(self):
        """
        Read and visualized Hyperreflective foci segmentation maps.
        """
        hrfs,hrfStatus,hrfBBox=self.oct.get_hrfs()
        self.currentHRFNumber=1
        npimg=hrfs[:,:,self.currentHRFNumber-1]
        self.mainWindowUi.show_viewer(npimg,'hrfViewer',self.oct.numSlices)
        npimg=self.oct.get_scan()[:,:,self.currentHRFNumber-1]
        overlay=np.copy(npimg)
        self.mainWindowUi.add_overlay([overlay],'hrfViewer',self.scanCoeff)
        self.activaViewerSet.add('hrfViewer')
        self.mainWindowUi.set_hrf_status(hrfStatus)
        self.mainWindowUi.set_hrf_bbox(hrfBBox)
        self.slice_value_changed(self.currentHRFNumber,'hrfViewer',furtherUpdate=False)
        
    def get_gas(self):
        """
        Read and visualized GA segmentation maps.
        """
        gas=self.oct.get_gas()
        self.currentGANumber=1
        npimg=gas[:,:,self.currentGANumber-1]
        self.mainWindowUi.show_viewer(npimg,'gaViewer',self.oct.numSlices)
        npimg=self.oct.get_scan()[:,:,self.currentGANumber-1]
        overlay=np.copy(npimg)
        self.mainWindowUi.add_overlay([overlay],'gaViewer',self.scanCoeff)
        self.activaViewerSet.add('gaViewer')
        
    def get_drusen(self):
        self.currentDrusenNumber=1
        drusen=self.oct.get_drusen()
        npimg=drusen[:,:,self.currentDrusenNumber-1]
        self.mainWindowUi.show_viewer(npimg,'drusenViewer',self.oct.numSlices) 
        npimg=self.oct.get_scan()[:,:,self.currentDrusenNumber-1]
        overlay1=np.copy(npimg)
        npimg=self.oct.get_layers()[:,:,self.currentDrusenNumber-1]
        overlay2=np.copy(npimg)
        self.mainWindowUi.add_overlay([overlay1,overlay2],'drusenViewer',self.scanCoeff)
        self.activaViewerSet.add('drusenViewer')
    
    def get_enface(self):  
        """
        Compute the enface projection view and visualize it.
        """
        enface,enfaceBBox=self.oct.get_enface()
        self.mainWindowUi.show_viewer(enface,'enfaceViewer',self.oct.numSlices) 
        self.mainWindowUi.set_enface_bbox(enfaceBBox)
        self.activaViewerSet.add('enfaceViewer')
        self.slice_value_changed(self.currentDrusenNumber,'enfaceViewer',furtherUpdate=False,stop=False)
   
    def get_enface_drusen(self):
        """
        Compute the enface projection of drusen maps and visualize it.
        """
        enfaceDrusen=self.oct.get_enface_drusen()
        self.mainWindowUi.show_viewer(enfaceDrusen,'enfaceDrusenViewer',self.oct.numSlices) 
        enface,bbox=self.oct.get_enface()
        overlay=enface
        self.mainWindowUi.add_overlay([overlay],'enfaceDrusenViewer',self.enfaceCoeff)
        self.activaViewerSet.add('enfaceDrusenViewer')
        self.enfaceDrusenViewOpen=True
        self.slice_value_changed(self.currentDrusenNumber,'enfaceDrusenViewer',furtherUpdate=False,stop=False)
        
    def get_PED_volume(self):
        """
        ToDo
        """
        pass
        
    def get_rastered_line_points(self,x1,y1,x2,y2,h=100000,w=100000):
        """
        Raster a line starting from x1,y1 to x2,y2. h and w are the maximum 
        dimension of a given map and used to filter out invalid points.
        """
        l=list(bresenham(int(x1),int(y1),int(x2),int(y2)))
        valid=list()
        for i in range(len(l)):
            if(l[i][1]>=0 and l[i][1]<h and l[i][0]>=0 and l[i][0]<w):
                valid.append(l[i])
        return valid
        
    def get_edit_rpe(self):
        return self.editRPE
        
    def get_edit_bm(self):
        return self.editBM
        
    def get_manual_markers(self):
        return self.mainWindowUi.get_manual_markers()
     
    def get_network_info(self):
        return self.mainWindowUi.get_network_info()
     
    def get_uncertainties(self):
        return  self.mainWindowUi.get_uncertainties()
        
    def get_enface_height(self):
        en,bb=self.oct.get_enface()
        return en.shape[0]
        
    def get_RPE_location(self,segImg):
        """
        Compute the pixelwise location of RPE layer in segImg map.
        """
        y = []
        x = []
        tmp = np.copy(segImg)
        if( np.sum(segImg)==0.0):
            return y, x
        if( len(np.unique(tmp)) == 4 ):
            tmp2 = np.zeros(tmp.shape)
            tmp2[np.where(tmp==170)] = 255
            tmp2[np.where(tmp==255)] = 255
            y, x = np.where(tmp2==255)
          
        else:
            y, x = np.where(tmp==255)
        return y, x
    
    
    
    
    def closing(self,callerName):
        """
        If user closes a viewer window.
        """
        if(callerName=='scanViewer'):
            self.activaViewerSet-={'scanViewer'}
        elif(callerName=='layerViewer'):
            self.activaViewerSet-={'layerViewer'}
        elif(callerName=='drusenViewer'):
            self.activaViewerSet-={'drusenViewer'}
        elif(callerName=='enfaceViewer'):
            self.activaViewerSet-={'enfaceViewer'}            
        elif(callerName=='enfaceDrusenViewer'):
            self.enfaceDrusenViewOpen=False
            self.activaViewerSet-={'enfaceDrusenViewer'}
    
    def write_in_log(self,l):
        f=open(self.logFile,'a+')
        f.write(l)
        f.close()   
        
    def show_progress_bar(self,message="Loading"):
        self.mainWindowUi.show_progress_bar(message)
        
    def hide_progress_bar(self):
        self.mainWindowUi.hide_progress_bar()
        self.reset_value() 
        
    def set_progress_bar_value(self,value):
        self.mainWindowUi.set_progress_bar_value(value)
        
    def update_progress_bar_value(self,step):
        self.mainWindowUi.update_progress_using_step(step)
        
    def reset_value(self):
        self.mainWindowUi.reset_value()
    
    def enable_probability_related_tools(self):
        self.mainWindowUi.enable_probability_related_tools()
        
    def disable_probability_related_tools(self):
        self.mainWindowUi.disable_probability_related_tools()

    def is_there_unsaved_changes(self):
        return (self.drusenEditted or self.layerEditted or self.hrfEditted or self.gaEditted or self.enfaceEditted)
        
    def save(self):
        """
        Control save action from the user.
        """
        if(self.drusenEditted or self.enfaceDrusenEditted):
            self.oct.save_drusen(self.lastScanPath)
            self.drusenEditted=False
            self.enfaceDrusenEditted=False
            self.mainWindowUi.saved_changes()
        if(self.layerEditted):
            self.oct.save_layers(self.lastScanPath)
            self.layerEditted=False
            self.mainWindowUi.saved_changes()
        if(self.hrfEditted):
            self.oct.set_hrf_bounding_boxes(self.get_hrf_bounding_boxes())
            self.oct.save_hrfs(self.lastScanPath)
            self.hrfEditted=False
            self.mainWindowUi.saved_changes()
        if(self.gaEditted):
            self.oct.save_gas(self.lastScanPath)
            self.gaEditted=False
            self.mainWindowUi.saved_changes()
        if(self.enfaceEditted):
            self.oct.set_enface_bounding_boxes(self.get_enface_bounding_boxes())
            self.oct.save_enface(self.lastScanPath)
            self.enfaceEditted=False
            self.mainWindowUi.saved_changes()   
        
            
    def save_as(self):
        dirName=self.mainWindowUi.get_save_path(self.lastScanPath,'drusen',self.oct.saveFormat)
        self.lastScanPath=dirName
        if(self.drusenEditted or self.enfaceDrusenEditted):
            self.oct.set_scan_path(self.lastScanPath)
            self.oct.save_drusen(self.lastScanPath)
            self.drusenEditted=False
            self.enfaceDrusenEditted=False
            self.mainWindowUi.saved_changes()
            
        if(self.layerEditted):
            self.oct.set_scan_path(self.lastScanPath)
            self.oct.save_layers(self.lastScanPath)
            self.layerEditted=False
            self.mainWindowUi.saved_changes()
            
        if(self.hrfEditted):
            self.oct.set_hrf_bounding_boxes(self.get_hrf_bounding_boxes())
            self.oct.set_scan_path(self.lastScanPath)
            self.oct.save_hrfs(self.lastScanPath)
            self.hrfEditted=False
            self.mainWindowUi.saved_changes()
            
        if(self.gaEditted):
            self.oct.set_scan_path(self.lastScanPath)
            self.oct.save_gas(self.lastScanPath)
            self.gaEditted=False
            self.mainWindowUi.saved_changes()  
            
        if(self.enfaceEditted):
            self.oct.set_enface_bounding_boxes(self.get_enface_bounding_boxes())
            self.oct.set_scan_path(self.lastScanPath)
            self.oct.save_enface(self.lastScanPath)
            self.enfaceEditted=False
            self.mainWindowUi.saved_changes()  

    def image_changed(self,image,callerName):
        """
        Cascade changes further, if the segmentation map changes.
        """
        if(callerName=='scanViewer'):
            pass
        elif(callerName=='layerViewer'):
           
            if('drusenViewer' in self.activaViewerSet):
                self.slice_value_changed(self.currentDrusenNumber,'drusenViewer',furtherUpdate=False)
        elif(callerName=='drusenViewer'):
            self.oct.set_drusen_b_scan(image,self.currentDrusenNumber)
            if(self.enfaceDrusenViewOpen):
                self.slice_value_changed(self.currentDrusenNumber,'enfaceDrusenViewer',furtherUpdate=False)
        elif(callerName=='enfaceViewer'):
            pass            
        elif(callerName=='enfaceDrusenViewer'):
            pass
            
    def slice_value_changed(self,value,callerName,furtherUpdate=True,stop=False):
        """
        Update views, upon change of the slice. 
        value: New slice value
        callerName: The viewer in which slice is change
        furtherUpdate: Update other viewers accordingly
        stop: Avoid updating further related views
        """
        images=[]
        coeffs=[]
        if(callerName=='scanViewer'):
            self.currentScanNumber=value
            npimg=self.oct.get_scan()[:,:,self.currentScanNumber-1]
            images=[npimg]
            coeffs=[1.0]
            
        elif(callerName=='hrfViewer'):
            self.currentHRFNumber=value
            s=self.oct.get_scan()[:,:,self.currentHRFNumber-1]
            l=self.oct.get_hrfs()[0][:,:,self.currentHRFNumber-1]
            images=[s,l]
            coeffs=[self.scanCoeff,1.-self.scanCoeff]
            
        elif(callerName=='gaViewer'):
            self.currentGANumber=value
            s=self.oct.get_scan()[:,:,self.currentGANumber-1]
            l=self.oct.get_gas()[:,:,self.currentGANumber-1]
            images=[s,l]
            coeffs=[self.scanCoeff,1.-self.scanCoeff]
             
        elif(callerName=='layerViewer'):
            self.currentLayerNumber=value
            s=self.oct.get_scan()[:,:,self.currentLayerNumber-1]
            l=self.oct.get_layers()[:,:,self.currentLayerNumber-1]
            images=[s,l]
            coeffs=[self.scanCoeff,1.-self.scanCoeff]
            if((not stop) and 'drusenViewer' in self.activaViewerSet):
                self.slice_value_changed(value,'drusenViewer',furtherUpdate=False,stop=True)
                self.mainWindowUi.set_spinbox_value(value,'drusenViewer')
   
        elif(callerName=='drusenViewer'):
            
            self.currentDrusenNumber=value
            self.currentEnfaceDrusenNumber=value
            self.currentEnfaceNumber=value

            s=self.oct.get_scan()[:,:,self.currentDrusenNumber-1]
            l=self.oct.get_layers()[:,:,self.currentDrusenNumber-1]
            d=self.oct.get_drusen()[:,:,self.currentDrusenNumber-1]

            images=[s,l,d]
            coeffs=[self.scanCoeff,self.layerCoeff,(2.-(self.scanCoeff+self.layerCoeff))/2.]
            if((not stop) and 'enfaceDrusenViewer' in self.activaViewerSet):
                self.slice_value_changed(value,'enfaceDrusenViewer',furtherUpdate=False,stop=True)
                self.mainWindowUi.set_spinbox_value(value,'enfaceDrusenViewer')
                
        elif(callerName=='enfaceViewer'):
            self.currentDrusenNumber=value
            self.currentEnfaceDrusenNumber=value
            self.currentEnfaceNumber=value
            npimg,bbox=self.oct.get_enface()
            images=[npimg]
            coeffs=[1.0]
            if((not stop) and 'enfaceDrusenViewer' in self.activaViewerSet):
                self.slice_value_changed(value,'enfaceDrusenViewer',furtherUpdate=False,stop=True)
                self.mainWindowUi.set_spinbox_value(value,'enfaceDrusenViewer')
                
        elif(callerName=='enfaceDrusenViewer'):
            self.currentDrusenNumber=value
            self.currentEnfaceDrusenNumber=value
            self.currentEnfaceNumber=value
            e,bb=self.oct.get_enface()
            ed=self.oct.get_enface_drusen()
            
            if(not self.enfaceDrusenController is None):
                self.enfaceDrusenController.set_enface_drusen(ed)
            images=[e,ed]
            coeffs=[self.enfaceCoeff,1.-self.enfaceCoeff]
            if((not stop) and 'drusenViewer' in self.activaViewerSet):
                self.slice_value_changed(value,'drusenViewer',furtherUpdate=False,stop=True)
                self.mainWindowUi.set_spinbox_value(value,'drusenViewer')
            if((not stop) and 'enfaceViewer' in self.activaViewerSet):
                self.slice_value_changed(value,'enfaceViewer',furtherUpdate=False,stop=True)
                self.mainWindowUi.set_spinbox_value(value,'enfaceViewer')
        if(not stop):
            self.mainWindowUi.update_viewer(images,coeffs,callerName,value) 
            self.mainWindowUi.set_spinbox_value(value,callerName)
            
        if(furtherUpdate):
            self.update_linked_viewers(value)  
                
    def update_enface_status(self):
        self.mainWindowUi.content_changed('enfaceViewer')
      
    def update_HRF_status(self,index,status,updateCheckBox=False):
        """
        Change status of slice (index) to whether it contains HRF or not.
        """
        self.oct.set_HRF_status(index,status)
        self.mainWindowUi.content_changed('hrfViewer')
        if(updateCheckBox):
            self.mainWindowUi.set_hrf_check_box(status)
        
    def update_linked_viewers(self,value):
        """
        If viewers are linked, when one changes, update other linked ones 
        accordingly to show similar slice.
        """
        if(self.linkViewers):
            for viewName in self.activaViewerSet:
                self.slice_value_changed(value,viewName,furtherUpdate=False)
                self.mainWindowUi.set_spinbox_value(value,viewName)
                
    def update_ga_mask_in_region(self,image,x1,x2,color):
        """
        Update GA segmentation map in a selection region starting from x1
        to x2.
        """
        h,w=image.shape
        tmp=np.copy(image)
        s=max(0,min(x1,x2))
        e=min(w-1,max(x1,x2))
        
        image[:,s:e+1]=color[0]
        xs,ys=np.where(tmp!=image)
        self.oct.set_ga(s,e,color[0],self.currentGANumber)
        self.slice_value_changed(self.currentGANumber,callerName='gaViewer',furtherUpdate=False)
        self.mainWindowUi.content_changed('gaViewer')
        return image,xs,ys
        
    def update_cost_image_redo(self,x,y,smoothness,layerName,sliceNum,callerName):
        """
        When CSP tool is used (x,y are the location of the selected point),
        update the cost map for either RPE or BM. Trigered by making the action
        or pressing the redo button.
        """
        info=dict()
        if(layerName=='RPE'):
            info=self.oct.update_cost_rpe(x,y,sliceNum-1,smoothness)
            self.mainWindowUi.content_changed('layerViewer')
        elif(layerName=='BM'):
            info=self.oct.update_cost_bm(x,y,sliceNum-1,smoothness)
            self.mainWindowUi.content_changed('layerViewer')
        return info
    
    def update_cost_image_undo(self,layerName,sliceNum,info,callerName):
        """
        The reverese action of updating cost images is applied when the undo 
        button is pressed.
        """
        if(layerName=='RPE'):
            self.oct.update_cost_rpe_using_info(info,sliceNum-1) 
        elif(layerName=='BM'):
            self.oct.update_cost_bm_using_info(info,sliceNum-1)
        self.slice_value_changed(sliceNum,'layerViewer',furtherUpdate=False)
        
    def update_cost_image(self,j,i,smoothness,callerName):
        """
        When user applies the CSP tool, create a undo/redo-able command.
        """
        # Get current state to store for redo
        if(self.editRPE):
            currLayer='RPE'
        elif(self.editBM):
            currLayer='BM'
        sliceNum=self.currentLayerNumber
        self.mainWindowUi.draw_cost_point_command(i,j,smoothness,currLayer,callerName,sliceNum)
        
    def update_tool_box(self):
        self.mainWindowUi.update_tool_box()
    
    def update_distance(self,sliceNumN):
        oldOveralDistance,oldDistances=self.oct.get_distances()
        overallDist,dist=self.oct.update_distance(sliceNumN)
                
    def set_link_viewers(self,linkState):
        self.linkViewers=linkState
        
    def set_drusen_slice_number(self,sliceNum):
        """
        Set the slice number for the three related viewers.
        """
        self.currentDrusenNumber=sliceNum
        self.currentEnfaceNumber=sliceNum
        self.currentEnfaceDrusenNumber=sliceNum
    
    def set_slice_number(self,sliceNum,viewerName):
        """
        Set the slice number for the given viewer name.
        """
        if(viewerName=='layerViewer'):    
            self.currentLayerNumber=sliceNum
        elif(viewerName=='hrfViewer'):    
            self.currentHRFNumber=sliceNum
        elif(viewerName=='gaViewer'):    
            self.currentGANumber=sliceNum
        elif(viewerName=='drusenViewer'):
            self.currentDrusenNumber=sliceNum
            self.currentEnfaceNumber=sliceNum
            self.currentEnfaceDrusenNumber=sliceNum
        elif(viewerName=='enfaceDrusenViewer'):
            self.currentDrusenNumber=sliceNum
            self.currentEnfaceNumber=sliceNum
            self.currentEnfaceDrusenNumber=sliceNum
        elif(viewerName=='enfaceViewer'):
            self.currentDrusenNumber=sliceNum
            self.currentEnfaceNumber=sliceNum
            self.currentEnfaceDrusenNumber=sliceNum
     
    def unset_editing_layer(self):
        self.editBM=False
        self.editRPE=False
               
    def set_editing_layer(self,index):
        if(index==0):
            self.editRPE=True
        elif(index==1):
            self.editBM=True
        
    def set_up_manual_marker_selection(self):
        self.mainWindowUi.set_up_manual_marker_selection()
        
    def set_merge_drusen(self):
        self.mainWindowUi.set_merge_drusen() 
        
    def unset_merge_drusen(self):
        self.mainWindowUi.unset_merge_drusen()
    
    def set_druse_info(self,height,volume,brightness):
        self.mainWindowUi.set_druse_info(height,volume,brightness)
        
    def set_uncertainties(self,uncertainties,sliceNumZ):
        self.mainWindowUi.set_uncertainties(uncertainties,sliceNumZ)
          
 
    def slider_value_changed(self,value,callerName,edittingIndex):
        """
        When the opecity of the images changed through the change of the value 
        of the slider.
        """
        if(callerName=='scan'):
            self.scanCoeff=value/99.
        elif(callerName=='layer'):
            self.layerCoeff=value/99.
        elif(callerName=='enface'):
            self.enfaceCoeff=value/99.
        
        if(edittingIndex==0 or edittingIndex==1):
            self.slice_value_changed(self.currentLayerNumber,callerName='layerViewer')
        elif(edittingIndex==2):
            self.slice_value_changed(self.currentDrusenNumber,callerName='drusenViewer')
        elif(edittingIndex==3):
            self.slice_value_changed(self.currentEnfaceDrusenNumber,callerName='enfaceDrusenViewer')
        elif(edittingIndex==4):
            self.slice_value_changed(self.currentHRFNumber,callerName='hrfViewer')           
        elif(edittingIndex==5):
            self.slice_value_changed(self.currentGANumber,callerName='gaViewer')
           
    def compute_overlayed_images(self,images,coeffs): 
        """
        Combine images with respect to different coefficients (opacities) they 
        have.s
        """
        res=np.copy(images[0])
        res.fill(0)
        for i in range(len(images)):
            res=res+images[i]*coeffs[i]
        return res
        
    def delete_drusen_in_region(self,image,topLeftX,topLeftY,bottomRightX,\
                                    bottomRightY,callerName='',undoRedo=False):
        """
        Delete drusen in selected regions by setting them to 0 in the drusen
        segmentation map.
        """
        tmp=np.copy(image[topLeftY:bottomRightY,topLeftX:bottomRightX])
        image[topLeftY:bottomRightY,topLeftX:bottomRightX]=0.
        xs,ys=np.where(image[topLeftY:bottomRightY,topLeftX:bottomRightX]!=tmp)
        xs=xs+topLeftY
        ys=ys+topLeftX
        zs=[]
        if(callerName=='enfaceDrusenViewer'):
            xs,ys,zs=self.oct.delete_drusen_in_region(topLeftY,bottomRightY,\
                                                      topLeftX,bottomRightX)
            zs=zs+topLeftY
            ys=ys+topLeftX
            self.slice_value_changed(self.currentDrusenNumber,\
                                callerName='drusenViewer',furtherUpdate=False)
        self.mainWindowUi.content_changed(callerName)
        if(not undoRedo):
            if(len(xs)>0 and len(ys)>0):
                if(callerName=='hrfViewer'):
                    self.mainWindowUi.draw_delete_command(xs,ys,zs,[0,0,0],callerName,self.currentHRFNumber)
                else:
                    self.mainWindowUi.draw_delete_command(xs,ys,zs,[0,0,0],callerName,self.currentDrusenNumber)
        return image
        
    def box_command(self,rect,sliceNum,callerName):
        """
        Create a new command for drawing bounding boxes.
        """
        self.mainWindowUi.draw_box_command(rect,sliceNum,callerName)
        
    def removed_box_command(self,removedBoxes,sliceNum,callerName):
        self.mainWindowUi.remove_box_command(removedBoxes,sliceNum,callerName)
        
    def extract_drusen_in_region(self,image,overImg,topLeftX,topLeftY,bottomRightX,\
                                 bottomRightY,callerName='',maxFilteringHeight=0,\
                                 undoRedo=False):  
        """
        Automatically extract drusen in the selected region either direction on
        drusen segmentation maps or the enface drusen projection map.
        Also segments out the Hyperreflective foci in a selected region by 
        applying Otsu thresholding in the given region.
        """
        if(topLeftX-bottomRightX==0 or topLeftY-bottomRightY==0):
            return image
        if(callerName=='hrfViewer'):
            
            zs=[]
            reg=overImg[topLeftY:bottomRightY,topLeftX:bottomRightX]
            tmp=np.copy(image[topLeftY:bottomRightY,topLeftX:bottomRightX])
     
#           Otsu
            if(len(np.unique(reg))>0):
                t=threshold_otsu(reg)
                reg=(reg>t).astype(int)*255
            else:
                reg.fill(0)
            
            image[topLeftY:bottomRightY,topLeftX:bottomRightX]=reg
            self.mainWindowUi.content_changed('hrfViewer')
            dd=image[topLeftY:bottomRightY,topLeftX:bottomRightX]
            xs,ys=np.where(dd!=tmp)
            xs=xs+topLeftY
            ys=ys+topLeftX
            zns=[]
            xns=[]
            yns=[]
            if(not undoRedo):
                if((len(xs)>0 and len(ys)>0)or(len(xns)>0 and len(yns)>0)):
                    self.mainWindowUi.draw_extract_command(xs,ys,zs,xns,yns,\
                            zns,[255,255,255],callerName,self.currentHRFNumber)
            return image
       
        if(callerName=='enfaceDrusenViewer'):
            drusen=self.oct.get_drusen()
            layers=self.oct.get_layers()
            h,w=drusen[:,:,0].shape
            s=topLeftY
            e=bottomRightY
            tmp=np.copy(drusen[:,topLeftX:bottomRightX,topLeftY:bottomRightY])
            while(s<e):
                drusen[:,:,s]=self.extract_drusen_in_region(drusen[:,:,s],\
                       np.copy(layers[:,:,s]),topLeftX,0,bottomRightX,h-1,\
                       callerName='fromEnfaceDrusen',maxFilteringHeight=\
                       maxFilteringHeight,undoRedo=True)

                s+=1
            self.oct.set_drusen(drusen)
            dd=drusen[:,topLeftX:bottomRightX,topLeftY:bottomRightY]
            xs,ys,zs=np.where(dd-tmp>0)
            zs=zs+topLeftY
            ys=ys+topLeftX
            
            xns,yns,zns=np.where(tmp-dd>0)
            zns=zns+topLeftY
            yns=yns+topLeftX
            if(not undoRedo):
                if((len(xs)>0 and len(ys)>0) or (len(xns)>0 and len(yns)>0)):

                    self.mainWindowUi.draw_extract_command(xs,ys,zs,xns,yns,\
                           zns,[255,0,255],callerName,self.currentDrusenNumber)

            self.mainWindowUi.content_changed(callerName)  
            self.slice_value_changed(self.currentDrusenNumber,\
                                 callerName='drusenViewer',furtherUpdate=False)

            return self.oct.get_enface_drusen()
        zs=[]
        reg=image[topLeftY:bottomRightY,topLeftX:bottomRightX]
        tmp=np.copy(reg)
        layerReg=np.copy(overImg[topLeftY:bottomRightY,topLeftX:bottomRightX])
        y,x=self.get_RPE_location(layerReg)
        druReg=np.copy(layerReg)
        layerReg.fill(0.)
        layerReg[y,x]=1.
        try:
            if(len(y)>0):
                for i in range(len(y)):                
                    druReg[y[i]:,x[i]]=1
                v=np.sum(druReg,axis=0)
                minXs=self.find_argrel_minima(v)
                if(len(minXs[0])==1):
                    minX=minXs[0][0]
                    minY=np.where(layerReg[:,minX]==1)
                    if(len(minY)>0):
                        for i in range(len(y)):
                            reg[y[i]:minY+1,x[i]]=255
                elif(len(minXs[0])>1):
                    sX=min(minXs[0])
                    eX=max(minXs[0])
                    sY=np.where(layerReg[:,sX]==1)[0][0]
                    eY=np.where(layerReg[:,eX]==1)[0][0]
                    bottomLine=list(bresenham(int(sX),int(sY),int(eX),int(eY)))
                    for i in range(len(bottomLine)):
                        bx,by=bottomLine[i]
                        ry=np.where(layerReg[:,bx]==1)[0][0]
                        reg[ry:by+1,bx]=255
        except:
            print "Error in extract_drusen_in_region"
        if(callerName=='fromEnfaceDrusen'):
            tmpImg=np.zeros((reg.shape[0],reg.shape[1]))
            tmpImg=np.copy(reg)
            reg=self.filter_drusen_wrt_height(tmpImg,0,maxFilteringHeight,\
                            0,0,reg.shape[1],reg.shape[0],callerName='drusenViewer',\
                            undoRedo=True)
            image[topLeftY:bottomRightY,topLeftX:bottomRightX]=reg
        else:
            tmpImg=np.zeros((reg.shape[0],reg.shape[1]))
            tmpImg=np.copy(reg)
            reg=self.filter_drusen_wrt_height(tmpImg,0,maxFilteringHeight,\
                            0,0,reg.shape[1],reg.shape[0],callerName='drusenViewer',\
                            undoRedo=True)
            image[topLeftY:bottomRightY,topLeftX:bottomRightX]=reg
        self.mainWindowUi.content_changed('drusenViewer')
        dd=image[topLeftY:bottomRightY,topLeftX:bottomRightX]
        xs,ys=np.where(dd-tmp>0)
        xs=xs+topLeftY
        ys=ys+topLeftX
        zns=[]
        xns,yns=np.where(tmp-dd>0)
        xns=xns+topLeftY
        yns=yns+topLeftX
        if(not undoRedo):
                if((len(xs)>0 and len(ys)>0)or(len(xns)>0 and len(yns)>0)):
                    self.mainWindowUi.draw_extract_command(xs,ys,zs,xns,yns,zns,[255,0,255],callerName,self.currentDrusenNumber)
        return image
        
    def draw_point(self,image,x,y,color,sliceNum,callerName='',undoRedo=False):
        """
        Draw a point on given viewer when the pen tool is selected.
        """
        prevValues=[]
        redoValues=[]
        oldValue=image[int(y),int(x)]
        if(callerName=='layerViewer'):
            i=int(x)
            j=int(y)
            x=[]
            y=[]
            rpeImg,bmImg=self.oct.decompose_into_RPE_BM_images(image)
            if(self.editRPE):
                # Delete everything in the column
                # Previous RPE loc
                if(color[0]>0):
                    j0=np.where(rpeImg[:,i]>0)    
                    for jj in j0[0]:
                        y.append(jj)
                        x.append(i)
                        prevValues.append(color[0])
                        redoValues.append(0)
                        rpeImg[jj,i]=0
                rpeImg[j,i]=color[0]
                
            elif(self.editBM):
                # Delete everything in the column
                if(color[0]>0):
                    j0=np.where(bmImg[:,i]>0)       
                    for jj in j0[0]:
                        y.append(jj)
                        x.append(i)
                        if(rpeImg[jj,i]==0):
                            prevValues.append(127)
                        else:
                            prevValues.append(170)
                        redoValues.append(0)
                        bmImg[jj,i]=0
                bmImg[j,i]=color[0]

            image=self.oct.combine_RPE_BM_images(rpeImg,bmImg)
            
            color=[image[j,i],image[j,i],image[j,i],255]
            
            prevValues.append(oldValue)
            redoValues.append(image[j,i])
            y.append(j)
            x.append(i)
       
        elif(callerName=='enfaceDrusenViewer'):
            if(color[0]==0):
                image[int(y),int(x)]=color[0]
                prevValues=self.oct.remove_druse_at([y],[x])
                self.slice_value_changed(sliceNum,callerName='drusenViewer',\
                    furtherUpdate=False)
        else:
            image[int(y),int(x)]=color[0]
        self.mainWindowUi.content_changed(callerName)
        if(not undoRedo):
            layerName=''
            if(self.editBM):
                layerName='BM'
            elif(self.editRPE):
                layerName='RPE'
            if(type(x)==list):
               
                if(oldValue!=image[int(y[-1]),int(x[-1])]):
                    self.mainWindowUi.draw_pen_command(x,y,color,callerName,\
                     sliceNum,prevValues,[y],[x],oldValue,redoValues,layerName)

            else:
                if(oldValue!=image[int(y),int(x)]):
                    self.mainWindowUi.draw_pen_command(x,y,color,callerName,\
                     sliceNum,prevValues,[y],[x],oldValue,redoValues,layerName)

        return image
    
    def visualize_uncertainties(self):
        """
        When uncertainty visualization is trigerred, use this function to set
        the views.
        """
        ent,prob=self.oct.get_uncertainties_per_bscan()
        self.mainWindowUi.set_uncertainties_per_bscan(ent,prob)
        
    def compute_probability_maps(self):
        """
        Compute the probability maps from the deep net. Compute uncertainties.
        """
        self.oct.compute_prob_maps()
        self.oct.compute_uncertainties()
        
    def apply_threshold_immediately(self):
        """
        Drusen height thresholding all over the segmentation map.
        """
        self.mainWindowUi.apply_threshold_immediately()
    
    def apply_split_redo(self):
        """
        Split the large druse into smaller ones.
        """
        info=dict()
        separators=self.mainWindowUi.get_drusen_separators()
        drusen=self.oct.get_drusen()
        y,x=np.where(separators==1.)
        info['locY']=y
        info['locX']=x
        info['values']=np.copy(drusen[:,x,y])
        info['enfaceController']=self.enfaceDrusenController.get_data()
        self.enfaceDrusenController.apply_separator(separators)
        self.done_spliting()
        self.mainWindowUi.content_changed('drusenViewer')
        return info                   
    
    def apply_split_undo(self,info):
        """
        Undo the druse spliting action.
        """
        drusen=self.oct.get_drusen()
        drusen[:,info['locX'],info['locY']]=info['values']
        self.oct.set_drusen(drusen)
        
        self.enfaceDrusenController.set_data(info['enfaceController'])
        self.slice_value_changed(self.currentEnfaceDrusenNumber,\
                                 'enfaceDrusenViewer',furtherUpdate=False)
        self.slice_value_changed(self.currentDrusenNumber,'drusenViewer',\
                                 furtherUpdate=False)
        
    def apply_split(self):   
        """
        Create the spliting command (to be used for unde/redo).
        """
        self.mainWindowUi.apply_split_command()

    def done_spliting(self):
        """
        After spliting the druse make some actions, mark slice to be as changed.
        """
        self.mainWindowUi.done_splitting()
        self.slice_value_changed(self.currentDrusenNumber,\
         callerName='enfaceDrusenViewer',furtherUpdate=False)
        
    def change_drusen_visiting_order(self,orderMethod):
        """
        Change the order of druse visiting. orderMethod selected the order to
        visit the drusen, i.e., based on their volume, brightness or size.
        """
        if(not self.enfaceDrusenController is None):        
            self.enfaceDrusenController.set_sort_method(orderMethod)
            self.enfaceDrusenController.update_sorting_method()
            
    def show_CCA_enface(self):
        """
        Perform connected component analysis on drusen in the enface projector,
        colorize the druse wrt being checked or not.
        """
        if(self.enfaceDrusenController is None):
            if(not self.oct.drusen is None):
                self.enfaceDrusenController=edc.EnfaceDrusenController(\
                          self.oct.get_drusen(),self.oct.get_enface()[0],self)
                mask=self.enfaceDrusenController.get_mask()
                self.mainWindowUi.set_cca_mask(mask,self.currentDrusenNumber)
        else:
            if(not self.oct.drusen is None):
                mask=self.enfaceDrusenController.get_mask()
                self.mainWindowUi.set_cca_mask(mask,self.currentDrusenNumber)
                
    def hide_CCA_enface(self):
        """
        Make the coloring based on CCA inactive.
        """
        self.mainWindowUi.unset_cca_mask()
        
    def check_component(self):
        """
        When CCA is activated, change the color from yellow (current) to 
        green (checked).
        """
        if(not self.enfaceDrusenController is None):
            self.enfaceDrusenController.check_current_drusen()
            mask=self.enfaceDrusenController.get_mask()
            self.mainWindowUi.set_cca_mask(mask,self.currentDrusenNumber)
            slc,pst=self.enfaceDrusenController.get_current_position()
            self.grap_position_changed(pst,slc,callerName='enfaceDrusenViewer')
            
    def uncheck_component(self):
        """
        When CCA is activated, change the color from yellow (current) to 
        red (unchecked).
        """
        if(not self.enfaceDrusenController is None):
            self.enfaceDrusenController.uncheck_current_drusen()
            mask=self.enfaceDrusenController.get_mask()
            self.mainWindowUi.set_cca_mask(mask,self.currentDrusenNumber)
            slc,pst=self.enfaceDrusenController.get_current_position()
            self.grap_position_changed(pst,slc,callerName='enfaceDrusenViewer')
            
    def next_component(self):
        """
        Activate next druse based on the order.
        """
        if(not self.enfaceDrusenController is None):
            self.enfaceDrusenController.next_drusen_id()
            mask=self.enfaceDrusenController.get_mask()
            self.mainWindowUi.set_cca_mask(mask,self.currentDrusenNumber)
            slc,pst=self.enfaceDrusenController.get_current_position()
            self.grap_position_changed(pst,slc,callerName='enfaceDrusenViewer')
            
    def prev_component(self):
        """
        Activate the previous druse based on the visiting order.
        """
        if(not self.enfaceDrusenController is None):
            self.enfaceDrusenController.previous_drusen_id()
            mask=self.enfaceDrusenController.get_mask()
            self.mainWindowUi.set_cca_mask(mask,self.currentDrusenNumber)
            slc,pst=self.enfaceDrusenController.get_current_position()
            self.grap_position_changed(pst,slc,callerName='enfaceDrusenViewer')
            
    def draw_line(self,image,xx1,yy1,xx2,yy2,color,callerName='',undoRedo=False,\
                  movingMouse=False):    
        """
        Draw line between two given points xx1,yy1 and xx2,yy2 in different 
        viewers. For the GA viewer, colorize the whole selected region from
        xx1 to xx2.
        """
        h,w=image.shape
        x1=xx1
        x2=xx2
        y1=yy1
        y2=yy2
        points=self.get_rastered_line_points(x1,y1,x2,y2,h,w)
        s=[]
        y=[]
        posX=[]
        prevValues=[]
        redoValues=[]
        if(callerName=='gaViewer'):
            x1=max(0,min(xx1,xx2))
            x2=min(w-1,max(xx1,xx2))
            y1=max(0,min(yy1,yy2))
            y2=min(h-1,max(yy1,yy2))
            newImg,xs,ys= self.update_ga_mask_in_region(image,x1,x2,color)
            if(not undoRedo):
                if(len(xs)>0 and len(ys)>0):
                    if(callerName=='gaViewer'):
                        self.mainWindowUi.draw_region_command(xs,ys,color,\
                           callerName,self.currentGANumber)
            
        if(callerName=='layerViewer'):
            rpeImg,bmImg=self.oct.decompose_into_RPE_BM_images(image)
            currentDrawingColor={}
            if(self.editBM):
                currentDrawingColor={127,170}
                
            elif(self.editRPE):
                currentDrawingColor={170,255}
            
            if(color[0]==0):
                currentDrawingColor={0}

        for i in range(len(points)):
            
            if(callerName=='layerViewer'):
                if((points[i][1]<h and points[i][1]>=0 and points[i][0]<w and\
                      points[i][0]>=0 ) and image[points[i][1],points[i][0]] not\
                      in currentDrawingColor):
                    prevValues.append(image[points[i][1],points[i][0]])
                    
                    if(self.editRPE):
                        rpeImg[points[i][1],points[i][0]]=color[0]
                    elif(self.editBM):
                        bmImg[points[i][1],points[i][0]]=color[0]
                    
                    s.append(points[i][1])
                    y.append(points[i][0])
                if(color[0]!=0):#Only for drawing RPE and BM (not deletion)
                    self.seenPoints.add(str(points[i][1])+','+str(points[i][0]))
                
            elif(callerName=='enfaceDrusenViewer'):
                if(color[0]==0): # Delete
                    if(image[points[i][1],points[i][0]]!=color[0]):
                        image[points[i][1],points[i][0]]=color[0]
                        s.append(points[i][1])
                        y.append(points[i][0])
                else:
                    pass # Do nothing
            else:
                if(image[points[i][1],points[i][0]]!=color[0]):
                    image[points[i][1],points[i][0]]=color[0]
                    s.append(points[i][1])
                    y.append(points[i][0])
        if(callerName=='layerViewer'):
            rv=[]
            for i in range(len(points)):
                if(color[0]==0): #Skip this for deletion
                    break
                if(self.editRPE):
                    j0=np.where(rpeImg[:,points[i][0]]>0)
                    for jj in j0[0]:
                        key=str(jj)+','+str(points[i][0])
                        if(not key in self.seenPoints):
                            s.append(jj)
                            y.append(points[i][0])
                            if(self.editRPE):
                                if(bmImg[jj,points[i][0]]>0):
                                    prevValues.append(170)
                                    rv.append(127)
                                else:
                                    prevValues.append(255)
                                    rv.append(0)
                                rpeImg[jj,points[i][0]]=0
                elif(self.editBM):
                    j0=np.where(bmImg[:,points[i][0]]>0)
                    for jj in j0[0]:
                        key=str(jj)+','+str(points[i][0])
                        if(not key in self.seenPoints):
                            s.append(jj)
                            y.append(points[i][0])
                            if(self.editBM):
                                if(rpeImg[jj,points[i][0]]>0):
                                    prevValues.append(170)
                                    rv.append(255)
                                else:
                                    prevValues.append(127)
                                    rv.append(0)
                                bmImg[jj,points[i][0]]=0
            image=self.oct.combine_RPE_BM_images(rpeImg,bmImg)
            redoValues=list(image[s,y])
            redoValues.extend(rv)            
                        
        if(callerName=='enfaceDrusenViewer' and color[0]==0):
            posX=self.oct.remove_druse_at(s,y)
            self.slice_value_changed(self.currentDrusenNumber,\
                callerName='drusenViewer',furtherUpdate=False)
        self.mainWindowUi.content_changed(callerName)
        if(not movingMouse):
            self.seenPoints=set()
        if(undoRedo):
            if(len(s)>0):
                self.lineS.append(s)
                self.lineY.append(y)
                self.lineX.append(posX)
                self.linePrevValues.append(prevValues)
                self.lineRedoValues.append(redoValues)
            
        if(not undoRedo):
            if(len(s)>0 and len(y)>0):
                if(callerName=='enfaceDrusenViewer' or callerName=='drusenViewer'):
                    self.mainWindowUi.draw_line_command(x1,y1,x2,y2,color,\
                             callerName,self.currentDrusenNumber,posX,y,s,\
                             prevValues,redoValues)
                elif(callerName=='hrfViewer'):
                    self.mainWindowUi.draw_line_command(x1,y1,x2,y2,color,\
                             callerName,self.currentHRFNumber,posX,y,s,\
                             prevValues,redoValues)
                elif(callerName=='layerViewer'):
                    self.mainWindowUi.draw_line_command(x1,y1,x2,y2,color,\
                             callerName,self.currentLayerNumber,posX,y,s,\
                             prevValues,redoValues)
        return image
        
    def finished_drawing_with_pen(self,color,callerName=''):
        """
        When drawing with pen tool, when the user released the click button, 
        create draw curve commands.
        """
        s=self.lineS
        y=self.lineY
        x=self.lineX
        prevValues=self.linePrevValues
        redoValues=self.lineRedoValues
        if(len(y)>0):
            if(callerName=='enfaceDrusenViewer' or callerName=='drusenViewer'):
                self.mainWindowUi.draw_curve_command(x,y,s,color,callerName,\
                                self.currentDrusenNumber,prevValues,redoValues)
            elif(callerName=='hrfViewer'):
                self.mainWindowUi.draw_curve_command(x,y,s,color,callerName,\
                                   self.currentHRFNumber,prevValues,redoValues)
            elif(callerName=='layerViewer'):
                self.mainWindowUi.draw_curve_command(x,y,s,color,callerName,\
                                 self.currentLayerNumber,prevValues,redoValues)
        self.lineS=[]
        self.lineY=[]
        self.lineX=[]
        self.linePrevValues=[]
        self.lineRedoValues=[]
        self.seenPoints=set()  
        
    def find_argrel_minima(self,a):
        return np.where((np.r_[True,a[1:]<=a[:-1]] & np.r_[a[:-1]<=a[1:],True])==True)
        
    def filter_drusen_wrt_height(self,image,filteringHeight,maxFilteringHeight,\
           topLeftX,topLeftY,bottomRightX,bottomRightY,callerName='',undoRedo=False):
        """
        Filter out those drusen with an overall height, less than maxFilteringHeight
        or columns with a height less than filtering height.
        """
        if(callerName=='enfaceDrusenViewer'):
            drusen=self.oct.get_drusen()
            
            h,w=drusen[:,:,0].shape
            
            dReg=drusen[:,topLeftX:bottomRightX,topLeftY:bottomRightY]
            tmp=np.copy(dReg)
            # First filter druse with filteringHeight
            heightProjection=np.sum((dReg>0).astype(int),axis=0)
            dReg[:,heightProjection<=filteringHeight]=0.          

            # Filter drusen with maxFilteringHeight
            dReg=self.oct.filter_druse_by_max_height(dReg,maxFilteringHeight)
            xs,ys,zs=np.where(dReg!=tmp)
            zs=zs+topLeftY
            ys=ys+topLeftX
            self.mainWindowUi.content_changed(callerName)
            self.oct.set_drusen(drusen)
            self.slice_value_changed(self.currentDrusenNumber,\
                callerName='drusenViewer',furtherUpdate=False)
            
            if(not undoRedo):
                if(len(xs)>0 and len(ys)>0):
                    self.mainWindowUi.draw_filter_command(xs,ys,zs,[0,0,0],\
                        callerName,self.currentDrusenNumber)
                
            return self.oct.get_enface_drusen()
            
        else:
            zs=[]
            img=image[topLeftY:bottomRightY,topLeftX:bottomRightX]
            tmp=np.copy(img)
            # First filter druse with filteringHeight
            heightProjection=np.sum((img>0).astype(int),axis=0)
            img[:,heightProjection<=filteringHeight]=0.
            
            # Filter druse with maxFilteringHeight
            img=self.oct.filter_druse_by_max_height(img,maxFilteringHeight)
            xs,ys=np.where(img!=tmp)
            xs=xs+topLeftY
            ys=ys+topLeftX
            image[topLeftY:bottomRightY,topLeftX:bottomRightX]=np.copy(img)
            self.mainWindowUi.content_changed(callerName)
            if(not undoRedo):
                if(len(xs)>0 and len(ys)>0):
                    self.mainWindowUi.draw_filter_command(xs,ys,zs,[0,0,0],\
                                           callerName,self.currentDrusenNumber)
            return image
            
    def fill_in_area(self,image,overImg,x,y,color,callerName='',undoRedo=False):
        """
        Fill in the area at the selected x,y point. Continue filling up until the
        RPE layer. Filling also possible on the enface drusen and also for the
        HRF viewer.
        """
        tmp=np.copy(image)
        rpeIndicator=np.cumsum(overImg,axis=0)
        if(callerName=='enfaceDrusenViewer' and color[0]!=0):
            pass # Do nothing
        else:
            # The x,y position must be swaped because screen and pixmap x,y is
            # different than numpy x,y
            x,y=y,x
            h,w=image.shape[0],image.shape[1] 
            vxy=image[x,y]
            seen=set()
            toPaint=set()
            xs=[]
            ys=[]
            posX=[]
            # Check if we have reached RPE layer
            # Check if this point is over RPE layer, then stop there
            layerV=overImg[min(x+1,h-1),y] 
           
            if(vxy!=color[0] and not self.oct.is_rpe(layerV)):
                toPaint.add((x,y))
            l=len(toPaint)
            while(l>0):
                x,y=toPaint.pop()
                if((x,y) in seen):
                    continue
                if(image[x,y]!=color[0] and not self.oct.is_above_rpe_and_white(\
                                                     rpeIndicator,x,y,color[0])):
                    xs.append(x)
                    ys.append(y)
                    image[x,y]=color[0]
                seen.add((x,y))            
                top=(max(0,x-1),y)
                bottom=(min(h-1,x+1),y)
                right=(x,min(w-1,y+1))
                left=(x,max(0,y-1))
                if(callerName=='enfaceDrusenViewer'):
                    if(not top in seen and\
                        (image[top[0],top[1]]!=color[0]) ):
                        toPaint.add(top)
                    if(not bottom in seen and\
                        (image[bottom[0],bottom[1]]!=color[0])):
                        toPaint.add(bottom)
                    if(not right in seen and\
                        (image[right[0],right[1]]!=color[0])):
                        toPaint.add(right)
                    if(not left in seen and\
                        (image[left[0],left[1]]!=color[0])):
                        toPaint.add(left)
                elif(callerName=='drusenViewer'):
                    if(not top in seen and\
                        (image[top[0],top[1]]!=color[0]) and\
                            not self.oct.is_above_rpe_and_white(rpeIndicator,\
                            top[0],top[1],color[0])):
                        toPaint.add(top)
                    if(not bottom in seen and\
                        (image[bottom[0],bottom[1]]!=color[0]) and\
                            not self.oct.is_above_rpe_and_white(rpeIndicator,\
                                bottom[0],bottom[1],color[0])):
                        toPaint.add(bottom)
                    if(not right in seen and\
                        (image[right[0],right[1]]!=color[0]) and\
                            not self.oct.is_above_rpe_and_white(rpeIndicator,\
                                right[0],right[1],color[0])):
                        toPaint.add(right)
                    if(not left in seen and\
                        (image[left[0],left[1]]!=color[0]) and\
                            not self.oct.is_above_rpe_and_white(rpeIndicator,\
                                left[0],left[1],color[0])):
                        toPaint.add(left)
                elif(callerName=='hrfViewer'):
                    if(not top in seen and\
                        (image[top[0],top[1]]!=color[0])):
                        toPaint.add(top)
                    if(not bottom in seen and\
                        (image[bottom[0],bottom[1]]!=color[0])):
                        toPaint.add(bottom)
                    if(not right in seen and\
                        (image[right[0],right[1]]!=color[0])):
                        toPaint.add(right)
                    if(not left in seen and\
                        (image[left[0],left[1]]!=color[0])):
                        toPaint.add(left)
                l=len(toPaint)
            if(callerName=='enfaceDrusenViewer'):
                # Update all B-scans affected by this change
                xs,ys=np.where(image!=tmp)
                posX=self.remove_druse_at(xs,ys) 
                self.slice_value_changed(self.currentDrusenNumber,\
                    callerName='drusenViewer',furtherUpdate=False)               
            elif(callerName=='hrfViewer'):
                self.slice_value_changed(self.currentHRFNumber,\
                    callerName='hrfViewer',furtherUpdate=False)               
            self.mainWindowUi.content_changed(callerName)
            if(not undoRedo):
                if(len(xs)>0 and len(ys)>0):
                    if(callerName=='hrfViewer'):
                        self.mainWindowUi.draw_fill_command(xs,ys,color,\
                            callerName,self.currentHRFNumber,posX)
                    else:
                        self.mainWindowUi.draw_fill_command(xs,ys,color,\
                            callerName,self.currentDrusenNumber,posX)
        return image
        
    def dilate_in_region(self,image,topLeftX,topLeftY,bottomRightX,bottomRightY,\
            iteration,callerName='',undoRedo=False):
        """
        In a selected region, use morphology filter, dialate, to increase the 
        size of the selected area.
        """
        if(iteration==0):
            return image
        
        if(callerName!='enfaceDrusenViewer'):
            reg=image[topLeftY:bottomRightY,topLeftX:bottomRightX]
            tmp=np.copy(reg)
            reg=sc.ndimage.morphology.binary_dilation(reg,\
                                  iterations=iteration).astype(image.dtype)*255
            xs,ys=np.where(reg!=tmp)
            xs=xs+topLeftY
            ys=ys+topLeftX
            image[topLeftY:bottomRightY,topLeftX:bottomRightX]=reg
            
        self.mainWindowUi.content_changed(callerName)
        if(not undoRedo and callerName!='enfaceDrusenViewer'):
            if(len(xs)>0 and len(ys)>0):
                if(callerName=='hrfViewer'):
                    self.mainWindowUi.draw_dilate_command(xs,ys,[255,255,255],\
                         callerName,self.currentHRFNumber)
                else:
                    self.mainWindowUi.draw_dilate_command(xs,ys,[255,255,255],\
                         callerName,self.currentDrusenNumber)
                
        return image
        
    def remove_druse_at(self,slices,posY):
        return self.oct.remove_druse_at(slices,posY)
        
    def erosion_in_region(self,image,topLeftX,topLeftY,bottomRightX,\
                          bottomRightY,iteration,callerName='',undoRedo=False):
        """
        Use erosion morphology filter on the segmentation in the selected region
        to make the segmentation smaller by the given iteration value.
        """
        if(iteration==0):
            return image
        posX=[]
        tmp=np.copy(image)
        reg=image[topLeftY:bottomRightY,topLeftX:bottomRightX]
        tmp1=np.copy(reg)
        # With respect to the iteration extend region boundary to avoid cutting the boundaries
        reg=np.pad(reg,pad_width=iteration,mode='edge')
        reg=sc.ndimage.morphology.binary_erosion(reg,iterations=iteration).\
                astype(image.dtype)*255
        reg=reg[iteration:-iteration,iteration:-iteration]
        xs,ys=np.where(reg!=tmp1)
        xs=xs+topLeftY
        ys=ys+topLeftX
        image[topLeftY:bottomRightY,topLeftX:bottomRightX]=reg
        if(callerName=='enfaceDrusenViewer'):
            # Update all B-scans affected by this change
            slices,posY=np.where(image!=tmp)
            posX=self.remove_druse_at(slices,posY)   
            self.slice_value_changed(self.currentDrusenNumber,\
                    callerName='drusenViewer',furtherUpdate=False)          
        self.mainWindowUi.content_changed(callerName)
        if(not undoRedo):
            if(len(xs)>0 and len(ys)>0):
                if(callerName=='hrfViewer'):
                    self.mainWindowUi.draw_erosion_command(xs,ys,[0,0,0],\
                        callerName,self.currentHRFNumber,posX)
                else:
                    self.mainWindowUi.draw_erosion_command(xs,ys,[0,0,0],\
                        callerName,self.currentDrusenNumber,posX)
        return image
        
    def pen_or_line_undo(self,sliceNum,info,layerName):
        self.oct.pen_or_line_undo(sliceNum,info,layerName)
        
    def pen_or_line_redo(self,sliceNum,layerName):
        tmp= self.oct.pen_or_line_redo(sliceNum,layerName)
        return tmp
        
    def poly_fit_redo(self,image,topLeftX,topLeftY,bottomRightX,\
                        bottomRightY,polyDegree,layerName,sliceNum,callerName):
        """
        Fit polynomial in the selection region in the current slice. 
        """
        info=dict()
        
        h,w=image.shape
        reg=image[topLeftY:bottomRightY,topLeftX:bottomRightX]
        ty=min(h,bottomRightY+1)-bottomRightY
        by=max(0,topLeftY-1)-topLeftY
        tx=min(h,bottomRightX+1)-bottomRightX
        bx=max(0,topLeftX-1)-topLeftX
        reg2=image[max(0,topLeftY-1):min(h,bottomRightY+1),\
                max(0,topLeftX-1):min(w,bottomRightX+1)]
        s=np.sum(reg)
        if(s>0 and reg.shape[0]>1 and reg.shape[1]>1):
            if(layerName=='RPE'):
                info=self.oct.interpolate_layer_in_region(reg,reg2,by,ty,bx,tx,\
                    topLeftX,topLeftY,polyDegree,'RPE',sliceNum)
            elif(layerName=='BM'):
                info=self.oct.interpolate_layer_in_region(reg,reg2,by,ty,bx,tx,\
                    topLeftX,topLeftY,polyDegree,'BM',sliceNum)
            image[topLeftY:bottomRightY,topLeftX:bottomRightX]=info['reg']
        self.mainWindowUi.set_image_in_editor(image)
        self.mainWindowUi.content_changed('layerViewer')
        return info
        
    def poly_fit_undo(self,layerName,sliceNum,info,callerName):
        """
        Undo the polynomial fitting action.
        """
        self.oct.interpolate_layer_in_region_using_info(info,sliceNum-1,layerName)     
        self.slice_value_changed(sliceNum,'layerViewer',furtherUpdate=False)
        
    def polyfit_in_region(self,image,topLeftX,topLeftY,bottomRightX,\
            bottomRightY,polyDegree,callerName=''):
        """
        Create the command for polynomial fitting. 
        """
        # Get current state to store for redo
        if(self.editRPE):
            currLayer='RPE'
        elif(self.editBM):
            currLayer='BM'
        sliceNum=self.currentLayerNumber
        self.mainWindowUi.draw_poly_fit_command(image,topLeftX,topLeftY,\
             bottomRightX,bottomRightY,sliceNum,polyDegree,currLayer,callerName)
 
    def drusen_value_changed(self,callerName):
        if(callerName=='drusenViewer'):
            self.drusenEditted=True
        elif(callerName=='enfaceDrusenViewer'):
            self.enfaceDrusenEditted=True
            
    def layer_value_changed(self,callerName):
        if(callerName=='layerViewer'):
            self.layerEditted=True
            
    def hrf_value_changed(self,callerName):
        if(callerName=='hrfViewer'):
            self.hrfEditted=True    
            
    def ga_value_changed(self,callerName):
        if(callerName=='gaViewer'):
            self.gaEditted=True    
            
    def enface_value_changed(self,callerName):
        if(callerName=='enfaceViewer'):
            self.enfaceEditted=True  
            
    def grap_position_changed(self,position,sliceNum,callerName=''):
        """
        Grab position changing, change the A-scan line and B-scan values according
        to the selected point using the grab tool.
        """
        position=int(min(self.oct.width-1,max(0,position)))
        sliceNum=int(min(self.oct.numSlices,max(0,sliceNum)))+1
        
        if(not self.enfaceDrusenController is None):
            sliceNum=min(sliceNum,self.oct.numSlices)
            self.enfaceDrusenController.select_component(sliceNum,position)
            
        if(callerName=='enfaceDrusenViewer' or callerName=='enfaceViewer'):
             self.slice_value_changed(sliceNum,'enfaceDrusenViewer',furtherUpdate=False)
             self.set_drusen_slice_number(sliceNum)
        
        self.mainWindowUi.set_grab_position(position,callerName)
         
    def numpy_to_pixmap(self,image):   
        """
        Convert numpy array into pixmap.
        """
        qimg=q2np.array2qimage(image)
        pixImage=QtGui.QPixmap.fromImage(qimg)
        return pixImage
        
    def pixmap_to_numpy(self,pixImg):
        qimg=pixImg.toImage()
        return q2np.rgb_view(qimg)[:,:,0]
        
    def show_image(self,image):
        self.mainWindowUi.show_image(image)
    
    # ToolBox activations
    def activate_pen(self):
        self.mainWindowUi.set_pen()
    
    def activate_line(self):
        self.mainWindowUi.set_line()
    
    def activate_fill(self):
        self.mainWindowUi.set_fill()
    
    def activate_draw_dru(self):
        self.mainWindowUi.set_draw_dru()
        
    def activate_morphology(self,itLevel):
        self.mainWindowUi.set_morphology(itLevel)
        
    def activate_filter_dru(self,filteringHeight,maxFilteringHeight):
        self.mainWindowUi.set_filter_dru(filteringHeight,maxFilteringHeight)
    
    def activate_grab(self):
        self.mainWindowUi.set_grab()
    
    def activate_bounding_box(self):        
        self.mainWindowUi.set_bounding_box()  
        
    def activate_cost_point(self,value):        
        self.mainWindowUi.set_cost_point(value)      
        
    def activate_poly_fit(self,value):        
        self.mainWindowUi.set_poly_fit(value)  
        
    def activate_drusen_spliting(self,value):     
        self.mainWindowUi.set_druse_splitting(value)
        # Perform splitting
        if(self.enfaceDrusenController is None):
            self.enfaceDrusenController=edc.EnfaceDrusenController(\
                 self.oct.get_drusen(),self.oct.get_enface()[0],self)
            self.enfaceDrusenController.split_druse()
        else:
            self.enfaceDrusenController.split_druse()
        
    def all_threshold_value_changed(self,value):
        self.all_threshold=value
        self.mainWindowUi.all_threshold_value_changed(value)
       
    def morphology_value_changed(self,value):
        self.mainWindowUi.morphology_value_changed(value)
    
    def poly_fit_degree_value_changed(self,value):
        self.mainWindowUi.polydegree_value_changed(value)
        
    def smoothness_value_changed(self,value):
        self.oct.set_smoothness_value(value)
        self.mainWindowUi.smoothness_value_changed(value)
        
    def max_threshold_value_changed(self,value):
        self.max_threshold=value
        self.mainWindowUi.max_threshold_value_changed(value)
       
    def pixel_unit_selected(self):
        cx,cy,area,height,volume,largeR,smallR,theta=self.oct.get_druse_info()
        self.mainWindowUi.update_drusen_table(cx,cy,area,height,volume,largeR,smallR,theta)
        
    def micrometer_unit_selected(self):  
        cx,cy,area,height,volume,largeR,smallR,theta=self.oct.convert_from_pixel_size_to_meter()
        self.mainWindowUi.update_drusen_table(cx,cy,area,height,volume,largeR,smallR,theta)
        
    def export_drusen_analysis(self):        
        self.oct.save_drusen_quantification(self.lastScanPath,unit='pixel')
        self.oct.save_drusen_quantification(self.lastScanPath,unit='micrometer')
        
    def update_drusen_analysis(self):
        self.mainWindowUi.update_drusen_analysis()
    
    def annotation_view_toggled(self,viewerName):
        self.mainWindowUi.annotation_view_toggled(viewerName)
     
    def run_watershed(self):
        """
        Run the watershed algorithm to perform druse splitting.
        """
        method=self.mainWindowUi.subwindowToolBoxUI.get_splitting_method()
        neighborhoodSize=self.mainWindowUi.subwindowToolBoxUI.get_neighborhood_size()
        separators,separatorsAvgHeight,labels=self.enfaceDrusenController.\
                                         run_watershed(method,neighborhoodSize)
        if(not separators is None):
            self.mainWindowUi.show_drusen_splitting_separators(separators,\
                                                    separatorsAvgHeight,labels)
            
    def separation_theshold_changed(self,value):
        self.mainWindowUi.separation_theshold_changed(value)
    
    def warn_cannot_open_network(self):
        self.mainWindowUi.warn_cannot_open_network()
        
if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    octController=OCTController(app)
    octController.mainWindow.showMaximized()
    sys.exit(app.exec_())
