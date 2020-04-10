#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr  2 16:00:52 2020

@author: marcnol
"""
import os
import numpy as np
import cv2
from skimage import io
import scipy.optimize as spo
import matplotlib.pyplot as plt
#from matplotlib import cm
#from PIL import Image as pil
from skimage import exposure
from skimage.feature.register_translation import _upsampled_dft
from scipy.ndimage import fourier_shift

class Image():
    def __init__(self):
        self.data=[]
        self.fileName=''
        self.data_2D=np.zeros((1,1))
        self.stageCoordinates=[0.0, 0.0]
        self.imageSize=-1
        self.focusPlane=-1
        self.extension=''
        
    # read an image as a numpy array
    def loadImage(self,fileName):
        self.data = io.imread(fileName).squeeze()
        self.fileName=fileName
        self.imageSize=self.data.shape
        self.extension=fileName.split('.')[-1]
        
    # save 2D projection as numpy array
    def saveImage2D(self,log,rootFolder,tag='_2d'):
        fileName=rootFolder+os.sep+os.path.basename(self.fileName).split('.')[0]+tag
        saveImage2Dcmd(self.data_2D,fileName,log)

    # read an image as a numpy array
    def loadImage2D(self,fileName,log,dataFolder,tag='_2d'):
        self.fileName=fileName
        #fileName=self.fileName.split('.'+self.extension)[0]+'_2d.npy'
        fileName=dataFolder.zProjectFolder+os.sep+os.path.basename(self.fileName).split('.')[0]+tag+'.npy'

        self.data_2D=np.load(fileName)
        log.report("Loading 2d projection from disk:{}".format(os.path.basename(fileName)),'info')
        #print("Loading 2d projection from disk:{}".format(fileName))

    # max intensity projection using all z planes
    def maxIntensityProjection(self):
        self.data_2D = np.max(self.data, axis=0)
    
    # Normalize a 3d image <im> by subtracting local gaussian blur of std <sz>
    def normalizeImage(self,im,sz=30,ratio=False):
        im_ = np.array(im,dtype=np.float32)
        im_blur = np.array([cv2.blur(im__,(sz,sz)) for im__ in im_])
        if ratio:
            im_ =im_/im_blur
        else:
            im_ =(im_-im_blur)/np.median(im_blur)
        return im_
    
    # returns the imagename
    def getImageFilename(self):
        return self.fileName

    # returns the picture x,y location, if available
    def getImageLocation(self):
        if hasattr(self, "stageCoordinates"):
            return self.stageCoordinates
        else:
            return [0.0, 0.0]    
        
    # returns the film size
    def getImageSize(self):
        return self.imageSize
    
    # returns the film focus
    def getFocusPlane(self):
        if hasattr(self, "focusPlane"):
            return self.focusPlane
        else:
            return 0.0
       
    # Outputs image properties to command line
    def printImageProperties(self): 
        #print("Image Name={}".format(self.fileName))
        print("Image Size={}".format(self.imageSize))
        print("Stage position={}".format(self.stageCoordinates))
        print("Focal plane={}".format(self.focusPlane))
        
    # processes sum image in axial direction given range
    def zProjectionRange(self, parameters,log):
        
        # find the correct range for the projection
        if parameters.param['zProject']['zmax'] > self.imageSize[0]:
            log.report("Setting z max to the last plane")
            parameters.param['zProject']['zmax'] = self.imageSize[0]
        
        if parameters.param['zProject']['mode']=='automatic':
            print("Calculating planes...")
            zRange = calculate_zrange(self.data, parameters)
        elif parameters.param['zProject']['mode']=='full':
            (zmin, zmax) = (0, self.imageSize[0])
            zRange=(round((zmin+zmax)/2),range(zmin,zmax))
        else:
            # Manual: reads from parameters file
            (zmin, zmax) = (parameters.param['zProject']['zmin'],
                                     parameters.param['zProject']['zmax'])
            zRange=(round((zmin+zmax)/2),range(zmin,zmax))
        
        log.report("Processing zRange:{}".format(zRange))
 
        # sums images
        I_collapsed = np.zeros((self.imageSize[1], self.imageSize[2]))
        if parameters.param['zProject']['zProjectOption']=='MIP':
            # Max projection of selected planes
            I_collapsed = np.max(self.data[zRange[1][0]:zRange[1][1]], axis=0)
        else:
            # Sums selected planes
            for i in zRange[1]:
                I_collapsed  += self.data[i]

        self.data_2D=I_collapsed  
        self.zRange=zRange[1]
        self.focusPlane=zRange[0]
        
    # displays image and shows it
    def imageShow(self,show=True,cmap='plasma',size=(10,10),dpi=300,outputName='tmp.png',save=True):
        fig = plt.figure()
        fig.set_size_inches(size)
        ax = plt.Axes(fig, [0., 0., 1., 1.])
        ax.set_axis_off()
        plt.set_cmap(cmap)
        if show:
            fig.add_axes(ax)
            ax.imshow(self.data_2D, aspect='equal')

        if save:
            plt.imsave(outputName, self.data_2D)
    
################################################################################
# Functions
#################################################################################

# Gaussian function
def gaussian(x, a=1, mean=0, std=0.5):
    return a*(1/(std*(np.sqrt(2*np.pi))))*(np.exp(-((x-mean)**2)/((2*std)**2)))

# Finds best focal plane by determining the max of the std deviation vs z curve    
def calculate_zrange(idata, parameters):
    """
    Calculates the focal planes based max standard deviation
    """
    zwin = parameters.param['zProject']['zwindows']
    numPlanes = parameters.param['zProject']['zmax'] - parameters.param['zProject']['zmin']
    stdMatrix = np.zeros(numPlanes)
    meanMatrix = np.zeros(numPlanes)
    # calculate STD in each plane
    #print("Building planes..." )
    for i in range(0, numPlanes):
        stdMatrix[i] = np.std(idata[i])
        meanMatrix[i] = np.mean(idata[i])


    maxStd = np.max(stdMatrix)
    ifocusPlane = np.where(stdMatrix == maxStd)[0][0]
    # Select a window to avoid being on the edges of the stack
    '''
    zmin = max(ifocusPlane - parameters.param['process']['windowSecurity'],
                          parameters.param['process']['zmin'])
    zmax = min(ifocusPlane + parameters.param['process']['windowSecurity'],
                          parameters.param['process']['zmax'])
    '''
    if (ifocusPlane < parameters.param['zProject']['windowSecurity']
        or (ifocusPlane > numPlanes
        - parameters.param['zProject']['windowSecurity'])):
       focusPlane = ifocusPlane
    else:
        # interpolate zfocus
        axisZ = range(max(parameters.param['zProject']['zmin'],
                      ifocusPlane - parameters.param['zProject']['windowSecurity'],
                      min(parameters.param['zProject']['zmax'],
                      ifocusPlane
                      + parameters.param['zProject']['windowSecurity'])))

        stdMatrix -= np.min(stdMatrix)
        stdMatrix /= np.max(stdMatrix)
        #plt.plot(stdMatrix)
        try:
            fitgauss = spo.curve_fit(gaussian, axisZ, stdMatrix[axisZ[0]:axisZ[-1]+1])
            #print("Estimation of focal plane (px): ", int(fitgauss[0][1]))
            focusPlane = int(fitgauss[0][1])
        except RuntimeError:
            print('Warning, too many iterations')
            focusPlane = ifocusPlane

    zmin=max(parameters.param['zProject']['windowSecurity'],
             focusPlane-parameters.param['zProject']['zwindows'])
    zmax=min(numPlanes, parameters.param['zProject']['windowSecurity']+numPlanes,
              focusPlane+parameters.param['zProject']['zwindows'])
    zrange = range(zmin, zmax + 1)
        
    return focusPlane, zrange


def imageAdjust(image,log1,fileName='test',lower_threshold=0.3, higher_threshold=.9999,display=False):
    # rescales image to [0,1]
    image1=exposure.rescale_intensity(image,out_range=(0,1))
    
    # calculates histogram of intensities
    hist1_before=exposure.histogram(image1)

    sum=np.zeros(len(hist1_before[0]))
    for i in range(len(hist1_before[0])-1):
        sum[i+1]=sum[i]+hist1_before[0][i]
        
    sum_normalized=sum/sum.max()
    lower_cutoff=np.where(sum_normalized>lower_threshold)[0][0]/255
    higher_cutoff=np.where(sum_normalized>higher_threshold)[0][0]/255
    ###############################################################
    
    log1.report("Lower-Upper thresholds for {}: {:.2f}-{:.2f}".format(os.path.basename(fileName),lower_cutoff,higher_cutoff))

    # adjusts image intensities from (lower_threshold,higher_threshold) --> [0,1]
    image1=exposure.rescale_intensity(image1,in_range=(lower_cutoff,higher_cutoff),out_range=(0,1))
    
    # calculates histogram of intensities of adjusted image
    hist1=exposure.histogram(image1)
    
    if display:
        plt.figure(figsize=(30, 30))
        plt.imsave(fileName+'_adjusted.png',image1,cmap='hot')
    
    return image1,hist1_before, hist1, lower_cutoff, higher_cutoff


def save2imagesRGB(I1,I2,outputFileName):
    '''
    Overlays two images as R and B and saves them to output file
    '''
    RGB_falsecolor_image=np.dstack([I1,np.zeros([2048,2048]),I2])
    plt.figure(figsize=(30, 30))
    plt.imsave(outputFileName, RGB_falsecolor_image)
        
    
def saveImage2Dcmd(image,fileName,log):
    if image.shape>(1,1):
        np.save(fileName,image)
        log.report("Saving 2d projection to disk:{}\n".format(os.path.basename(fileName)),'info')
    else:
        log.report("Warning, data_2D does not exist",'Warning')

