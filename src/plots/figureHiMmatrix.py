#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun  4 09:04:10 2020

@author: marcnol
 Produces 
"""


#%% imports and plotting settings
import os, sys
import numpy as np
import argparse

# import matplotlib as plt
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import json, csv

# import scaleogram as scg

from matrixOperations.HIMmatrixOperations import plotDistanceHistograms, plotMatrix, listsSCtoKeep
from matrixOperations.HIMmatrixOperations import (
    analysisHiMmatrix,
    normalizeMatrix,
    shuffleMatrix,
    plotScalogram,
    calculatesEnsemblePWDmatrix,
    loadList,
    calculateContactProbabilityMatrix,
)

#%% define and loads datasets


def parseArguments():
    # [parsing arguments]
    parser = argparse.ArgumentParser()
    parser.add_argument("-T", "--scPWDMatrix", help="Filename of single-cell PWD matrices in Numpy")
    parser.add_argument("-U", "--uniqueBarcodes", help="csv file with list of unique barcodes")
    parser.add_argument("-O", "--outputFolder", help="Folder for outputs")

    parser.add_argument(
        "-P", "--parameters", help="Provide name of parameter files. folders2Load.json assumed as default",
    )
    parser.add_argument("-A", "--label", help="Add name of label (e.g. doc)")
    parser.add_argument("-W", "--action", help="Select: [all], [labeled] or [unlabeled] cells plotted ")
    parser.add_argument("--fontsize", help="Size of fonts to be used in matrix")
    parser.add_argument("--axisLabel", help="Use if you want a label in x and y", action="store_true")
    parser.add_argument("--axisTicks", help="Use if you want axes ticks", action="store_true")
    parser.add_argument("--barcodes", help="Use if you want barcode images to be displayed", action="store_true")
    parser.add_argument(
        "--scalingParameter", help="Normalizing scaling parameter of colormap. Max will matrix.max()/scalingParameter"
    )
    parser.add_argument("--cScale", help="Colormap absolute scale")
    parser.add_argument("--plottingFileExtension", help="By default: png. Other options: svg, pdf, png")
    parser.add_argument(
        "--shuffle",
        help="Provide shuffle vector: 0,1,2,3... of the same size or smaller than the original matrix. No spaces! comma-separated!",
    )
    parser.add_argument("--proximity_threshold", help="proximity threshold in um")
    parser.add_argument("--pixelSize", help="pixel size in um")
    parser.add_argument("--cmap", help="Colormap. Default: coolwarm")
    parser.add_argument(
        "--mode", help="Mode used to calculate the mean distance. Can be either 'median', 'KDE' or 'proximity'. Default: median"
    )

    args = parser.parse_args()

    runParameters = {}

    if args.scPWDMatrix:
        runParameters["scPWDMatrix_filename"] = args.scPWDMatrix
    else:
        print('>> ERROR: you must provide a filename with the single cell PWD matrices in Numpy format')
        sys.exit(-1)

    if args.uniqueBarcodes:
        runParameters["uniqueBarcodes"] = args.uniqueBarcodes
    else:
        print('>> ERROR: you must provide a CSV file with the unique barcodes used')
        sys.exit(-1)

    if args.outputFolder:
        runParameters["outputFolder"] = args.outputFolder
    else:
        runParameters["outputFolder"] = "plots"

    if args.parameters:
        runParameters["parametersFileName"] = args.parameters
    else:
        runParameters["parametersFileName"] = "folders2Load.json"

    if args.label:
        runParameters["label"] = args.label
    else:
        runParameters["label"] = "doc"

    if args.action:
        runParameters["action"] = args.action
    else:
        runParameters["action"] = "labeled"

    if args.fontsize:
        runParameters["fontsize"] = args.fontsize
    else:
        runParameters["fontsize"] = 12

    if args.axisLabel:
        runParameters["axisLabel"] = args.axisLabel
    else:
        runParameters["axisLabel"] = False

    if args.axisTicks:
        runParameters["axisTicks"] = args.axisTicks
    else:
        runParameters["axisTicks"] = False

    if args.barcodes:
        runParameters["barcodes"] = args.barcodes
    else:
        runParameters["barcodes"] = False

    if args.scalingParameter:
        runParameters["scalingParameter"] = float(args.scalingParameter)
    else:
        runParameters["scalingParameter"] = 1.0

    if args.proximity_threshold:
        runParameters["proximity_threshold"] = float(args.proximity_threshold)
    else:
        runParameters["proximity_threshold"] = 0.5

    if args.cScale:
        runParameters["cScale"] = float(args.cScale)
    else:
        runParameters["cScale"] = 0.0

    if args.plottingFileExtension:
        runParameters["plottingFileExtension"] = "." + args.plottingFileExtension
    else:
        runParameters["plottingFileExtension"] = ".png"

    if args.shuffle:
        runParameters["shuffle"] = args.shuffle
    else:
        runParameters["shuffle"] = 0

    if args.pixelSize:
        runParameters["pixelSize"] = args.pixelSize
    else:
        runParameters["pixelSize"] = 1

    if args.cmap:
        runParameters["cmap"] = args.cmap
    else:
        runParameters["cmap"] = "coolwarm"

    if args.mode:
        runParameters["mode"] = args.mode
    else:
        runParameters["mode"] = "KDE"

    return runParameters


#%%

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":

    print(">>> Producing HiM matrix")
    
    runParameters = parseArguments()

    if os.path.exists(runParameters["scPWDMatrix_filename"]):
        SCmatrix = np.load(runParameters["scPWDMatrix_filename"])
    else:
        print("*** Error: could not find {}".format(runParameters["scPWDMatrix_filename"]))
        sys.exit(-1)

    if not os.path.exists(runParameters["outputFolder"]):
        os.mkdir(runParameters["outputFolder"])
        print("Folder created: {}".format(runParameters["outputFolder"]))

    nCells = SCmatrix.shape[2]

    cells2Plot = range(nCells)
    # cells2Plot = listsSCtoKeep(runParameters, HiMdata.data["SClabeledCollated"])
    
    print("$ N traces to plot: {}/{}".format(len(cells2Plot), SCmatrix.shape[2]))
    
    uniqueBarcodes = list(np.loadtxt(runParameters["uniqueBarcodes"], delimiter = " "))
    uniqueBarcodes = [int(x) for x in uniqueBarcodes]
    print(f'$ unique barcodes loaded: {uniqueBarcodes}')
    
    print(f'$ averaging method: {runParameters["mode"]}')
    
    if runParameters["cScale"] == 0:
        cScale = SCmatrix[~np.isnan(SCmatrix)].max() / runParameters["scalingParameter"]
    else:
        cScale = runParameters["cScale"]

    print("$ loaded cScale: {} | used cScale: {}".format(runParameters["scalingParameter"], cScale))

    outputFileName = (
        runParameters["outputFolder"]
        + os.sep
        + "Fig_HiMmatrix"
        + "_label:"
        + runParameters["label"]
        + "_action:"
        + runParameters["action"]
        + runParameters["plottingFileExtension"]
    )

    if runParameters["shuffle"] == 0:
        index = range(SCmatrix.shape[0])
    else:
        index = [int(i) for i in runParameters["shuffle"].split(",")]
        SCmatrix = shuffleMatrix(SCmatrix, index)

    if runParameters["mode"]=='proximity':
        # calculates and plots contact probability matrix from merged samples/datasets
        SCmatrix, nCells = calculateContactProbabilityMatrix(
            SCmatrix, uniqueBarcodes, runParameters["pixelSize"], norm="nCells",
        )  # norm: nCells (default), nonNANs

    plotMatrix(
        SCmatrix,
        uniqueBarcodes,
        runParameters["pixelSize"],
        1,
        outputFileName,
        'log',
        figtitle="Map: "+runParameters["mode"],
        mode=runParameters["mode"],  # median or KDE
        clim=cScale,
        nCells=nCells,
        cm=runParameters["cmap"],
        cmtitle="distance, um",
        fileNameEnding="_"+runParameters["mode"]+runParameters["plottingFileExtension"],
        )
    
    print("Output figure: {}".format(outputFileName))

    print("\nDone\n\n")
