# -*- coding: utf-8 -*-
"""
Created in 2018

@author: Shekoufeh Gorgi Zadeh
"""
import re
import os
import pickle
import numpy as np
import scipy as sc
import pandas as pd
from skimage import io
from os import listdir
from scipy import misc
import skimage.measure as skm
from PyQt4 import QtCore, QtGui
from os.path import isfile, join
from matplotlib import pyplot as plt

import deeplearning
import drusenextractor

octParams = dict()
octParams['bResolution'] = 'high' #high
octParams['hx'] = 200./16. #x axis in each B-scan
octParams['hy'] = 200./51. #y axis in each B-scan 
octParams['hz'] = 200./10. #z axis in direction of B-scan slices
octParams['zRate'] = 2 #every 13 pixels for low resolution, every two pixels for high res

#==============================================================================
# OCT class contains the OCT volume, and related segmentation maps
#==============================================================================
class OCT:

    def __init__(self,controller):
        self.saveFormat='png'
        self.scanPath=""
        self.bResolution=''
        self.hx=200./16. #x axis in each B-scan
        self.hy=200./51. #y axis in each B-scan 
        self.hz=200./10. #z axis in direction of B-scan slices
        self.zRate=0. #every 13 pixels for low resolution, every two pixels for high res
        self.scans = None
        self.layers= None
        self.hrfs=None
        self.gas=None
        self.drusen= None
        self.enface= None
        self.enfaceDrusen=None
        self.hrfStatus=None
        self.hrfBBox=None
        self.enfaceBBox=None
        self.probMaps=None
        self.numSlices=0
        self.width=0
        self.height=0
        
        self.scanIDs=list()
        
        # Drusen analysis
        self.cx=None
        self.cy=None
        self.area=None
        self.height=None
        self.volume=None
        self.largeR=None
        self.smallR=None
        self.theta=None
        
        self.controller=controller
        
        self.layerSegmenter=None 
        self.drusenSegmenter=None
        
        self.progressBarValue=0
        
        self.certainSlices=list()
        
        self.GTlayers=None
        self.distances=list()
        self.overallDistance=10000
        
    def show_image(self, image, block = True ):
        plt.imshow( image, cmap = plt.get_cmap('gray'))
        plt.show(block)    
          
        
    def set_scan_path(self,scanPath):
        self.scanPath=scanPath  
        
    def set_scan(self,scans):
        self.scans=scans
        
    def set_layers(self,layers):
        self.layers=layers
        
    def set_prob_maps(self,probMaps):
        self.probMaps=probMaps
        
    def set_hrfs(self,hrfs):
        self.hrfs=hrfs
        
    def set_gas(self,gas):
        self.gas=gas
        
    def set_ga(self,s,e,color,sliceNum):
        self.gas[:,s:e+1,sliceNum-1]=color
        
    def set_drusen(self,drusen):
        self.drusen=drusen
        
    def set_enface(self,enface):
        self.enface=enface
        
    def set_enface_drusen(self,enfaceDrusen):
        self.enfaceDrusen=enfaceDrusen
        
    def set_drusen_b_scan(self,sliceD,sliceNumber):
        self.drusen[:,:,int(sliceNumber)-1]=sliceD
        
    def set_HRF_status(self,index,status):
        self.hrfStatus[index]=status
    
    def set_hrf_bounding_boxes(self,bbox):
        self.hrfBBox=bbox
    
    def set_enface_bounding_boxes(self,bbox):
        self.enfaceBBox=bbox
    
    def set_smoothness_value(self,value):
        self.layerSegmenter.set_yLength(value)
        
    def set_progress_val(self,val):
        self.progressBarValue=val
        
        
    def save_drusen(self,savePath):
        savePath=os.path.join(savePath,'drusen')
        
        if(self.drusen is not None):
            self.create_directory(savePath)
            if(self.saveFormat=='pkl'):
                druLoc=np.where(self.drusen>0)
                self.write_pickle_data(os.path.join(savePath,'drusen.pkl'),druLoc)
            else:
                self.controller.show_progress_bar("Saving")
                pStep=100/float(max(1,self.drusen.shape[2]))
                for s in range(self.drusen.shape[2]):
                    self.controller.update_progress_bar_value(pStep)
                    misc.imsave(os.path.join(savePath,str(self.scanIDs[s])+\
                        '-drusen.png'),self.drusen[:,:,s])
                self.controller.hide_progress_bar()   
                
    def save_drusen_as(self,saveName):
        if(self.drusen is not None):
            if(self.saveFormat=='pkl'):
                druLoc=np.where(self.drusen>0)
                self.write_pickle_data(saveName,druLoc) 
            else:
                savePath,saveName=os.path.split(saveName)
                savePath=os.path.join(savePath,'drusen')
                
                saveName=saveName.split('.')[0]
                self.controller.show_progress_bar("Saving")
                pStep=100/float(max(1,self.drusen.shape[2]))
                for s in range(self.drusen.shape[2]):
                    self.controller.update_progress_bar_value(pStep)
                    misc.imsave(os.path.join(savePath,str(self.scanIDs[s])+\
                        '-'+saveName+'.png'),self.drusen[:,:,s])
                self.controller.hide_progress_bar()
                
    def save_layers(self,saveP):
        
        savePath=os.path.join(saveP,'layers')
        savePath2=os.path.join(saveP,'probabilityMaps')
        
        self.create_directory(savePath)
        self.create_directory(savePath2)
        if(self.layers is not None):
            layers=self.change_layers_format_for_saving()
            if(self.saveFormat=='pkl'):
                layerLoc=dict()       
                vs=np.unique(layers)
                for v in vs:
                    if(v==0):
                        continue
                    layerLoc[v]=np.where(layers==v)
                self.write_pickle_data(os.path.join(savePath,'layers.pkl'),layerLoc)
            else:
                self.controller.show_progress_bar("Saving")
                pStep=100/float(max(1,layers.shape[2]))
                for s in range(layers.shape[2]):
                    self.controller.update_progress_bar_value(pStep)
                    misc.imsave(os.path.join(savePath,str(self.scanIDs[s])+\
                        '-layers.png'),layers[:,:,s])
                    if(not self.probMaps is None):
                        io.imsave(os.path.join(savePath2,str(self.scanIDs[s])+\
                            '-0-layers.tif'),self.probMaps[:,:,0,s])
                        io.imsave(os.path.join(savePath2,str(self.scanIDs[s])+\
                            '-1-layers.tif'),self.probMaps[:,:,1,s])
                        io.imsave(os.path.join(savePath2,str(self.scanIDs[s])+\
                            '-2-layers.tif'),self.probMaps[:,:,2,s])
                        io.imsave(os.path.join(savePath2,str(self.scanIDs[s])+\
                            '-3-layers.tif'),self.probMaps[:,:,3,s])
                        
                u1,u2,u3=self.controller.get_uncertainties()
                if((not u1 is None) and (not u2 is None) and (not u3 is None)):
                    np.savetxt(os.path.join(savePath2,'prob-entropy.txt'),np.asarray(u1))
                    np.savetxt(os.path.join(savePath2,'prob.txt'),np.asarray(u2))
                    np.savetxt(os.path.join(savePath2,'entropy.txt'),np.asarray(u3))
                    
                self.controller.hide_progress_bar()
                
    def save_layers_as(self,saveName):
        if(self.layers is not None):
            if(self.saveFormat=='pkl'):
                layers=self.change_layers_format_for_saving()
                layerLoc=dict()       
                vs=np.unique(layers)
                for v in vs:
                    if(v==0):
                        continue
                    layerLoc[v]=np.where(layers==v)
                self.write_pickle_data(saveName,layerLoc)
            else:
                savePath,saveName=os.path.split(saveName)
                savePath=os.path.join(savePath,'layers')
                self.controller.show_progress_bar("Saving")
                pStep=100/float(max(1,layers.shape[2]))
                for s in range(layers.shape[2]):
                    self.controller.update_progress_bar_value(pStep)
                    misc.imsave(os.path.join(savePath,str(self.scanIDs[s])+\
                        '-'+saveName+'.png'),layers[:,:,s])
                self.controller.hide_progress_bar()
                
    def save_bbox(self,fileName,bboxesIn):
        f=open(fileName,'w')
        if(bboxesIn is not None):
            for sliceNum in bboxesIn.keys():
                strline=str(sliceNum+1)+':'
                bboxes=bboxesIn[sliceNum]
                for bbox in bboxes:
                    tl=bbox.topLeft()
                    br=bbox.bottomRight()
                    strline=strline+str(tl.x())+','+str(tl.y())+','+str(br.x())+\
                        ','+str(br.y())+'|'
                f.write(strline+'\n')
        f.close()
        
    def save_hrfs(self,savePath):
        savePath=os.path.join(savePath,'HRF')
        if(self.hrfs is not None):
            self.create_directory(savePath)
            if(self.saveFormat=='pkl'):
                hrfLoc=np.where(self.hrfs>0)
                self.write_pickle_data(os.path.join(savePath,'hrfs.pkl'),hrfLoc)
            else:
                self.controller.show_progress_bar("Saving")
                pStep=100/float(max(1,self.hrfs.shape[2]))
                for s in range(self.hrfs.shape[2]):
                    self.controller.update_progress_bar_value(pStep)
                    misc.imsave(os.path.join(savePath,str(self.scanIDs[s])+\
                        '-hrf.png'),self.hrfs[:,:,s])
                self.controller.hide_progress_bar()
            np.savetxt(os.path.join(savePath,'hrfs.txt'),self.hrfStatus)
            self.save_bbox(os.path.join(savePath,'hrfs-bounding-box.txt'),\
                self.hrfBBox)
            
    def save_hrfs_as(self,saveName):
        if(self.hrfs is not None):
            if(self.saveFormat=='pkl'):
                hrfLoc=np.where(self.hrfs>0)
                self.write_pickle_data(saveName,hrfLoc) 
            else:
                savePath,saveName=os.path.split(saveName)
                savePath=os.path.join(savePath,'HRF')
                self.controller.show_progress_bar("Saving")
                pStep=100/float(max(1,self.hrfs.shape[2]))
                for s in range(self.hrfs.shape[2]):
                    self.controller.update_progress_bar_value(pStep)
                    misc.imsave(os.path.join(savePath,str(self.scanIDs[s])+\
                                         '-'+saveName+'.png'),self.hrfs[:,:,s])
                self.controller.hide_progress_bar()
            np.savetxt(os.path.join(savePath,saveName+'.txt'),self.hrfStatus)
            self.save_bbox(os.path.join(savePath,saveName+'-bounding-box.txt'),\
                                         self.hrfBBox)
            
    def save_gas(self,savePath):
        savePath=os.path.join(savePath,'GA')
        if(self.gas is not None):
            self.create_directory(savePath)
            if(self.saveFormat=='pkl'):
                gaLoc=np.where(self.gas>0)
                self.write_pickle_data(os.path.join(savePath,'gas.pkl'),gaLoc)
            else:
                self.controller.show_progress_bar("Saving")
                pStep=100/float(max(1,self.gas.shape[2]))
                for s in range(self.gas.shape[2]):
                    self.controller.update_progress_bar_value(pStep)
                    misc.imsave(os.path.join(savePath,str(self.scanIDs[s])+\
                                                    '-ga.png'),self.gas[:,:,s])
                self.controller.hide_progress_bar()
    def save_gas_as(self,saveName):
        if(self.gas is not None):
            if(self.saveFormat=='pkl'):
                gaLoc=np.where(self.gas>0)
                self.write_pickle_data(saveName,gaLoc) 
            else:
                savePath,saveName=os.path.split(saveName)
                savePath=os.path.join(savePath,'GA')
                self.controller.show_progress_bar("Saving")
                pStep=100/float(max(1,self.gas.shape[2]))
                for s in range(self.gas.shape[2]):
                    self.controller.update_progress_bar_value(pStep)
                    misc.imsave(os.path.join(savePath,str(self.scanIDs[s])+'-'+\
                                              saveName+'.png'),self.gas[:,:,s]) 
                self.controller.hide_progress_bar()   
                
    def save_enface(self,savePath):
        savePath=os.path.join(savePath,'reticular-drusen')
        self.create_directory(savePath)
        self.save_bbox(os.path.join(savePath,\
                          'reticular-drusen-bounding-box.txt'),self.enfaceBBox)
                    
    def save_enface_as(self,saveName):
        savePath,saveName=os.path.split(saveName)
        savePath=os.path.join(savePath,'reticular-drusen')
        self.save_bbox(os.path.join(savePath,saveName+'-bounding-box.txt'),\
                                                               self.enfaceBBox)
        
    def save_drusen_quantification(self,savePath,unit='pixel'):
        savePath=os.path.join(savePath,'drusen-analysis')
        self.create_directory(savePath)

        if(unit=='pixel'):
            cxM=self.cx
            cyM=self.cy
            areaM=self.area
            heightM=self.height
            volumeM=self.volume
            largeM=self.largeR
            smallM=self.smallR
            saveName=os.path.join(savePath,'drusen-analysis-pixel.xlsx')
            
        elif(unit=='micrometer'):
            cxM,cyM,areaM,heightM,volumeM,largeM,smallM,\
                                  theta=self.convert_from_pixel_size_to_meter()
            saveName=os.path.join(savePath,'drusen-analysis-micrometer.xlsx')
            
        drusenInfo=dict()
        drusenInfo['Center']=list()
        drusenInfo['Area']=list()
        drusenInfo['Height']=list()
        drusenInfo['Volume']=list()
        drusenInfo['Diameter']=list()
        
        for i in range(len(cxM)):
            drusenInfo['Center'].append((int(cxM[i]),int(cyM[i])))
            drusenInfo['Area'].append(areaM[i])
            drusenInfo['Height'].append(heightM[i])
            drusenInfo['Volume'].append(volumeM[i])
            drusenInfo['Diameter'].append((largeM[i],smallM[i]))
            
        df=pd.DataFrame(drusenInfo,index=(np.arange(len(areaM))+1),\
                        columns=['Center','Area','Height','Volume','Diameter'])
        df.to_csv(saveName, sep='\t')

        return  

            
    def get_scan_path(self):
        return self.scanPath
        
    def get_scan(self):
        return self.scans
        
    def get_bbox_from_file_reticular(self,fileName):
        """
        Load the bounding box annotation for reticular drusen if there are any.
        """
        retBBox=dict()
        try:
            f=open(fileName,'r')
            lines=f.readlines()
            for l in lines:
                l=l.rstrip()
                boxes=l.split(':')[1]
                boxes=boxes.split('|')
                for box in boxes:
                    pnts=box.split(',')
                    if(len(pnts)==4):
                        rect=QtCore.QRect(QtCore.QPoint(int(pnts[0]),\
                                    int(pnts[1])),QtCore.QPoint(int(pnts[2]),\
                                    int(pnts[3])))
                        if(not 0 in retBBox.keys()):
                            retBBox[0]=list()
                        retBBox[0].append(rect)
            return retBBox
        except:
            return retBBox    
            
    def get_bbox_from_file(self,fileName):
        """
        Load the bounding box annotation for HRFs if there are any.
        """
        hrfBBox=dict()
        try:
            f=open(fileName,'r')
            lines=f.readlines()
            for l in lines:
                l=l.rstrip()
                sliceNum=int(l.split(':')[0])
                boxes=l.split(':')[1]
                boxes=boxes.split('|')
                for box in boxes:
                    pnts=box.split(',')
                    if(len(pnts)==4):
                        rect=QtCore.QRect(QtCore.QPoint(int(pnts[0]),\
                                int(pnts[1])),QtCore.QPoint(int(pnts[2]),\
                                int(pnts[3])))
                        if(not sliceNum-1 in hrfBBox.keys()):
                            hrfBBox[sliceNum-1]=list()
                        hrfBBox[sliceNum-1].append(rect)
            return hrfBBox
        except:
            return hrfBBox
            
    def get_hrfs(self):
        """
        Read the HRF segmentation from the disk if they exist.
        """
        scanPath=os.path.join(self.scanPath,'HRF')
        if(self.hrfs is None):  
            if(self.saveFormat=='pkl'):
                hrfLoc=self.read_pickle_data(os.path.join(scanPath,'hrfs.pkl'))
                self.hrfs=np.zeros(self.scans.shape)
                self.hrfs[hrfLoc]=255
            elif(self.saveFormat=='png'):
                self.create_directory(scanPath)
                d2 = [f for f in listdir(scanPath) if isfile(join(scanPath, f))]
                rawstack = list()
                ind = list()
                rawStackDict=dict()   
                rawSize=()
                for fi in range(len(d2)):
                     filename = os.path.join(scanPath,d2[fi])
                     ftype = d2[fi].split('-')[-1]
                     if(ftype=='hrf.png'):
                         ind.append(int(d2[fi].split('-')[0]))
                
                         raw = io.imread(filename)
                         rawSize = raw.shape
                         rawStackDict[ind[-1]]=raw
                if(len(rawSize)>0):
                    rawstack=np.empty((rawSize[0],rawSize[1],len(ind)))   
                    keys=rawStackDict.keys()
                    keys.sort()
                    i=0
                    for k in keys:
                        rawstack[:,:,i]=rawStackDict[k]
                        i+=1
                        
                    self.hrfs=np.copy(rawstack)
            if(self.hrfs is None):
                self.hrfs=np.zeros(self.scans.shape)
            try:
        
                self.hrfStatus=np.loadtxt(os.path.join(scanPath,'hrfs.txt'))
                self.hrfStatus=self.hrfStatus.astype(bool)
            except:
                self.hrfStatus=np.empty(self.scans.shape[2],dtype=bool)
                self.hrfStatus.fill(False)
           
            if(self.hrfStatus.shape[0]!=self.hrfs.shape[2]):
                self.hrfStatus=np.empty(self.hrfs.shape[2],dtype=bool)
                self.hrfStatus.fill(False)
                
            self.hrfBBox=self.get_bbox_from_file(os.path.join(scanPath,\
                'hrfs-bounding-box.txt'))
   
        return self.hrfs,self.hrfStatus,self.hrfBBox
        
    def get_gas(self):
        """
        Read the GA segmentation maps from the disk if they exist.
        """
        scanPath=os.path.join(self.scanPath,'GA')
        if(self.gas is None):  
            if(self.saveFormat=='pkl'):
                gasLoc=self.read_pickle_data(os.path.join(scanPath,'gas.pkl'))
                self.gas=np.zeros(self.scans.shape)
                self.gas[gasLoc]=255
            elif(self.saveFormat=='png'):
                self.create_directory(scanPath)
                d2 = [f for f in listdir(scanPath) if isfile(join(scanPath, f))]
                rawstack = list()
                ind = list()
                rawStackDict=dict()   
                rawSize=()
                for fi in range(len(d2)):
                     filename = os.path.join(scanPath,d2[fi])
                     ftype = d2[fi].split('-')[-1]
                     if(ftype=='ga.png'):
                         ind.append(int(d2[fi].split('-')[0]))
                
                         raw = io.imread(filename)
                         rawSize = raw.shape
                         rawStackDict[ind[-1]]=raw
                if(len(rawSize)>0):
                    rawstack=np.empty((rawSize[0],rawSize[1],len(ind)))   
                    keys=rawStackDict.keys()
                    keys.sort()
                    i=0
                    for k in keys:
                        rawstack[:,:,i]=rawStackDict[k]
                        i+=1
                        
                    self.gas=np.copy(rawstack)
            if(self.gas is None):
                self.gas=np.zeros(self.scans.shape)
            
        return self.gas  
            
    def get_progress_val(self):
        return self.progressBarValue 
        
    def get_uncertainties_per_bscan(self):
        return self.layerSegmenter.get_uncertainties_per_bscan()
        
    def get_layer_from_path(self,scanPath):
        """
        Read retinal layer segmentation from disk. If there's no segmentation,
        use the CNN for automatic layer segmentation.
        """
        createLayerSeg=False
        # Check if path exists
        if not os.path.exists(scanPath):
            createLayerSeg=True
            self.create_directory(scanPath)
        # Check if layer files exist
        d2 = [f for f in listdir(scanPath) if isfile(join(scanPath, f))]
        if(len(d2)==0):
            createLayerSeg=True
            
        probPath=os.path.join(os.path.split(scanPath)[0],'probabilityMaps')   
        # Use Caffe to create initial layer segmentation
        if(createLayerSeg):  
            self.layerSegmenter=deeplearning.DeepLearningLayerSeg(self)
            layers=self.layerSegmenter.get_layer_seg_from_deepnet(self.scans)
            saveName='layers'
            self.probMaps=np.transpose(self.probMaps,(1,0,2,3))
            probmaps=self.probMaps
            
            self.create_directory(probPath)
            
            progressVal=self.get_progress_val()
            self.set_progress_val(progressVal+2)
            self.update_progress_bar()
            
            probmaps=probmaps.astype('float16')
            for s in range(layers.shape[2]):
                
                layers[:,:,s]=self.convert_indices(layers[:,:,s])
                misc.imsave(os.path.join(scanPath,str(self.scanIDs[s])+'-'+\
                    saveName+'.png'),layers[:,:,s])
                io.imsave(os.path.join(probPath,str(self.scanIDs[s])+'-0-'+\
                    saveName+'.tif'),probmaps[:,:,0,s])
                io.imsave(os.path.join(probPath,str(self.scanIDs[s])+'-1-'+\
                    saveName+'.tif'),probmaps[:,:,1,s])
                io.imsave(os.path.join(probPath,str(self.scanIDs[s])+'-2-'+\
                    saveName+'.tif'),probmaps[:,:,2,s])
                io.imsave(os.path.join(probPath,str(self.scanIDs[s])+'-3-'+\
                    saveName+'.tif'),probmaps[:,:,3,s])
        try:
           
            self.certainSlices=list(np.where(np.loadtxt(os.path.join(probPath,\
                'prob-entropy.txt'))==0.05)[0])
            
        except:
            self.certainSlices=list()
        self.progressBarValue=100
        self.controller.set_progress_bar_value(self.progressBarValue)
        QtGui.QApplication.processEvents()        
        d2 = [f for f in listdir(scanPath) if isfile(join(scanPath, f))]    
        return d2
        
    def get_GT_layers(self):
        """
        Read ground truth for the layer segmentation. Useful for the software
        evaluation.
        """
        scanPath=os.path.join(self.scanPath,'GT')
        showLayersOnScan=False
        d2 = [f for f in listdir(scanPath) if isfile(join(scanPath, f))]
        rawstack = list()
        ind = list()
        rawStackDict=dict()   
        rawSize=()
        for fi in range(len(d2)):
             filename = os.path.join(scanPath,d2[fi])
             ftype = d2[fi].split('-')[-1]
             if(ftype=='BinSeg.tif'):
                 ind.append(int(d2[fi].split('-')[0]))
        
                 raw = io.imread(filename)
                 rawSize = raw.shape
                 rawStackDict[ind[-1]]=raw
        if(len(rawSize)>0):
            rawstack=np.empty((rawSize[0],rawSize[1],len(ind)))   
            keys=rawStackDict.keys()
            keys.sort()
            i=0
            for k in keys:
                rawstack[:,:,i]=rawStackDict[k]
                if(showLayersOnScan):
                    y,x=np.where(rawstack[:,:,i]>0)
                    self.scans[y,x,i]=255
                i+=1
                
            self.GTlayers=np.copy(rawstack)
            
    def get_distances(self):
        return self.overallDistance,self.distances
        
    def get_layers(self):
        """
        Find the layer segmentation for the RPE and BM layers.
        """
        scanPath=os.path.join(self.scanPath,'layers')
        if(self.layers is None):  
            if(self.saveFormat=='pkl'):
                layersLoc=self.read_pickle_data(os.path.join(scanPath,'layers.pkl'))
                self.layers=np.zeros(self.scans.shape)
                keys=layersLoc.keys()
                for v in keys:
                    self.layers[layersLoc[v]]=v
                self.change_layers_format_for_GUI()
            elif(self.saveFormat=='png'):
                self.controller.show_progress_bar()
                self.progressBarValue=1
                self.controller.set_progress_bar_value(self.progressBarValue)
        
                d2=self.get_layer_from_path(scanPath)
                 
                rawstack = list()
                ind = list()
                rawStackDict=dict()   
                rawSize=()
                for fi in range(len(d2)):
                     filename = os.path.join(scanPath,d2[fi])
                     ftype = d2[fi].split('-')[-1]
                     if(ftype=='layers.png'):
                         ind.append(int(d2[fi].split('-')[0]))
                
                         raw = io.imread(filename)
                         rawSize = raw.shape
                         rawStackDict[ind[-1]]=raw
                if(len(rawSize)>0):
                    rawstack=np.empty((rawSize[0],rawSize[1],len(ind)))   
                    keys=rawStackDict.keys()
                    keys.sort()
                    i=0
                    for k in keys:
                        rawstack[:,:,i]=rawStackDict[k]
                        i+=1
                        
                    self.layers=np.copy(rawstack)
                    self.layerSegmenter=deeplearning.DeepLearningLayerSeg(self)
                    self.change_layers_format_for_GUI()
                self.controller.hide_progress_bar()
            else:
                d2 = [f for f in listdir(scanPath) if isfile(join(scanPath, f))]
                rawstack = list()
                ind = list()
                rawStackDict=dict()   
                rawSize=()
                for fi in range(len(d2)):
                     filename = os.path.join(scanPath,d2[fi])
                     ftype = d2[fi].split('-')[-1]
                     if(ftype=='BinSeg.tif'):
                         ind.append(int(d2[fi].split('-')[0]))
                
                         raw = io.imread(filename)
                         rawSize = raw.shape
                         rawStackDict[ind[-1]]=raw
                if(len(rawSize)>0):
                    rawstack=np.empty((rawSize[0],rawSize[1],len(ind)))   
                    keys=rawStackDict.keys()
                    keys.sort()
                    i=0
                    for k in keys:
                        rawstack[:,:,i]=rawStackDict[k]
                        i+=1
                        
                    self.layers=np.copy(rawstack)
                    self.change_layers_format_for_GUI()
        
        return self.layers
        
    def get_prob_maps(self):
        return self.probMaps
        
    def get_current_path(self):
        return self.scanPath
        
    def get_drusen(self):
        """
        Read the drusen segmentation maps from the disk if exists, otherwise,
        compute them automatically from the retinal layer segmentations.
        """
        scanPath=os.path.join(self.scanPath,'drusen')
        if(self.drusen is None):  
            if(self.saveFormat=='pkl'):
                druLoc=self.read_pickle_data(os.path.join(scanPath,'drusen.pkl'))
                self.drusen=np.zeros(self.scans.shape)
                self.drusen[druLoc]=255
            elif(self.saveFormat=='png'):
                self.controller.show_progress_bar()
                d2=self.get_drusen_from_path(scanPath)
                self.controller.set_progress_bar_value(25)
                rawstack = list()
                ind = list()
                rawStackDict=dict()   
                rawSize=()
                
                pStep=50/float(len(d2))
                for fi in range(len(d2)):
                     self.controller.update_progress_bar_value(pStep)
                     filename = os.path.join(scanPath,d2[fi])
                     ftype = d2[fi].split('-')[-1]
                     if(ftype=='drusen.png'):
                         ind.append(int(d2[fi].split('-')[0]))
                
                         raw = io.imread(filename)
                         rawSize = raw.shape
                         raw[raw>0]=1
                         raw=self.filter_drusen_by_size(raw)
                         raw=raw*255
                         rawStackDict[ind[-1]]=raw
                if(len(rawSize)>0):
                    rawstack=np.empty((rawSize[0],rawSize[1],len(ind)))   
                    keys=rawStackDict.keys()
                    keys.sort()
                    i=0
                    pStep=25/float(max(1,len(keys)))
                    for k in keys:
                        self.controller.update_progress_bar_value(pStep)
                        rawstack[:,:,i]=rawStackDict[k]
                        i+=1
                    self.drusen=np.copy(rawstack)
                self.controller.update_progress_bar_value(100)
                self.controller.hide_progress_bar()
            else:
                d2 = [f for f in listdir(scanPath) if isfile(join(scanPath, f))]
                rawstack = list()
                ind = list()
                rawStackDict=dict()   
                rawSize=()
                for fi in range(len(d2)):
                     filename = os.path.join(scanPath,d2[fi])
                     ftype = d2[fi].split('-')[-1]
                     if(ftype=='binmask.tif'):
                         ind.append(int(d2[fi].split('-')[0]))
                
                         raw = io.imread(filename)
                         rawSize = raw.shape
                         raw[raw>0]=1
                         raw=self.filter_drusen_by_size(raw)
                         raw=raw*255
                         rawStackDict[ind[-1]]=raw
                if(len(rawSize)>0):
                    rawstack=np.empty((rawSize[0],rawSize[1],len(ind)))   
                    keys=rawStackDict.keys()
                    keys.sort()
                    i=0
                    for k in keys:
                        rawstack[:,:,i]=rawStackDict[k]
                        i+=1
                    self.drusen=np.copy(rawstack)
        
        return self.drusen
        
    def get_enface(self):
        """
        Read or create the enface projection image.
        """
        try:
            self.enface=io.imread(os.path.join(self.scanPath,"enface.png"))
           
        except:
            if(self.enface is None):
                self.controller.show_progress_bar()
                self.get_layers()
                projection,masks=self.produce_drusen_projection_image(useWarping=True )
                projection /= np.max(projection) if np.max(projection) != 0.0 else 1.0
                self.enface=(projection*255).astype(int)
                misc.imsave(os.path.join(self.scanPath,"enface.png"),self.enface)
                self.controller.set_progress_bar_value(100)
                QtGui.QApplication.processEvents()
                self.controller.hide_progress_bar()
        self.enfaceBBox=self.get_bbox_from_file_reticular(os.path.join(self.scanPath,'reticular-drusen','reticular-drusen-bounding-box.txt'))
        return self.enface,self.enfaceBBox
        
    def get_enface_drusen(self,recompute=True):
        """
        Compute the enface projection for the drusen segmentation maps.
        """        
        if(recompute):
            self.enfaceDrusen=((np.sum(self.drusen,axis=0)>0).astype(int).T)*255
        return self.enfaceDrusen
        
    def get_RPE_layer(self,seg_img):
        y = []
        x = []
        if( len(np.unique(seg_img)) == 4 ):
            tmp = np.zeros(seg_img.shape)
            tmp[np.where(seg_img==170)] = 255
            tmp[np.where(seg_img==255)] = 255
            y, x = np.where(tmp==255)
          
        else:
            y, x = np.where(seg_img==255)
        tmp = np.zeros(seg_img.shape)
        tmp[y,x] = 255
        y,x = np.where(tmp>0)
        return y,x
        
    def get_BM_layer(self,seg_img):
        y = []
        x = []
        if( len(np.unique(seg_img)) == 4 ):
            tmp = np.zeros(seg_img.shape)
            tmp[np.where(seg_img==170)] = 255
            tmp[np.where(seg_img==85)] = 255
            y, x = np.where(tmp==255)          
        else:
            y, x = np.where(seg_img==127)
        return y, x 
        
    def get_RPE_location( self,seg_img ):
        y = []
        x = []
        tmp = np.copy(seg_img)
        if( np.sum(seg_img)==0.0):
            return y, x
        if( len(np.unique(tmp)) == 4 ):
            tmp2 = np.zeros(tmp.shape)
            tmp2[np.where(tmp==170)] = 255
            tmp2[np.where(tmp==255)] = 255
            y, x = np.where(tmp2==255)
          
        else:
            y, x = np.where(tmp==255)
        return y, x
    
    def get_BM_location( self,seg_img ):
        y = []
        x = []
        tmp = np.copy(seg_img)
        if( np.sum(seg_img)==0.0):
            return y, x
        if( len(np.unique(tmp)) == 4 ):
            tmp2 = np.zeros(tmp.shape)
            tmp2[np.where(tmp==170)] = 255
            tmp2[np.where(tmp==85)] = 255
            y, x = np.where(tmp2==255)
        else:
            y, x = np.where(tmp==127)
        return y, x 
        
    def get_label_of_largest_component(self,labels ):
        size = np.bincount(labels.ravel())
        largest_comp_ind = size.argmax() 
        return largest_comp_ind
        
    def get_druse_info(self):
        return self.cx, self.cy, self.area, self.height, self.volume,\
               self.largeR, self.smallR,self.theta
        
        
        
    
    def hrf_exist_in_slice(self,sliceNum):
        s=np.sum(self.hrfs[:,:,sliceNum-1])
        if(s>0):
            return True
        else:
            return False
            
    def change_layers_format_for_GUI(self):
        for s in range(self.layers.shape[2]):                    
            if(170 in self.layers[:,:,s]):
                # Join point
                y,x=np.where(self.layers[:,:,s]==255)
                # RPE
                yrpe,xrpe=np.where(self.layers[:,:,s]==170)
                # BM
                ybm,xbm=np.where(self.layers[:,:,s]==85)
                self.layers[yrpe,xrpe,s]=255
                self.layers[y,x,s]=170
                self.layers[ybm,xbm,s]=127
                
    def change_layers_format_for_saving(self):
        layers=self.layers
        for s in range(layers.shape[2]):                    
            if(170 in layers[:,:,s]):
                # Join point
                y,x=np.where(layers[:,:,s]==170)
                # RPE
                yrpe,xrpe=np.where(self.layers[:,:,s]==255)
                # BM
                ybm,xbm=np.where(self.layers[:,:,s]==127)
                self.layers[yrpe,xrpe,s]=170
                self.layers[ybm,xbm,s]=85
                self.layers[y,x,s]=255
        return layers
        
    def interpolate_layer_in_region(self,reg,reg2,by,ty,bx,tx,topLeftX,\
            topLeftY,polyDegree,layerName,sliceNum):   
        if(self.drusenSegmenter is None):
            self.drusenSegmenter=drusenextractor.DrusenSeg(self.controller)
            
        info=dict()
        info['layers']=np.copy(reg)
        if(not self.probMaps is None):
            info['probMaps']=np.copy(self.probMaps[:,:,:,sliceNum-1])
            info['uncertainties']=self.layerSegmenter.get_uncertainties(sliceNum-1)
        else:
            info['probMaps']=None
            info['uncertainties']=None
        info['topLeftX']=topLeftX
        info['topLeftY']=topLeftY
        interpolated=self.drusenSegmenter.interpolate_layer_in_region(reg,reg2,\
                by,ty,bx,tx,polyDegree,layerName)
        interpolated[np.where(interpolated==85)]=127.
        
        eps=1.e-10
        if(not self.probMaps is None):
            if(layerName=='RPE'):
                y,x=self.drusenSegmenter.get_RPE_location(interpolated)
                
                self.probMaps[:,x+topLeftX,3,sliceNum-1]=eps
                self.probMaps[:,x+topLeftX,2,sliceNum-1]=eps
                self.probMaps[y+topLeftY,x+topLeftX,2,sliceNum-1]=1.
            elif(layerName=='BM'):
                y,x=self.drusenSegmenter.get_BM_location(interpolated)
                self.probMaps[:,x+topLeftX,3,sliceNum-1]=eps
                self.probMaps[:,x+topLeftX,1,sliceNum-1]=eps
                self.probMaps[y+topLeftY,x+topLeftX,1,sliceNum-1]=1.
                
        info['reg']=np.copy(interpolated)
        return info
        
    def interpolate_layer_in_region_using_info(self,info,sliceNumZ,layerName):
        reg=info['layers']
        
        self.layers[info['topLeftY']:info['topLeftY']+reg.shape[0],\
             info['topLeftX']:info['topLeftX']+reg.shape[1],sliceNumZ]=info['layers']
        if(not info['probMaps'] is None):   
            self.probMaps[:,:,:,sliceNumZ]=info['probMaps']
            self.layerSegmenter.set_uncertainties(info['uncertainties'],sliceNumZ)  
            self.controller.set_uncertainties(info['uncertainties'],sliceNumZ)  
            
   
    def convert_indices(self,s):
        ids=np.unique(s)
        if(max(ids)<5):
            if(len(ids)==4):
                s[np.where(s==3)]=255.
                s[np.where(s==2)]=170.
                s[np.where(s==1)]=127.
            else:
                s[np.where(s==2)]=255.
                s[np.where(s==1)]=127.
        return s
        
    def update_progress_bar(self):
        self.controller.set_progress_bar_value(self.progressBarValue)
        QtGui.QApplication.processEvents() 
        
    def compute_distance(self,gt,pr):
        distMeasure='RPEBM'
        gtRpe=np.sum((np.cumsum((gt>128).astype(float),axis=0)>0).astype(float),axis=0)
        gtBM=np.sum((np.cumsum((np.logical_and(gt<128,gt!=0)).astype(float).\
                                astype(float),axis=0)>0).astype(float),axis=0)
        
        prRpe=np.sum((np.cumsum((pr>128).astype(float).astype(float),axis=0)>0).astype(float),axis=0)
        prBM=np.sum((np.cumsum((np.logical_and(pr<128,pr!=0)).astype(float).\
                                astype(float),axis=0)>0).astype(float),axis=0)
        
        distRpe=np.abs(gtRpe-prRpe)
        distBM=np.abs(gtBM-prBM)
        
        distRpe[np.where(distRpe>100)]=0.
        distBM[np.where(distBM>100)]=0.
        
        rpeMax10=distRpe[np.where(distRpe>np.percentile(distRpe,90))]
        bmMax10=distBM[np.where(distBM>np.percentile(distBM,90))]
        
        if(distMeasure=='onlyBM'):
            nom=np.sum(bmMax10)
            denom=np.sum((bmMax10>0).astype(float))
        elif(distMeasure=='onlyRPE'):
            nom=np.sum(rpeMax10)
            denom=np.sum((rpeMax10>0).astype(float))
        else:
            nom=np.sum(rpeMax10)+np.sum(bmMax10)
            denom=np.sum((rpeMax10>0).astype(float))+np.sum((bmMax10>0).astype(float))
        if(denom == 0):
            return 0
        return nom/denom
    
    def update_distance(self,sliceNumZ):
        gt=self.GTlayers[:,:,sliceNumZ]        
        pr=self.layers[:,:,sliceNumZ]
        dist=self.compute_distance(gt,pr)
        self.distances[sliceNumZ]=dist
        self.overallDistance=sum(self.distances)/float(len(self.distances))
        return self.overallDistance,self.distances
        
    def compute_distances(self):
        sumD=0
        for s in range(self.layers.shape[2]):
            d=self.compute_distance(self.GTlayers[:,:,s],self.layers[:,:,s])
            self.distances.append(d)
            sumD+=d
        self.overallDistance=sumD/float(len(self.distances))
        
   
    def probmaps_does_exist(self):
        scanPath=os.path.join(self.scanPath,'layers')
        probPath=os.path.join(os.path.split(scanPath)[0],'probabilityMaps')
        self.create_directory(probPath)
        d2=[f for f in listdir(probPath) if isfile(join(probPath, f))]
        if(len(d2)==0):
            return False
        return True
   
    def compute_prob_maps(self):
        scanPath=os.path.join(self.scanPath,'layers')
        if(self.probMaps is None):
                if(self.layerSegmenter is None):
                    self.layerSegmenter=deeplearning.DeepLearningLayerSeg(self)
                probPath=os.path.join(os.path.split(scanPath)[0],'probabilityMaps')
                self.create_directory(probPath)
                d2=[f for f in listdir(probPath) if isfile(join(probPath, f))]
                if(len(d2)==0):
                    return -1 # probmapsDon't Exist
                rawstack = list()
                ind = list()
                rawStackDict=dict()   
                rawSize=()
                self.controller.show_progress_bar()
                pStep=80/float(max(1,len(d2)))
                for fi in range(len(d2)):
                     self.controller.update_progress_bar_value(pStep)
                     filename = os.path.join(probPath,d2[fi])
                     ftype = d2[fi].split('-')[-1]
                     if(ftype=='layers.tif'):
                         ind1=int(d2[fi].split('-')[0])
                         if(not ind1 in ind):
                             ind.append(ind1)
                         ind2=int(d2[fi].split('-')[1])
                         raw = io.imread(filename)
                         rawSize = raw.shape
                         if(not ind1 in rawStackDict.keys()):
                             rawStackDict[ind1]=np.empty((rawSize[0],rawSize[1],4))
                         rawStackDict[ind1][:,:,ind2]=raw
                
                if(len(rawSize)>0):
                    self.controller.update_progress_bar_value(5)
                    rawstack=np.empty((rawSize[0],rawSize[1],4,len(ind)))   
                    keys=rawStackDict.keys()
                    keys.sort()
                    i=0
                    pStep=15/float(max(1,len(keys)))
                    for k in keys:
                        self.controller.update_progress_bar_value(pStep)
                        rawstack[:,:,:,i]=rawStackDict[k]
                        i+=1
                    self.probMaps=np.copy(rawstack)
                    self.layerSegmenter.layers=self.layers
                self.controller.hide_progress_bar()
                
    def compute_uncertainties(self):
        self.layerSegmenter.compute_segmentation_uncertainty(self.certainSlices)

    def update_cost_rpe(self,i,j,sliceNumZ,smoothness): 
        info=dict()
        self.compute_prob_maps()
        info['probMaps']=np.copy(self.probMaps[:,:,:,sliceNumZ])
        info['layers']=np.copy(self.layers[:,:,sliceNumZ])
        info['uncertainties']=self.layerSegmenter.get_uncertainties(sliceNumZ)
        info['smoothness']=smoothness
        self.layers[:,:,sliceNumZ]=self.layerSegmenter.\
                    update_probability_image(i,j,sliceNumZ,'RPE',smoothness)
        return info

    def update_cost_rpe_using_info(self,info,sliceNumZ):
        self.probMaps[:,:,:,sliceNumZ]=info['probMaps']
        self.layers[:,:,sliceNumZ]=info['layers']
        self.layerSegmenter.set_uncertainties(info['uncertainties'],sliceNumZ)
        self.layerSegmenter.set_yLength(info['smoothness'])
        self.controller.set_uncertainties(info['uncertainties'],sliceNumZ)
        
    def update_cost_bm(self,i,j,sliceNumZ,smoothness):
        info=dict()
        self.compute_prob_maps()
        info['probMaps']=np.copy(self.probMaps[:,:,:,sliceNumZ])
        info['layers']=np.copy(self.layers[:,:,sliceNumZ])
        info['uncertainties']=self.layerSegmenter.get_uncertainties(sliceNumZ)
        info['smoothness']=smoothness
        self.layers[:,:,sliceNumZ]=self.layerSegmenter.\
                    update_probability_image(i,j,sliceNumZ,'BM',smoothness)
        return info

    def update_cost_bm_using_info(self,info,sliceNumZ):
        self.probMaps[:,:,:,sliceNumZ]=info['probMaps']
        self.layers[:,:,sliceNumZ]=info['layers']
        self.layerSegmenter.set_uncertainties(info['uncertainties'],sliceNumZ)   
        self.layerSegmenter.set_yLength(info['smoothness'])
        self.controller.set_uncertainties(info['uncertainties'],sliceNumZ)
        
    def get_drusen_from_path(self,scanPath):
        createDrusenSeg=False
        # Check if path exists
        if not os.path.exists(scanPath):
            createDrusenSeg=True
            self.create_directory(scanPath)
        # Check if drusen files exist
        d2 = [f for f in listdir(scanPath) if isfile(join(scanPath, f))]
        if(len(d2)==0):
            createDrusenSeg=True
        # Use rectification
        if(createDrusenSeg):  
            if(self.drusenSegmenter is None):
                self.drusenSegmenter=drusenextractor.DrusenSeg(self.controller)
            drusen=self.drusenSegmenter.get_drusen_seg_polyfit(self.layers)
            saveName='drusen'
            for s in range(drusen.shape[2]):
                misc.imsave(os.path.join(scanPath,str(self.scanIDs[s])+'-'+\
                                                saveName+'.png'),drusen[:,:,s])
            
        d2 = [f for f in listdir(scanPath) if isfile(join(scanPath, f))]    
        return d2 
    
    def walklevel(self,some_dir, level=1):
        some_dir = some_dir.rstrip(os.path.sep)
        assert os.path.isdir(some_dir)
        num_sep = some_dir.count(os.path.sep)
        for root, dirs, files in os.walk(some_dir):
            yield root, dirs, files
            num_sep_this = root.count(os.path.sep)
            if num_sep + level <= num_sep_this:
                del dirs[:]
    
    def atoi(self,text):
        return int(text) if text.isdigit() else text

    def natural_keys(self,text):
        '''
        alist.sort(key=natural_keys) sorts in human order
        http://nedbatchelder.com/blog/200712/human_sorting.html
        (See Toothy's implementation in the comments)
        '''
        return [ self.atoi(c) for c in re.split('(\d+)', text) ]
    
    def read_scan_from(self,scanPath):
        rawstack = list()
        ind = list()
        rawStackDict=dict()   
        rawSize=()
        idCounter=1
        
        for root,dirs,files in os.walk(scanPath):
            depth=len(scanPath.split(os.path.sep))
            curDepth=len(root.split(os.path.sep))
            if(curDepth>depth):
                continue
            if(len(files)<=0):
                return
            files.sort(key=self.natural_keys)
            for fname in files:
                if(fname=='enface.png'):
                    continue
                try:
                    ftype = fname.split('-')[-1]
                except:
                    ftype=""
                if(ftype=='Input.tif'):
                    ind.append(int(fname.split('-')[0]))
            
                    raw = io.imread(os.path.join(root,fname))
                    rawSize = raw.shape
                    rawStackDict[ind[-1]]=raw
                else:
                    try:
                        raw = io.imread(os.path.join(root,fname))
                    except:
                        print "Warning reading file:"+fname+" is not image."
                        continue
                    ind.append(idCounter)
                    idCounter+=1
                    
                    rawSize = raw.shape
                    rawStackDict[ind[-1]]=raw
        
        rawstack=np.empty((rawSize[0],rawSize[1],len(ind)))   
        keys=rawStackDict.keys()
        keys.sort()
        self.scanIDs=keys
        i=0
        for k in keys:
            rawstack[:,:,i]=rawStackDict[k]
            i+=1
            
        self.scans=np.copy(rawstack)
        self.numSlices=self.scans.shape[2]
        self.width=self.scans.shape[1]
        self.height=self.scans.shape[0]
        
        if(self.numSlices>50):
            self.zRate=2
            self.bResolution='high'
        else:
            self.zRate=13
            self.bResolution='low'
            
    def remove_druse_at(self,slices,posY):
        if(len(slices)>0):
            
            prevValues=np.copy(self.drusen[:,posY,slices])
            self.drusen[:,posY,slices]=0.
            return prevValues
            
    def insert_druse_at_pos(self,xs,ys,zs):
        self.drusen[xs,ys,zs]=255
        
    def insert_druse_at(self,slices,posY,posX):
        if(len(slices)>0):
            self.drusen[:,posY,slices]=posX
            
    def insert_hrf_at_slice(self,sliceNum,x,y,value):
        if(len(x)>0):
            self.hrfs[x,y,sliceNum-1]=value
            
    def insert_ga_at_slice(self,sliceNum,x,y,value):
        if(len(x)>0):
            self.gas[x,y,sliceNum-1]=value   
            
    def instert_druse_at_slice(self,sliceNum,x,y,value):
        if(len(x)>0):
            self.drusen[x,y,sliceNum-1]=value
    def instert_layer_at_slice(self,sliceNum,x,y,value):
        if(len(x)>0):
            for i in range(len(x)):
                self.layers[int(x[i]),int(y[i]),sliceNum-1]=int(value[i])
            
    def switch_BM_format(self,sliceNum):
        l=self.layers[:,:,sliceNum-1]
        if(170 in l):
            try:
                self.layers[np.where(l==127),sliceNum-1]=85
            except:
                pointsx,pointsy=np.where(l==127)
                for i in range(len(pointsx)):
                    x=pointsx[i]
                    y=pointsy[i]
                    h,w=self.layers[:,:,sliceNum-1].shape
                    if( x>=0 and x<h and y>=0 and y<w):
                        self.layers[x,y,sliceNum-1]=85
            
    def insert_value_at(self,x,y,z,value):
        if(len(x)>0):
            self.drusen[x,y,z]=value
            
    def delete_drusen_in_region(self,topLeftS,bottomRightS,topLeftY,bottomRightY):
        tmp=np.copy(self.drusen[:,topLeftY:bottomRightY,topLeftS:bottomRightS])
        self.drusen[:,topLeftY:bottomRightY,topLeftS:bottomRightS]=0.
        return np.where(tmp!=self.drusen[:,topLeftY:bottomRightY,topLeftS:bottomRightS])
        
    def produce_drusen_projection_image(self, useWarping=False):
        height,width,depth=self.scans.shape
        masks=np.zeros(self.scans.shape)
        xys=dict()
        xysn=dict()
        b_scans = self.scans.astype('float')
        projection = np.zeros((b_scans.shape[2], b_scans.shape[1]))
        total_y_max = 0
        progressStep=((100./float(b_scans.shape[2]))/3.)*2.
        progressValue=0.
        img_max = np.zeros(b_scans[:,:,0].shape)
        for i in range(b_scans.shape[2]):
            progressValue+=progressStep
            self.controller.set_progress_bar_value(int(progressValue))
            QtGui.QApplication.processEvents()
            
            b_scan = self.layers[:,:,i]
            y, x     = self.get_RPE_layer( b_scan )
            y_n, x_n = self.normal_RPE_estimation( b_scan,useWarping=useWarping )
            xys[i]=[y,x]
            xysn[i]=[y_n,x_n]
            vr = np.zeros((b_scans.shape[1]))
            vr[x] = y
            vn = np.zeros((b_scans.shape[1]))
            vn[x_n] = y_n
            y_diff   = np.abs(y-y_n)
            y_max    = np.max(y_diff)
            if( total_y_max < y_max ):             
                img_max.fill(0)
                img_max[y,x]=255
                img_max[y_n,x_n]=127
                total_y_max = y_max
        progressStep=((100./float(b_scans.shape[2]))/3.)*1.
        for i in range(b_scans.shape[2]):
            progressValue+=progressStep
            self.controller.set_progress_bar_value(int(progressValue))
            QtGui.QApplication.processEvents()
            b_scan = b_scans[:,:,i]
            b_scan = (b_scan - np.min(b_scan))/(np.max(b_scan)-np.min(b_scan)) if\
                     len(np.unique(b_scan))>1 else np.ones(b_scan.shape)
            label=self.layers[:,:,i]
            n_bscan  = np.copy(b_scan)
            y,x=xys[i]
            y_n,x_n=xysn[i]
            y_b, x_b = self.get_BM_layer( label )           
            y_max    = total_y_max
            upper_y  = (y_n - y_max)
            c = 0
            upper_y[np.where(upper_y<0)]=0
            upper_y[np.where(upper_y>=height)]=height-1
            for ix in x:
                n_bscan[y[c]:y_n[c],ix] = np.max(b_scan[upper_y[c]:y_n[c],ix])              
                projection[i,ix] =  np.sum(n_bscan[upper_y[c]:y_n[c]+1,ix])    
                c += 1        
        return projection.astype('float'), masks
        
        return y, x 
        
    def decompose_into_RPE_BM_images(self,image):
        rpeImg=((image==255)+(image==170)).astype(int)*255.
        bmImg=((image==127)+(image==170)+(image==85)).astype(int)*255.
        return rpeImg,bmImg
        
    def combine_RPE_BM_images(self,rpeImg,bmImg):
        join=rpeImg*bmImg
        rpeImg[bmImg==255]=127.
        rpeImg[join>0]=170.
        return rpeImg
        
    def normal_RPE_estimation(self, b_scan , degree = 3, it = 3, s_ratio = 1, \
                    farDiff = 5, ignoreFarPoints=True, returnImg=False,\
                    useBM = False,useWarping=True,xloc=[],yloc=[]):   
                        
        if(useWarping):
            y, x = self.get_RPE_location(b_scan)
            
            yn, xn = self.warp_BM(b_scan)
         
            return yn, xn
        if( useBM ):
            y_b, x_b = self.get_BM_location( b_scan ) 
            y_r, x_r = self.get_RPE_location( b_scan )  
            
            z = np.polyfit(x_b, y_b, deg = degree)            
            p = np.poly1d(z)        
            y_b = p(x_r).astype('int')
            
            prev_dist = np.inf
            offset = 0
            for i in range(50):
                 newyb = y_b - i
                 diff  = np.sum(np.abs(newyb-y_r))
                 if( diff < prev_dist ):
                      prev_dist = diff
                      continue
                 offset = i
                 break
            if( returnImg ):
                img = np.zeros(b_scan.shape)
                img[y_b-offset, x_r] = 255.0
                return y_b-offset, x_r, img
            return y_b-offset, x_r
            
        tmp = np.copy(b_scan)
        y = []
        x = []
        if(xloc==[] or yloc==[]):
            if( np.sum(b_scan)==0.0):
                return y, x
            if( len(np.unique(tmp)) == 4 ):
                tmp2 = np.zeros(tmp.shape)
                tmp2[np.where(tmp==170)] = 255
                tmp2[np.where(tmp==255)] = 255
                y, x = np.where(tmp2==255)
              
            else:
                y, x = np.where(tmp==255)
        else:
            y = yloc
            x = xloc
        tmpx = np.copy(x)
        tmpy = np.copy(y)
        origy = np.copy(y)
        origx = np.copy(x)
        finalx = np.copy(tmpx)
        finaly = tmpy
        for i in range(it):
            if( s_ratio > 1 ):
                s_rate = len(tmpx)/s_ratio
                rand   = np.random.rand(s_rate) * len(tmpx)
                rand   = rand.astype('int')            
                
                sx = tmpx[rand]
                sy = tmpy[rand]
                
                z = np.polyfit(sx, sy, deg = degree)
                
            else:
                z = np.polyfit(tmpx, tmpy, deg = degree)
            p = np.poly1d(z)
            
            new_y = p(finalx).astype('int')
            if( ignoreFarPoints ):
                tmpx = []
                tmpy = []
                for i in range(0,len(origx)):
                  diff=new_y[i]-origy[i]
                  if diff<farDiff:
                      tmpx.append(origx[i])
                      tmpy.append(origy[i])
            else:
                tmpy = np.maximum(new_y, tmpy)

            finaly = new_y
        
        if( returnImg ):
            return finaly, finalx, tmp
        
        return finaly, finalx
        
        
    def find_area_btw_RPE_normal_RPE(self,mask):
            area_mask = np.zeros(mask.shape)
            for i in range( mask.shape[1] ):
                col = mask[:,i]
                v1  = np.where(col==1.0)
                v2  = np.where(col==2.0)
                v3  = np.where(col==3.0)
               
                v1 = np.min(v1[0]) if len(v1[0]) > 0  else -1
                v2 = np.max(v2[0]) if len(v2[0]) > 0  else -1
                v3 = np.min(v3[0]) if len(v3[0]) > 0  else -1
                
                if( v1 >= 0 and v2 >= 0 ):
                    area_mask[v1:v2,i] = 1
            return area_mask
            
    def filter_drusen_by_size(self,dmask, slice_num=-1 ):
        h_threshold=0
        max_h_t=0
        w_over_h_ratio_threshold=0.0
        
        hv=(np.sum(dmask,axis=0)).astype(int)
        dmask[:,hv<h_threshold]=0
        return dmask
        
        drusen_mask = np.copy( dmask )
 
        if( h_threshold == 0.0 and  max_h_t == 0.0 and\
                    w_over_h_ratio_threshold == 10000.0 ):
            return drusen_mask
           
        cca, num_drusen = sc.ndimage.measurements.label( drusen_mask )
        filtered_mask = np.ones( drusen_mask.shape )
        h  = self.compute_heights( cca )
        filtered_mask[np.where( h <=  h_threshold )] = 0.0
      
        h  = self.compute_component_max_height( cca )
        filtered_mask[np.where( h <=  max_h_t )] = 0.0
        cca, num_drusen = sc.ndimage.measurements.label( filtered_mask )
        w_o_h, height  = self.compute_width_height_ratio_height_local_max( cca )
        filtered_mask = np.ones( drusen_mask.shape ).astype('float')
        filtered_mask[np.where(w_o_h  >  w_over_h_ratio_threshold)] = 0.0
        filtered_mask[np.where(w_o_h == 0.0)] = 0.0

        return filtered_mask
        
    def filter_druse_by_max_height(self,drusenImg,maxHeight):
        if(maxHeight==0):
            return drusenImg
        if(len(drusenImg.shape)<3):
            cca, num_drusen = sc.ndimage.measurements.label( drusenImg )
            h  = self.compute_component_max_height( cca )
            drusenImg[np.where(h<=maxHeight)] = 0.0
        else:
            heightProjection=np.sum((drusenImg>0).astype(int),axis=0)
            
            cca, num_drusen = sc.ndimage.measurements.\
                                      label((heightProjection>0).astype('int'))
            h  = self.compute_component_max_height(cca,heightProjection)
            heightProjection[np.where(h<=maxHeight)] = 0.0
            
            y,s=np.where(heightProjection==0)
            drusenImg[:,y,s]=0.
        return drusenImg
        
    def warp_BM(self, seg_img, returnWarpedImg=False ):
        h, w = seg_img.shape
        yr, xr = self.get_RPE_location( seg_img )
        yb, xb = self.get_BM_location( seg_img )
        rmask  = np.zeros((h, w), dtype='int')
        bmask  = np.zeros((h, w), dtype='int')
        rmask[yr, xr] = 255
        bmask[yb, xb] = 255
        vis_img = np.copy(seg_img)
        shifted = np.zeros(vis_img.shape)
        wvector = np.empty((w), dtype='int')
        wvector.fill(h-(h/2))
        nrmask = np.zeros((h,w), dtype='int')
        nbmask = np.zeros((h,w), dtype='int')
        
        zero_x =[]
        zero_part = False  
        last_nonzero_diff = 0
        for i in range(w):
            bcol = np.where(bmask[:,i]>0)[0]
            wvector[i] = wvector[i]-np.max(bcol) if len(bcol) > 0 else 0
            if( len(bcol) == 0  ):
                zero_part = True
                zero_x.append(i)
            if( len(bcol)>0 and zero_part ):
                diff = wvector[i]
                zero_part = False
                wvector[zero_x]=diff
                zero_x=[]
            if( len(bcol)>0):
                last_nonzero_diff = wvector[i]
            if( i == w-1 and zero_part):
                wvector[zero_x]=last_nonzero_diff
        for i in range(w):
            nrmask[:, i] = np.roll(rmask[:,i], wvector[i])
            nbmask[:, i] = np.roll(bmask[:,i], wvector[i])
            shifted[:, i] = np.roll(vis_img[:,i], wvector[i])
        shifted_yr =[]   
        for i in range(len(xr)):
            shifted_yr.append(yr[i] + wvector[xr[i]])
        yn, xn = self.normal_RPE_estimation( rmask,it=5,useWarping=False,\
                xloc=xr, yloc=shifted_yr )
        for i in range(len(xn)):
            yn[i] = yn[i] - wvector[xn[i]]
        if(returnWarpedImg):
            return shifted
            
        return yn, xn
        
    def compute_heights(self,cca ):
        bg_lbl  = self.get_label_of_largest_component( cca )
        mask  = cca != bg_lbl
        mask  = mask.astype('int')
        cvr_h = np.sum( mask, axis = 0 )
        hghts = np.tile( cvr_h, cca.shape[0] ).reshape(cca.shape)
        mask  = mask * hghts
        return mask
        
    def compute_component_max_height(self,cca,heights=[] ):
        labels  = np.unique( cca )
        max_hs  = np.zeros( cca.shape )
        if(heights==[]):
            heights = self.compute_heights( cca )
        for l in labels:
            
            region = cca == l
            max_hs[region] = np.max( region * heights )
            
        return max_hs
        
    def compute_width_height_ratio_height_local_max(self,cca ):
        mx_h = self.compute_component_sum_local_max_height( cca )
        mx_w = self.compute_component_width( cca )
        mx_h[mx_h == 0] = 1
        return mx_w.astype('float')/(mx_h.astype('float')), mx_h
          
    def compute_component_sum_local_max_height( self,cca ):
        labels  = np.unique( cca )
        max_hs  = np.zeros( cca.shape )  
        bg_lbl  = self.get_label_of_largest_component( cca )
        heights = self.compute_heights( cca )
        for l in labels:
            if( l != bg_lbl ):
                region = cca == l
                masked_heights = region * heights
                col_h = np.max( masked_heights, axis = 0 )
                local_maxima   = self.find_rel_maxima( col_h )
                if( len(local_maxima) == 0 ):
                    local_maxima = np.asarray([np.max(masked_heights)])
                max_hs[region] = np.sum(local_maxima)        
        
        return max_hs
        
    def compute_component_width(self,cca ):
        labels  = np.unique( cca )
        max_ws  = np.zeros( cca.shape )  
        bg_lbl  = self.get_label_of_largest_component( cca )
        for l in labels:
            if( l != bg_lbl ):
                y, x = np.where( cca == l )
                w = np.max(x) - np.min(x)
                max_ws[cca == l] = w
        return max_ws
        
    def find_rel_maxima(self, arr ):
        val = []
        pre = -1
        for a in arr:
            if( a != pre ):
                val.append(a)
            pre = a
        val = np.asarray(val)
        return val[sc.signal.argrelextrema(val, np.greater)]
        
    def is_rpe(self,value):
        if( value==170 or value==255 ):
            return True
        return False
        
    def is_above_rpe_and_white(self,image,x,y,c):
        if(image[x,y]==0 and c==255):
            return True
        return False
        
    def read_pickle_data(self,dataPath ):
        with open( dataPath, 'rb' ) as input:
            return pickle.load( input )
        
    def write_pickle_data(self,dataPath, d):
        with open( dataPath,'w') as output:
            pickle.dump( d, output, pickle.HIGHEST_PROTOCOL )
            
    def find_area_between_seg_lines(label):
        h, w = label.shape
        label_area = np.copy(label)
        ls = np.sort(np.unique( label_area ))
        if(False):
            if( len(ls) == 3):
        
                for j in range(w):
                    col = label[:, j]
                    l_1 = np.where( col == ls[1] )
                    l_2 = np.where( col == ls[2])
                    if(len(l_1[0]) != 0 and len(l_2[0]) != 0 ):
            
                        label_area[l_1[0][0]:l_2[0][0], j] = 1
                        label_area[l_2[0][0]:l_1[0][0], j] = 1
                        
                # Replace all the labels with 1
                label_area[label_area > 0] = 1
               
                return label_area  
            if( len(ls) == 4):
        
                for j in range(w):
                    col = label[:, j]
                    l_1 = np.where( col == ls[1] )
                    l_2 = np.where( col == ls[3])
                    if(len(l_1[0]) != 0 and len(l_2[0]) != 0 ):
            
                        label_area[l_1[0][0]:l_2[0][0], j] = 1
                        label_area[l_2[0][0]:l_1[0][0], j] = 1
                    
                # Replace all the labels with 1
                label_area[label_area > 0] = 1
               
                return label_area   
        else:
            for j in range(w):
                col = label[:, j]
                y=np.where(col>0)[0]
                if(len(y)>0):
                    minInd=np.min(y)
                    maxInd=np.max(y)
                    label_area[minInd:maxInd,j]=1
                    label_area[maxInd:minInd,j]=1
            label_area[label_area > 0] = 1
            return label_area
        return label
        
    def increase_resolution(self, b_scans, factor , interp='nearest'):
        
        self.controller.set_progress_bar_value(int(3))
        QtGui.QApplication.processEvents() 
        
        new_size = (b_scans.shape[0], b_scans.shape[1], b_scans.shape[2]*factor)
        res = np.zeros(new_size)
        progressValue=5.0
        
        self.controller.set_progress_bar_value(int(progressValue))
        QtGui.QApplication.processEvents()
        
        progressStep=((100./new_size[1])/3.)*2.
        
        for i in range(new_size[1]):
            progressValue+=progressStep
            self.controller.set_progress_bar_value(int(progressValue))
            QtGui.QApplication.processEvents() 
            slice_i = b_scans[:,i,:]
            
            res[:,i,:] = (misc.imresize(slice_i, (new_size[0], new_size[2]),\
                            interp = interp).astype('float'))/255.0
            mask=np.copy(np.cumsum(res[:,i,:],axis=0)*((res[:,i,:]>0).astype('int')))
            res[:,i,:]=(mask>=1.0).astype('float')
        return res,progressValue
   
    def convert_from_pixel_size_to_meter(self):    
        voxelSize = self.hx*self.hy*self.hz
        volumeM=self.volume * voxelSize
        areaM=self.area*self.hx*self.hz
        heightM=self.height*self.hy
        xM=self.largeR*np.cos(self.theta)*self.hx
        zM=self.largeR*np.sin(self.theta)*self.hz
        largeM=np.sqrt(xM**2+zM**2)
        thetaVer=self.theta+(np.pi/2.0)
        xM=self.smallR*np.cos(thetaVer)*self.hx
        zM=self.smallR*np.sin(thetaVer)*self.hz
        smallM=np.sqrt(xM**2+zM**2)
        return self.cx*self.hx,self.cy*self.hz,areaM, heightM, volumeM, largeM, smallM,self.theta
        
    def quantify_drusen(self):
        self.controller.show_progress_bar()
        
        projected_labels=self.enfaceDrusen
        labels=self.drusen
        
        progressValue=0.
        
        self.controller.set_progress_bar_value(int(1))
        QtGui.QApplication.processEvents()   
        realResProjLbl = sc.misc.imresize(projected_labels, size=\
                            (projected_labels.shape[0]*self.zRate,\
                            projected_labels.shape[1]),interp='nearest')
        self.controller.set_progress_bar_value(int(2))
        QtGui.QApplication.processEvents()  
        realResLbl,progressValue = self.increase_resolution(((labels>0).\
                        astype('float')), factor=self.zRate,interp='bilinear')
        
        heightImg  = np.sum(realResLbl, axis=0).T
        realResProjLbl = ((realResProjLbl*heightImg)>0.0).astype('float')
        self.controller.set_progress_bar_value(int(4))
        QtGui.QApplication.processEvents()
        cca, numL = sc.ndimage.measurements.label(realResProjLbl)
        self.controller.set_progress_bar_value(int(5))
        QtGui.QApplication.processEvents()  
            
        area=list()
        volume=list()
        largeR=list()
        smallR=list()
        theta=list()
        height=list()
        cx=list()
        cy=list()
        bgL = self.get_label_of_largest_component( cca )
        labels   = np.unique(cca)

        self.controller.set_progress_bar_value(int(progressValue))
        QtGui.QApplication.processEvents()
        
        progressStep=((100./len(labels))/3.)*1.
        
        for l in labels:
            
            if( l != bgL ):
                progressValue+=progressStep
                self.controller.set_progress_bar_value(int(progressValue))
                QtGui.QApplication.processEvents()
                
                componentL = (cca==l).astype('float')
                componentL=((heightImg*componentL)>0.0).astype('float')
                cyL,cxL = sc.ndimage.measurements.center_of_mass(componentL)
                areaL = np.sum(((heightImg*componentL)>0.0).astype('float'))
                volumeL = np.sum(heightImg*componentL)
                heightL = np.max(heightImg*componentL)
                largeL=0.0
                smallL=0.0
                thetaL=0.0
                props=skm.regionprops(componentL.astype('int'))
                for p in props:
                    if(p.label==1):
                        areaL=p.area
                        largeL=max(1.,p.major_axis_length)
                        smallL=max(1.,p.minor_axis_length)
                        thetaL=p.orientation
                 
                area.append(areaL)
                volume.append(volumeL)
                theta.append(thetaL)
                smallR.append(smallL)
                largeR.append(largeL)
                height.append(heightL)
                cx.append(cxL)
                cy.append(cyL)
    
        area = np.asarray(area)
        volume = np.asarray(volume)
        largeR = np.asarray(largeR)
        smallR = np.asarray(smallR)
        theta = np.asarray(theta)
        height=np.asarray(height)
        cy=np.asarray(cy)
        cx=np.asarray(cx)
        total=(area+height+volume+largeR+smallR)/5.0
        indx=np.argsort(total)
        indx=indx[::-1]
        area = area[indx]
        volume = volume[indx]
        largeR = largeR[indx]
        smallR = smallR[indx]
        theta = theta[indx]
        height=height[indx]
        cy=cy[indx]
        cx=cx[indx]
        
        self.controller.set_progress_bar_value(100)
        self.controller.hide_progress_bar()
        self.cx=cx
        self.cy=cy
        self.area=area
        self.height=height
        self.volume=volume
        self.largeR=largeR
        self.smallR=smallR
        self.theta=theta
        return cx, cy, area, height, volume, largeR, smallR, theta
        
    def pen_or_line_undo(self,sliceNum,info,layerName):
            
        sliceNumZ=sliceNum-1
        if(sliceNumZ in self.certainSlices):
            self.certainSlices.remove(sliceNumZ)
        
        self.layerSegmenter.set_uncertainties(info['uncertainties'],sliceNumZ)
        self.controller.set_uncertainties(info['uncertainties'],sliceNumZ)

    def pen_or_line_redo(self,sliceNum,layerName):
        info=dict()
        sliceNumZ=sliceNum-1
        self.certainSlices.append(sliceNumZ)
        
        
        info['uncertainties']=self.layerSegmenter.get_uncertainties(sliceNumZ)
        
        return info
        
    def create_directory(self,path):
        """
        Check if the directory exists. If not, create it.
        Input:
            path: the directory to create
        Output:
            None.
        """
        if not os.path.exists(path):
            os.makedirs(path)
