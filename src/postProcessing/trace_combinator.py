#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Feb 19 08:43:49 2022

@author: marcnol
- This script takes JSON file with folders where datasets are
stored.
- It searches for Trace files with the expected methods, loads them, and
- combines them into a single table that is outputed to the buildPWDmatrix folder.

$ trace_combinator.py

outputs

ChromatinTraceTable() object and output .ecsv formatted file with assembled trace tables.


"""

# =============================================================================
# IMPORTS
# =============================================================================q

import numpy as np
import os, sys
import json
from datetime import datetime
import argparse
import csv
import glob

from matrixOperations.chromatin_trace_table import ChromatinTraceTable

# =============================================================================
# FUNCTIONS
# =============================================================================q


def parseArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-F", "--rootFolder", help="Folder with images")
    parser.add_argument(
        "-P", "--parameters", help="Provide name of parameter files. folders2Load.json assumed as default",
    )
    parser.add_argument("-A", "--label", help="Add name of label (e.g. doc)")
    parser.add_argument("-W", "--action", help="Select: [all], [labeled] or [unlabeled] cells plotted ")
    parser.add_argument("--saveMatrix", help="Use to load matlab formatted data", action="store_true")
    parser.add_argument("--ndims", help="Dimensions of trace")
    parser.add_argument("--method", help="Method or mask ID used for tracing: KDtree, mask, DAPI")

    p = {}

    args = parser.parse_args()
    if args.rootFolder:
        p["rootFolder"] = args.rootFolder
    else:
        p["rootFolder"] = "."

    if args.parameters:
        p["parametersFileName"] = args.parameters
    else:
        p["parametersFileName"] = "folders2Load.json"

    if args.label:
        p["label"] = args.label
    else:
        p["label"] = "M"

    if args.action:
        p["action"] = args.action
    else:
        p["action"] = "all"

    if args.saveMatrix:
        p["saveMatrix"] = True
    else:
        p["saveMatrix"] = False

    if args.ndims:
        p["ndims"] = args.ndims
    else:
        p["ndims"] = 3

    if args.method:
        p["method"] = args.method
    else:
        p["method"] = "mask"

    print("Input parameters\n" + "-" * 15)
    for item in p.keys():
        print("{}-->{}".format(item, p[item]))

    return p


def filter_trace(trace, label, action):

    rows_to_remove = list()
    number_original_traces = len(trace.data)

    # print(f"label:{label}|action:{action}")
    if "all" not in action:  # otherwise it keeps all rows

        # finds rows to remove
        for index, trace_row in enumerate(trace.data):
            labels = trace_row["label"]
            if ("unlabeled" in action) and (label in labels):
                # removes labeled
                rows_to_remove.append(index)
            elif ("labeled" in action) and ("unlabeled" not in action) and (label not in labels):
                # removes unlabeled
                rows_to_remove.append(index)

        # removes rows
        trace.data.remove_rows(rows_to_remove)

    print(
        f"> {number_original_traces-len(rows_to_remove)}/{number_original_traces} trace rows with <{label}> selected: ~{int(100*(number_original_traces-len(rows_to_remove))/number_original_traces)}%"
    )

    return trace


def load_traces(folders, ndims=3, method="mask", label="none", action="all"):

    traces = ChromatinTraceTable()
    traces.initialize()
    traces.number_traces = 0
    new_trace = ChromatinTraceTable()

    for folder in folders:
        trace_files = [x for x in glob.glob(folder.rstrip("/") + os.sep + "Trace*ecsv") if "uniqueBarcodes" not in x]
        trace_files = [x for x in trace_files if (str(ndims) + "D" in x) and (method in x)]

        print("\n{} trace files to process= {}".format(len(trace_files), "\n--> ".join(map(str, trace_files))))

        if len(trace_files) > 0:
            # iterates over traces in folder
            for trace_file in trace_files:

                # reads new trace
                new_trace.load(trace_file)

                # filters rows based on label
                new_trace = filter_trace(new_trace, label, action)

                # adds it to existing trace collection

                traces.append(new_trace.data)
                traces.number_traces += 1

    print(f"Read and accumulated {traces.number_traces} trace files with ndims = {ndims} and method = {method}")

    return traces


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    begin_time = datetime.now()

    # [parsing arguments]
    p = parseArguments()

    # [ Lists and loads datasets from different embryos]
    input_parameters = p["rootFolder"] + os.sep + p["parametersFileName"]
    print("\n" + "-" * 80)
    if os.path.exists(input_parameters):
        with open(input_parameters) as json_file:
            data_dict = json.load(json_file)
        print("Loaded JSON file with {} datasets from {}\n".format(len(data_dict), input_parameters))
    else:
        print("File not found: {}".format(input_parameters))
        sys.exit()

    # [ creates output folder]
    p["outputFolder"] = p["rootFolder"] + os.sep + "combined_traces"
    if not os.path.exists(p["outputFolder"]):
        os.mkdir(p["outputFolder"])
        print("Folder created: {}".format(p["outputFolder"]))

    # [loops over lists of datafolders]
    dataset_names = list(data_dict.keys())
    for dataset in dataset_names:
        folders = data_dict[dataset]["Folders"]
        traces = load_traces(folders, ndims=p["ndims"], method=p["method"], label=p["label"], action=p["action"])

    outputfile = (
        p["outputFolder"]
        + os.sep
        + "Trace_combined_"
        + str(p["ndims"])
        + "D_method:"
        + p["method"]
        + "_label:"
        + p["label"]
        + "_action:"
        + p["action"]
        + ".ecsv"
    )

    traces.save(outputfile, traces.data, comments="appended_trace_files=" + str(traces.number_traces))

    print("Finished execution")
