# A collection of analyses that I routinely perform on silicon probe recordings.

import scipy.io
import scipy.ndimage
import numpy as np
import re
import glob
import os
import matplotlib.pyplot as plt

def importJRCLUST(filepath, annotation='single', depth=250):
    """
    Imports the features of the JrClust output I use most.
    
    inputs:
        filepath - str with path to S0 filename
        annotation - str that indicates which spikes to include 'single' or 'multi'
            -- in the future, increase this functionality
        depth - int/float, depth of top electrode site, in microns (default 250 microns, my typical insertion depth of probe tip is 1100 microns)
    output: Dict with keys
        goodSpikes - ndarray of clusters (unit identities of spikes)
        goodSamples - ndarray of spike samples (time of spike)
        sampleRate - int sample rate in Hz
        goodTimes - ndarray of spike times (in s)
        unitPosXY - tuple of two ndarrays, (X center of mass, Y center of mass)
        depthIndices - index of good units in the order of their depth
        depths - depth of site (taking into account depth of probe)
        layers - the cortical layer to which the depth corresponds
    """
    outDict = {}

    S0 = scipy.io.loadmat(filepath,squeeze_me=True, struct_as_record=False)
    
    spikeAnnotations = S0['S0'].S_clu.csNote_clu
    
    try:
        annotatedUnits = np.where(spikeAnnotations == annotation)[0]+1 # +1 to account for 1-indexing of jrclust output; jrc spikes that = 0 are not classified
    except(FutureWarning):
        print('Not all units are annotated (FutureWarning triggered).')
        pass
    goodSamples = S0['S0'].viTime_spk
    goodSpikes = S0['S0'].S_clu.viClu
    
    goodSamples = goodSamples[np.isin(goodSpikes,annotatedUnits)]
    goodSpikes = goodSpikes[np.isin(goodSpikes,annotatedUnits)]
    
    
    
    outDict['sampleRate'] = S0['S0'].P.sRateHz
    outDict['goodSamples'] = goodSamples
    outDict['goodSpikes'] = goodSpikes
    outDict['goodTimes'] = goodSamples/S0['S0'].P.sRateHz
    outDict['unitPosXY'] = (S0['S0'].S_clu.vrPosX_clu[spikeAnnotations == annotation],S0['S0'].S_clu.vrPosY_clu[spikeAnnotations == annotation]) 
    outDict['depthIndices'] = np.argsort(S0['S0'].S_clu.vrPosY_clu[spikeAnnotations == annotation]) ## to get an index to use for sorting by depth
    outDict['tmrWav_raw_clu'] = np.transpose(S0['S0'].S_clu.tmrWav_raw_clu[:,:,spikeAnnotations == annotation])
    outDict['tmrWav_spk_clu'] = np.transpose(S0['S0'].S_clu.tmrWav_spk_clu[:,:,spikeAnnotations == annotation])
    
    outDict['viSite_clu'] = S0['S0'].S_clu.viSite_clu[spikeAnnotations == annotation] - 1 # subtract 1 for python indexing
    
    
    ## calculating trough to peak time
    spikeTroughPeak = []
    for i in range(len(np.unique(goodSpikes))):
        waveform = outDict['tmrWav_raw_clu'][i,outDict['viSite_clu'][i],:] ## extracts the waveform from the best spike
        spikeTroughPeak.append(np.where(waveform[12:] == np.max(waveform[12:]))[0][0]) # for raw waveforms, trough occurs at sample 12, finding location of maximum post trough
    spikeTroughPeak = np.array(spikeTroughPeak)/outDict['sampleRate'] # convert to s
    outDict['spikeTroughPeak'] = spikeTroughPeak
    
    
    ## calculating layer
    depths = outDict['unitPosXY'][1] - 150
    outDict['depths'] = depths
    layer_demarcations = -np.array([119,416.5,535.5,952]) ## from post-hoc anatomy with DAPI/layer V labeled + DiI, appears to match well with depth of Layer IV optotagged units
    layers = []
    for d in depths:
        if d > layer_demarcations[0]:
            layers.append(1)
        elif (d > layer_demarcations[1]) & (d < layer_demarcations[0]):
            layers.append(2)
        elif (d > layer_demarcations[2]) & (d < layer_demarcations[1]):
            layers.append(4)
        elif (d > layer_demarcations[3]) & (d < layer_demarcations[2]):
            layers.append(5)
        elif d < layer_demarcations[3]:
            layers.append(6)
    layers = np.array(layers)
    outDict['layers'] = layers
    
    return outDict

def importDImat(filepath, sortOption='mtime'):
    """
    Imports digital inputs saved as '*DigitalInputs.mat'
    
    input:
        filepath - str with directory containing files
        sortOption - str designating sorting method, options include 'mtime' or 'regexp'
    output:
        DI, ndarray with all digital channels
    """
    
    
    if sortOption == 'mtime':
        diFiles = glob.glob(filepath+'*DigitalInputs.mat')
        diFiles.sort(key=os.path.getmtime) # sorting by file creation time (may be problematic in mac or linux)
    elif sortOption == 'regexp':
        diFiles = glob.glob('*DigitalInputs.mat') # including full filepath results in regezp matches
        diFiles.sort(key=lambda l: grp('[0-9]*D',l)) # regular expression finding string of numbers before D
    else:
        print('Invalid sortOption')
        return -1
        
    DI = []
    
    for file in diFiles:
        print(file)
        temp = scipy.io.loadmat(file)
        
        if(temp['board_dig_in_data'].shape[0] == 1):  ## haven't checked if this works yet -- made for Anda
            tempList = [temp['board_dig_in_data'][0], np.zeros(temp['board_dig_in_data'].shape[1])]
            tempArray = np.array(tempList)
            DI.append(tempArray)
        else:
            DI.append(temp['board_dig_in_data'])
    DI = np.concatenate(DI,axis=1)
    
    return DI

def importAImat(filepath, sortOption='mtime'):
    """
    Yurika wrote this part, modified by AE 3/8/18:
    Imports analog inputs saved as '*AnalogInputs.mat'
    
    input:
        filepath - str with directory containing files
        sortOption - str designating sorting method, options include 'mtime' or 'regexp'
            if you use 'regexp' your current working diretory must include the *AnalogInputs.mat files
    output:
        AI, ndarray with all analog channels
    """
    
    if sortOption == 'mtime':
        aiFiles = glob.glob(filepath+'*AnalogInputs.mat')
        aiFiles.sort(key=os.path.getmtime) # sorting by file creation time (may be problematic in mac or linux)
    elif sortOption == 'regexp':
        aiFiles = glob.glob('*AnalogInputs.mat') # including full filepath results in regezp matches
        aiFiles.sort(key=lambda l: grp('[0-9]*D',l)) # regular expression finding string of numbers before D
    else:
        print('Invalid sortOption')
        return -1
    
    
    AI = []
    
    for file in aiFiles:
        print(file)
        temp = scipy.io.loadmat(file)
        #print(temp['board_adc_data'].shape)
        AI.append(temp['board_adc_data'])
    AI = np.concatenate(AI,axis=1)
    return AI

def plotStimRasters(stimulus, samples, spikes, unit, ltime, rtime, save=False, saveString = '',
                    baseline=0, sample_rate=20000, fig_size=(10,4),
                    heightRatio=[1,4], markerSize=3,stimLabel='Force (mN)'):
    """
    Generate plots with stimulus displayed at top and rasters below for individual units.
    
    inputs:
        stimulus - list of ndarrays, stimulus waveform
        samples - list of ndarrays, spike times in samples
        spikes - list of ndarrays, cluster identity for each spike
        unit - int, unit to include in raster
        save - boolean, save plot to disk, default=False
        baseline - float, time before first stimulus in s, default=0.0
        sample_rate - int, sample rate in Hz, default=20000
        fig_size - tuple, ratio of width to length
        heightRatio - list, ratio of heights of stimulus and raster plots
        
    generates a plot; no outputs
    """
    
    # Plot stimulus waveform
    f, (a0, a1) = plt.subplots(2,1,gridspec_kw={'height_ratios':heightRatio},figsize=fig_size)
    xaxis = np.arange(ltime-baseline,rtime-baseline,1/sample_rate)
    for sweep in stimulus:
        a0.plot(xaxis,sweep[int(sample_rate*ltime):int(sample_rate*rtime)],linewidth=.5,color='gray') # add +5*i to the y axis to get separate traces
    topxlim = a0.get_xlim()
    a0.set_title('Unit '+str(unit))
    a0.set_xticks([])
    a0.set_ylabel(stimLabel)
    
    # Plot Rasters
    for sweep in range(len(samples)):
        sweepspikes = spikes[sweep][spikes[sweep]==unit]
        sweepsamples = samples[sweep][spikes[sweep]==unit]
        sweepspikes = sweepspikes[(sweepsamples > ltime*sample_rate) & (sweepsamples < rtime*sample_rate)]
        sweepsamples = sweepsamples[(sweepsamples > ltime*sample_rate) & (sweepsamples < rtime*sample_rate)]
        a1.plot(sweepsamples/sample_rate-baseline,(sweepspikes+sweep-unit),'|',color='k',markersize=markerSize,mew=.5)
    a1.set_xlim(topxlim)
    a1.set_ylim(-1,len(samples))
    a1.set_xlabel('Time (s)')
    a1.set_ylabel('Step #')
    plt.tight_layout()

    if save:
        plt.savefig('RasterUnit'+str(unit)+saveString+'.png',dpi=300)
    plt.show()
    plt.close()    
    
def makeSweepPSTH(bin_size, samples, spikes,sample_rate=20000, units=None, duration=None, verbose=False, rate=True, bs_window=[0, 0.25]):
    """
    Use this to convert spike time rasters into PSTHs with user-defined bin
    
    inputs:
        bin_size - float, bin size in seconds
        samples - list of ndarrays, time of spikes in samples
        spikes- list of ndarrays, spike cluster identities
        sample_rate - int, Hz, default = 20000
        units - None or sequence, list of units to include in PSTH
        duration - None or float, duration of PSTH; if None, inferred from last spike
        verbose - boolean, print information about psth during calculation
        rate - boolean; Output rate (divide by bin_size and # of trials) or total spikes per trial (divide by # trials only)
        bs_window - sequence, len 2; window (in s) to use for baseline subtraction; default = [0, 0.25]
    output: dict with keys:
        psths - ndarray
        bin_size - float, same as input
        sample_rate - int, same as input
        xaxis - ndarray, gives the left side of the bins
        units - ndarray, units included in psth
    """
    
    bin_samples = bin_size * sample_rate
    
    if duration is None:
        maxBin = max(np.concatenate(samples))/sample_rate    
    else: 
        maxBin = duration
    
    if units is None:  # if user does not specify which units to use (usually done with np.unique(goodSpikes))
        units = np.unique(np.hstack(spikes))
    numUnits = len(units)
    
    psths = np.zeros([int(np.ceil(maxBin/bin_size)), numUnits])
    if verbose:
        print('psth size is',psths.shape)
    for i in range(len(samples)):
        for stepSample, stepSpike in zip(samples[i], spikes[i]):
            if stepSpike in units:
                if int(np.floor(stepSample/bin_samples)) == psths.shape[0]:
                    psths[int(np.floor(stepSample/bin_samples))-1, np.where(units == stepSpike)[0][0]] += 1 ## for the rare instance when a spike is detected at the last sample of a sweep
                else:
                    psths[int(np.floor(stepSample/bin_samples)), np.where(units == stepSpike)[0][0]] += 1
    psth_dict = {}
    if rate:
        psth_dict['psths'] = psths/bin_size/len(samples) # in units of Hz
    else:
        psth_dict['psths'] = psths/len(samples) # in units of spikes/trial in each bin
    
    psths_bs = np.copy(np.transpose(psth_dict['psths']))
    for i,psth in enumerate(psths_bs):
        tempMean = np.mean(psth[int(bs_window[0]/bin_size):int(bs_window[1]/bin_size)])
        #print(tempMean)
        psths_bs[i] = psth - tempMean
    psth_dict['psths_bs'] = np.transpose(psths_bs)
    psth_dict['bin_size'] = bin_size # in s
    psth_dict['sample_rate'] = sample_rate # in Hz
    psth_dict['xaxis'] = np.arange(0,maxBin,bin_size)
    psth_dict['units'] = units
    psth_dict['num_sweeps'] = len(samples)
    return psth_dict
    
def calcStepMetrics(psth_dict, bsMean, bsSTD, on_window=(0.25,0.3), off_window=(0.75,0.80)):
    """
    Calculate the ON and OFF responses (sum of spikes in windows) as well as ratios from PSTHs.
    Inputs:
        psth_dict - dict; from makeSweepPSTH
        bsMean - sequence; list of mean firing rate at baseline for each unit
        bsSTD - sequence; list of std of firing rate at baseline for each unit
        on_window - sequence, len 2; window for ON response
        off_window - sequence len 2; window for OFF response
    Outputs:
        response_metrics - dict; containing:
            * ON responses for each unit in psth
            * OFF responses for each unit in psth
            * ratio of OFF:ON responses for each unit in psth
    
    written by AE 3/9/2018
    """
    ## calculating parameters
    threshold = bsMean + 3 * bsSTD
    threshold[threshold<(2/psth_dict['bin_size']/psth_dict['num_sweeps'])] = 2/psth_dict['bin_size']/psth_dict['num_sweeps'] # artificial threshold requires at least two spikes in the same bin
    on_window_bins = np.int8(np.array(on_window)/psth_dict['bin_size'])
    off_window_bins = np.int8(np.array(off_window)/psth_dict['bin_size'])
    
    
    
    ## calculating metrics
    ONresponsePresent = []
    OFFresponsePresent = []
    for i,thr in enumerate(threshold):
        if np.any(psth_dict['psths'][on_window_bins[0]:on_window_bins[1],i] > thr):
            ONresponsePresent.append(True)
        else:
            ONresponsePresent.append(False)
        if np.any(psth_dict['psths'][off_window_bins[0]:off_window_bins[1],i] > thr):
            OFFresponsePresent.append(True)
        else:
            OFFresponsePresent.append(False)
    
    ON_peaks = np.max(psth_dict['psths_bs'][on_window_bins[0]:on_window_bins[1],:],axis=0)
    OFF_peaks = np.max(psth_dict['psths_bs'][off_window_bins[0]:off_window_bins[1],:],axis=0)
    ON_sums = np.sum(psth_dict['psths_bs'][on_window_bins[0]:on_window_bins[1],:],axis=0)
    OFF_sums = np.sum(psth_dict['psths_bs'][off_window_bins[0]:off_window_bins[1],:],axis=0)
    ratios_sums = OFF_sums/ON_sums
    ratios_peaks = OFF_peaks/ON_peaks
    
    ## Assigning to dictionary
    response_metrics = {}
    response_metrics['ONresponsePresent'] = ONresponsePresent
    response_metrics['OFFresponsePresent'] = OFFresponsePresent
    response_metrics['ON_peaks'] = ON_peaks
    response_metrics['OFF_peaks'] = OFF_peaks
    response_metrics['ON_sums'] = ON_sums
    response_metrics['OFF_sums'] = OFF_sums
    response_metrics['ratios_sums'] = ratios_sums
    response_metrics['ratios_peaks'] = ratios_peaks
    response_metrics['threshold'] = threshold
    return response_metrics
    
### functions regarding indentOnGrid

def plotActualPositions(filename, setup='alan', center=True, labelPositions=True, save=False):
    """
    Plot locations of grid indentation.
    
    inputs:
        filename - str, file containing indentOnGrid output
        setup - str, specifies which setup used, specified because some x and y stages are transposed
            current options: 'alan'
        center - boolean, specify whether to center grid on 0,0
        labelPositions - boolean, label order of the positions with text annotations
        save - boolean, whether to save figure as image to current path
        
    No output, generates plots.
    """
    gridIndent = scipy.io.loadmat(filename)
    try:
        gridPosActual = gridIndent['grid_positions_actual']
    except KeyError:
        print('File not from indentOnGrid')
        return -1
    gridPosActual = np.transpose(gridPosActual)
    # plotting
    if gridIndent['num_repetitions'][0][0] > 1:
        gridPosActual = gridPosActual[0] ## take only the first round for now
    
    if setup == 'alan':  # displays the points so that they match the orientation of the image. 
        xmultiplier = 1  ## my stage is not transposed in x
        ymultiplier = -1  ## my stage is transposed in y
        if center:
            xOffset = -np.median(gridPosActual[0])
            yOffset = np.median(gridPosActual[1])
        else:
            xOffset = 0
            yOffset = 0
    else:
        xmultiplier = 1
        ymultiplier = 1
        if center:
            xOffset = -((np.median(gridPosActual[0])))
            yOffset = -((np.median(gridPosActual[1])))
        else:
            xOffset = 0
            yOffset = 0
    
    f0 = plt.figure(figsize=(8,8))
    a0 = plt.axes()
    if setup == 'alan':
        a0.scatter(gridPosActual[0]*xmultiplier+xOffset,gridPosActual[1]*ymultiplier+yOffset,s=1500,marker='.')
        if labelPositions:
            for i,pos in enumerate(np.transpose(gridPosActual)):
                #print(pos)
                a0.annotate(str(i+1),(pos[0]*xmultiplier+xOffset,pos[1]*ymultiplier+yOffset),
                    horizontalalignment='center',
                    verticalalignment='center',
                    color='white',
                    weight='bold')
    else:
        a0.scatter(gridPosActual[0]*xmultiplier + xOffset, gridPosActual[1]*ymultiplier+yOffset,s=1500,marker='.')
        if labelPositions:
            for i,pos in enumerate(np.transpose(gridPosActual)):
                #print(pos)
                a0.annotate(str(i+1),(pos[0]*xmultiplier+xOffset,pos[1]*ymultiplier+yOffset),
                    horizontalalignment='center',
                    verticalalignment='center',
                    color='white',
                    weight='bold')
    
    a0.set_ylabel('mm')
    a0.set_xlabel('mm')
    a0.set_aspect('equal')
    if save:
        f0.savefig('gridPositions.png')

def plotGridResponses(filename, window, bs_window, samples, spikes,
                        goodSteps=None, units='all', numRepeats=3, numSteps=1, sampleRate=20000,
                        save=False, force=0, center=True, setup='alan',
                        doShuffle=True, numShuffles=10000, size=300, saveString=''):
    """
    Plots each unit's mechanical spatial receptive field.
    Inputs:
    filename - str; .mat filename produced by indentOnGrid
    window - sequence, len 2; start and stop of window of interest
    bs_window - sequence, len 2; start and stop of baseline window
    samples - sequence; list of samples at which spikes are detected for each sweep
    spikes - sequence; list of spike IDs corresponding to samples in goodsamples_sweeps
    goodSteps - None or sequence; list of steps to be included
    units - sequence or str; sequence of units to plot or str = 'all'
    sampleRate = int; sample rate in Hz, defaults to 20000
    saveString = string; string to add to filename, default ''
    Output is a plot.
    """
    if abs((window[1]-window[0]) - (bs_window[1] - bs_window[0])) > 1e-8: # requires some tolerance for float encoding; could also use np.isclose()
        print('Warning: Window and baseline are not same size.')
    
    gridIndent = scipy.io.loadmat(filename)
    try:
        gridPosActual = gridIndent['grid_positions_actual'] # 
        gridPosActual = np.transpose(gridPosActual)
        if gridIndent['num_repetitions'] > 1:        
            gridPosActual = gridPosActual[0] # taking the first grid positions here -- perhaps change this in the future
    except KeyError:
        print('File not from indentOnGrid')
        return -1
    
    
    gridSpikes = extractSpikesInWindow(window, samples, spikes, sampleRate=sampleRate)
    gridSpikesBS = extractSpikesInWindow(bs_window, samples, spikes, sampleRate=sampleRate)
    outDict = gridIndent # save all variables from the grid file
    numX = int((gridIndent['max_x'] - gridIndent['min_x'])/gridIndent['grid_spacing'])+1
    numY = int((gridIndent['max_y'] - gridIndent['min_y'])/gridIndent['grid_spacing'])+1
    ind = []
    for position in gridIndent['grid_positions']:
        for i, position2 in enumerate(gridIndent['grid_positions_rand']):
            if np.all(position == position2):
                ind.append(i) ## ind is a an index that can reorder the position responses for making a matrix
    if type(units) is not str: # units != 'all'
        for unit in units:
            outDict[unit] = {}
            positionResponses, positionResponsesShuffle, numGoodPositions = generatePositionResponses(gridPosActual, gridSpikes,
                                                                                                        numRepeats=numRepeats, numSteps=numSteps,
                                                                                                        unit=unit, goodSteps=goodSteps,
                                                                                                        doShuffle=doShuffle, numShuffles=numShuffles)
            
            positionResponses_baseline, positionResponseShuffle_baseline = generatePositionResponses(gridPosActual, gridSpikesBS, numRepeats=numRepeats,
                                                                                                        numSteps=numSteps, unit=unit, goodSteps=goodSteps,
                                                                                                        doShuffle=doShuffle, numShuffles=numShuffles)[:2]
            
            positionResponsesBS = {}
            for index in positionResponses:
                positionResponsesBS[index] = positionResponses[index] - positionResponses_baseline[index] ## subtract spikes in baseline window from # spikes in response window
            
            plotPositionResponses(positionResponsesBS, gridPosActual, force=force, save=save, saveString=saveString, unit=unit, center=center, setup=setup, size=size) ## edit plotPositionResponses
            
            if doShuffle:
                positionResponsesBS_shuffles = {}
                for index in positionResponsesShuffle:
                    positionResponsesBS_shuffles[index] = positionResponsesShuffle[index] - positionResponseShuffle_baseline[index] ## subtract baselines
                pValues = {}
                for index in positionResponsesBS:
                    pValues[index] = (np.sum(np.abs(positionResponsesBS_shuffles[index]) >= np.abs(positionResponsesBS[index]))+1)/numShuffles
                plotPositionResponses(pValues, gridPosActual, force=force, save=save, saveString=saveString, unit=unit, center=center, setup=setup, pValues=True,size=size)
                outDict[unit]['pValue'] = pValues
            outDict[unit]['positionResponsesBS'] = positionResponsesBS
            posResp = []
            for index in positionResponsesBS:
                posResp.append([index, positionResponsesBS[index]])
            posResp.sort(key=lambda pos: pos[0]) ## sort by position
            matrix = np.reshape(np.transpose(posResp)[1][ind],[numX,numY])
            outDict[unit]['matrix'] = np.transpose(matrix) ## this empirically matches the plotted output for my grids
    else:
        positionResponses, positionResponsesShuffle, numGoodPositions = generatePositionResponses(gridPosActual, gridSpikes, numRepeats=numRepeats, numSteps=numSteps, goodSteps=goodSteps,
                                                                                                    doShuffle=doShuffle, numShuffles=numShuffles)
        positionResponses_baseline, positionResponseShuffle_baseline = generatePositionResponses(gridPosActual, gridSpikesBS, numRepeats=numRepeats, numSteps=numSteps, goodSteps=goodSteps,
                                                                                                    doShuffle=doShuffle, numShuffles=numShuffles)[:2]
        positionResponsesBS = {}
        for index in positionResponses:
            positionResponsesBS[index] = positionResponses[index] - positionResponses_baseline[index] ## subtract spikes in baseline window from spikes in response window
        
        plotPositionResponses(positionResponsesBS, gridPosActual, force=force, save=save, saveString=saveString, center=center, setup=setup, size=size)
        outDict['all'] = {}
        outDict['all']['positionResponsesBS'] = positionResponsesBS
        
        posResp = []
        for index in positionResponsesBS:
            posResp.append([index, positionResponsesBS[index]])
        posResp.sort(key=lambda pos: pos[0]) ## sort by position
        matrix = np.reshape(np.transpose(posResp)[1][ind],[numX,numY])
        
        outDict['all']['matrix'] = np.transpose(matrix) ## this empirically matches the plotted output for my grids
    
    
    
    return outDict

def extractSpikesInWindow(window, samples, spikes, sampleRate=20000):
    """
    Inputs:
    window = sequence, len 2; start and stop of window in s
    samples = sequence; list of samples at which spikes are detected for each sweep
    spikes = sequence; list of spike IDs corresponding to samples in goodsamples_sweeps
    sampleRate = int; sample rate in Hz, defaults to 20000
    
    Returns:
    spikesOut - list of spikes in that window for each sweep
    
    """
    windowOnsetinSamples = window[0]*sampleRate # in samples
    windowDurinSamples =  (window[1]-window[0])*sampleRate # in samples
    spikesOut = []
    i = 0
    for spikeSample, spike in zip(samples,spikes):
        i += 1
        spikesOut.append((spikeSample[(spikeSample > windowOnsetinSamples) & (spikeSample < windowOnsetinSamples + windowDurinSamples)],
                         spike[(spikeSample > windowOnsetinSamples) &  (spikeSample < windowOnsetinSamples + windowDurinSamples)]))
        #plt.plot(spikeSample[(spikeSample > windowOnsetinSamples) & (spikeSample < windowOnsetinSamples + windowDurinSamples)],
        #         spike[(spikeSample > windowOnsetinSamples) & (spikeSample < windowOnsetinSamples + windowDurinSamples)],'|')
    return spikesOut

def generatePositionResponses(gridPosActual, spikes, numRepeats=3, numSteps=1, unit=None, goodSteps=None, doShuffle=True, numShuffles=10000):
    """
    Calculate the number of spikes belonging to each unit (or all units) evoked at each position. Also generate shuffled versions of these responses (for statistical analysis).
    
    Inputs:
        gridPosActual - ndarray, sequence of positions from gridIndent*[0-9].mat file generated during experiment
        spikes - list of spikes at each position
        numRepeats - int,  # of times the whole grid was repeated
        numSteps - int, # of times a step was repeated at each position of the grid
        shuffle - bool, if True, will shuffle and return positionResponseShuffle
        numShuffles - int, # of times to shuffle the positions
     
    Outpus:
        positionResponse - dict, keys refer to position indices, int values are # of spikes per good step
        positionResponseShuffle - dict, keys refer to position indices, ndarray values are arrays, len(numShuffles) of # of spikes per good step at each shuffle position
            (none if doShuffle == False)
        numGoodPositions - dict, keys refer to position indices, int values are # of steps included in that position
    """
    
    
    
    gridPosActualAll = np.transpose(gridPosActual)
    if numRepeats > 1:
        gridPosActualAll = np.matlib.repmat(gridPosActualAll,numRepeats,1)
    else:
        gridPosActualAll = np.array(gridPosActualAll)
    
    positionIndex = np.arange(len(np.transpose(gridPosActual)))
    positionIndex = np.matlib.repmat(positionIndex,numSteps,numRepeats)
    
    if numSteps > 1:
        positionIndex = np.transpose(positionIndex)
        positionIndex = positionIndex.reshape(positionIndex.shape[0]*positionIndex.shape[1]) # linearize
    if goodSteps is None:
        goodSteps = np.ones(len(spikes)) ## all steps included
    if not len(spikes) == len(positionIndex):
        print('Incorrect # of steps')
        print('len(spikes) = '+str(len(spikes)))
        print('len(positionIndex) = '+str(len(positionIndex)))
    positionResponse = {}
    numGoodPositions = {}
    
    ## Extracting Actual Responses
    if unit:
        for sweep, index, good in zip(spikes,positionIndex,goodSteps):
            if good:
                positionResponse[index] = positionResponse.get(index,0) + len(sweep[1][sweep[1]==unit])
                if index in numGoodPositions:
                    numGoodPositions[index] += 1
                else:
                    numGoodPositions[index] = 1
    else:
        for sweep, index, good in zip(spikes, positionIndex, goodSteps):
            if good:
                positionResponse[index] = positionResponse.get(index,0) + len(sweep[1])
                if index in numGoodPositions:
                    numGoodPositions[index] += 1
                else:
                    numGoodPositions[index] = 1
    for index in positionResponse:
        positionResponse[index] = positionResponse[index]/numGoodPositions[index]
    
    
    ## Extracting Shuffled Responses
    
    positionResponseShuffle  = {}
    np.random.seed(20180407) # for replicability
    if doShuffle:
        if len(positionIndex) < 20:
            if numShuffles > np.math.factorial(len(positionIndex)): ## unlikely, but just in case used a small grid
                numShuffles = np.math.factorial(len(positionIndex))
                print('numShuffles > possible permutations; assigning numShuffles to '+str(numShuffles))
        
        for shuffle in range(numShuffles):
            positionIndexShuffle = np.random.permutation(positionIndex)
            
            tempResponse = {}
            tempGoodPositions = {}
            
            if unit:
                for sweep, index, good in zip(spikes, positionIndexShuffle, goodSteps):
                    if good:
                        tempResponse[index] = positionResponse.get(index,0) + len(sweep[1][sweep[1]==unit])
                        tempGoodPositions[index] = tempGoodPositions.get(index,1) + 1   
            else:
                for sweep, index, good in zip(spikes, positionIndexShuffle, goodSteps):
                    if good:
                        tempResponse[index] = positionResponse.get(index,0) + len(sweep[1])
                        tempGoodPositions[index] = tempGoodPositions.get(index,1) + 1
            
            if shuffle == 0:
                for index in tempResponse:
                    positionResponseShuffle[index] = [tempResponse[index]/tempGoodPositions[index]] ## making lists so I can append when shuffle not 0
            else:
                for index in positionResponseShuffle:
                    positionResponseShuffle[index].append(tempResponse[index]/tempGoodPositions[index])
        
        for index in positionResponseShuffle:
            positionResponseShuffle[index] = np.array(positionResponseShuffle[index])  ## making into ndarrays
    else:
        positionResponseShuffle = None
    return positionResponse, positionResponseShuffle, numGoodPositions

def plotPositionResponses(positionResponses, gridPosActual, force=0, size=300, save=False, saveString='', unit=None, setup='alan', center=True, pValues=False):
    """
    plotting function for spatial receptive fields
    
    inputs
    positionResponses - dict, from generatePositionResponses
    force - int, in mN, for titling and savename of graph
    saveString - string, for filename saving, default ''
    output: plot
    f0 is the plot handle
    """
    if setup == 'alan': # my axes are transposed
        xmultiplier = 1
        ymultiplier = -1
        if center:
            xOffset = -int(round(np.median(gridPosActual[0])))
            #print('xOffset = {0}'.format(xOffset))
            yOffset = int(round(np.median(gridPosActual[1])))
            #print('yOffset = {0}'.format(yOffset))
        else:
            xOffset, yOffset = (0, 0)
    else:
        xmultiplier = 1
        ymultiplier = 1
        if center:
            xOffset = -np.median(gridPosActual[0])
            #print('xOffset = {0}'.format(xOffset))
            yOffset = -np.median(gridPosActual[1])
            #print('yOffset = {0}'.format(yOffset))
        else:
            xOffset, yOffset = (0, 0)
    
    positionResponse = []
    for index in positionResponses:
        positionResponse.append([index, positionResponses[index]])
    positionResponse.sort(key=lambda pos: pos[0]) ## sort by position
    
    minSpikes = min(np.transpose(positionResponse)[1])
    maxSpikes = max(np.transpose(positionResponse)[1])
    if abs(minSpikes) > abs(maxSpikes):
        absMax = abs(minSpikes)
    else:
        absMax = abs(maxSpikes)
    
    f0 = plt.figure(figsize=(6,6))
    a0 = plt.axes()
    if pValues: # plotting pValues rather than actual response
        sc = a0.scatter(gridPosActual[0][:len(positionResponse)]*xmultiplier+xOffset,gridPosActual[1][:len(positionResponse)]*ymultiplier+yOffset,c=np.transpose(np.log10(positionResponse))[1], s=size, cmap='viridis_r')
    else:
        sc = a0.scatter(gridPosActual[0][:len(positionResponse)]*xmultiplier+xOffset,gridPosActual[1][:len(positionResponse)]*ymultiplier+yOffset,c=np.transpose(positionResponse)[1], s=size, cmap='bwr', vmin=-absMax,vmax=absMax)
    a0.set_aspect('equal')
    a0.set_xlabel('mm')
    a0.set_ylabel('mm')
    if unit:
        a0.set_title('Unit %d, %d mN'%(unit, force))
    else:
        a0.set_title('{0} mN'.format(force))
    cb = f0.colorbar(sc,fraction=0.1,shrink=.5)
    if pValues:
        cb.set_label('log(p)')
    else:
        cb.set_label(r'$\Delta$ spikes per step')
    f0.tight_layout()
    if save: 
        if pValues:
            plt.savefig('positionPVALUE_unit{0}_{1}mN{2}.png'.format(unit, force, saveString),transparent=True)
        else:
            plt.savefig('positionResponse_unit{0}_{1}mN{2}.png'.format(unit, force, saveString),transparent=True)
    plt.show()
    plt.close()

### Functions for plotting responses to optical random dot patterns

def extractLaserPositions(matFile):
    """
    Calculate the positions of the stimulus at each point.
    
    input:
    matFile - str, path to file generated from stimulus
    
    output:
    positions - list of tuples containing (x, y) coordinates at each position.
    """
    
    voltageToDistance = 3.843750000000000e+03  # calibration for alan's rig with thorlabs scan mirrors
    temp = scipy.io.loadmat(matFile, variable_names=['laser','lz1','x','y'])
    try:
        laser = temp['laser']
    except(KeyError):
        laser = temp['lz1'] ## old version
    x = temp['x']
    y = temp['y']
    positions = []
    laserSamples = np.where(laser[1:] > laser[:-1])[0]
    for sample in laserSamples:
        positions.append((float(x[sample]*voltageToDistance), float(y[sample]*voltageToDistance)))
    return positions

def extractLaserPSTH(matFile, samples, spikes, sampleRate=20000):
    """
    Make lists of samples and spikes at each laser pulse
    inputs:
        matFile - str, path to file made when stimulating
        samples - sequence of spike times
        spikes - sequence of cluster identities for each spike
    outputs:
        samplesList - list of lists of spike samples after each laser pulse
        spikesList - list of lists of cluster identity corresponding to samplesList
        laserList - list of ndarrays with waveform of laser pulse command
    """
    
    
    temp = scipy.io.loadmat(matFile)
    try:
        laserOnsets = np.where(temp['laser'][1:] > temp['laser'][:-1])[0]
    except(KeyError):
        laserOnsets = np.where(temp['lz1'][1:] > temp['lz1'][:-1])[0] ### old version of stim file
    duration = temp['ISI']
    
    samplesList = []
    spikesList = []
    laserList = []
    
    for start in laserOnsets:
        adjStart = int(start * (sampleRate/temp['Fs']))
        end = int(adjStart + sampleRate * duration)
        samplesList.append(samples[(samples > adjStart) & (samples < end)] - adjStart)
        spikesList.append(spikes[(samples > adjStart) & (samples < end)])
        try:
            laserList.append(temp['laser'][start:int(start+temp['Fs']*temp['ISI'])])
        except(KeyError):
            laserList.append(temp['lz1'][start:int(start+temp['Fs']*temp['ISI'])])
    
    return samplesList, spikesList, laserList

def calcBinnedOpticalResponse(matFile, samples, spikes, binSize, window, bs_window, units, save=False, saveString='', smoothBin=0):
    """
    matFile - string, path to file generated with randSquareOffset stimulus
    samples - list, samples during stimulus
    spikes - list, cluster identities during stimulus
    binSize - float, size of spatial bin
    window - sequence, len 2 - window of analysis (in ms)
    bs_window - sequence, len 2 - spikes in this window subtracted from those in window ( in ms)
    units - sequence - units to include
    save - boolean, whether to save plot or not
    saveString - string, string appended to filename when saving
    smoothBin - float, size of gaussian filter for smoothing (in bin units), default=0, no smoothing
    """
    
    samplesList, spikesList, laserList = extractLaserPSTH(matFile, samples, spikes)
    parameters = scipy.io.loadmat(matFile, variable_names=['edgeLength','offsetX','offsetY','ISI'])
    laserPositions = np.transpose(extractLaserPositions(matFile))
    binSizeMicron = binSize * 1000
    halfEdgeLength = parameters['edgeLength']/2
    xmin = int(parameters['offsetX'] - halfEdgeLength)
    xmax = int(parameters['offsetX'] + halfEdgeLength)
    ymin = int(parameters['offsetY'] - halfEdgeLength)
    ymax = int(parameters['offsetY'] + halfEdgeLength)
    
    numBins = int(parameters['edgeLength']/binSizeMicron)
    numUnits = len(units)
    
    output = np.zeros([numBins, numBins, numUnits])
    
    for Bin in range(numBins * numBins):
        binxy = np.unravel_index(Bin,(numBins,numBins))
        tempPositions = np.where((laserPositions[0] > (xmin + binSizeMicron*binxy[0])) &
                             (laserPositions[0] < xmin + binSizeMicron*(binxy[0]+1)) &
                             (laserPositions[1] > (ymin + binSizeMicron*binxy[1])) &
                             (laserPositions[1] < ymin + binSizeMicron*(binxy[1]+1)))[0]
        if len(tempPositions > 0):
            tempPSTH = makeSweepPSTH(0.001,[samplesList[a] for a in tempPositions],[spikesList[a] for a in tempPositions],
                units=units, duration=float(parameters['ISI']), rate=False)
            
            for unit in range(numUnits):
                output[binxy[0],binxy[1],unit] = np.mean(tempPSTH['psths'][window[0]:window[1],unit]) - np.mean(tempPSTH['psths'][bs_window[0]:bs_window[1],unit])
    for unit in range(numUnits):
        if smoothBin > 0:
            output[:,:,unit] = scipy.ndimage.gaussian_filter(output[:,:,unit],smoothBin)
        plt.figure(figsize=(4,4))
        a0 = plt.axes()
        absMax = np.amax(np.absolute(output[:,:,unit]))
        sc = a0.imshow(output[:,:,unit],extent=[xmin/1000, xmax/1000, ymin/1000, ymax/1000],origin='lower',
                        clim=[-absMax,absMax],cmap='bwr')
        a0.set_title('Unit {0}'.format(units[unit]))
        a0.set_xlabel('mm')
        a0.set_ylabel('mm')
        cb = plt.colorbar(sc,fraction=.03)
        cb.set_label(r'$\Delta$ Rate (Hz)')
        plt.tight_layout()
        if save:
            plt.savefig('lasRFunit{0}{1}.png'.format(units[unit],saveString),dpi=300,transparent=True)
        plt.show()
        plt.close()
    return output

#### For Image Analysis

def createDiffLine(video, cropx1, cropx2, cropy1, cropy2):
    """
    Binarizes video and returns a frame to frame difference trace.
    Inputs:
    video - pims object
    cropx1 - int, crop pixel starting for first dimension
    cropx2 - int, crop pixel ending for first dimension
    cropy1 - int, crop pixel starting for second dimension
    cropy2 - int, crop pixel ending for second dimension
    
    Output:
    diffLine, ndarray; frame to frame differences
    """
    from skimage import filters
    threshold = filters.threshold_otsu(video[0][cropx1:cropx2,cropy1:cropy2])
    diffLine = []
    for i, image in enumerate(video):
        if i > 0:
            binary1 = image[cropx1:cropx2,cropy1:cropy2] > threshold
            binary2 = video[i-1][cropx1:cropx2,cropy1:cropy2] > threshold
            diffLine.append(np.sum(binary1 != binary2))
    diffLine = np.array(diffLine)
    diffLine = np.append(diffLine, diffLine[-1]) ## duplicate the last value to make the array the right size
    return diffLine
            
#### For PrintHead Stimulation

def randSingleAnalysis(matFile, samples, spikes, units, 
                        window=[0,25], psthSize = 1000, psthBin = 1, sampleRate=20000,verbose=True):
    """
    Generates relative spike rates in analysis window to overall mean to map out receptive fields using single indentations.
    The window is defined relative to the start of the pin in question and defaults to 25 ms.
    
    matFile - string, path to file generated with printHead singlePin stimulus
    samples - list, samples during stimulus
    spikes - list, cluster identities during stimulus
    window - sequence, len 2 - window of analysis relative to start of pin (in ms)
    units - sequence - units to include
    psthSize - float, size of psth in ms
    psthBin - float, size of bin to use in psth, in ms
    
    output - dict containing various computations
        KEYS:
        positions - positions in mm of the 24 pins
        units - same as input
        positionRepsonse - 2-dimensional ndarray - change in rate for each position (dim 1) x unit (dim 2)
        psth - dict (same as makeSweepPSTH
    """
    
    a = scipy.io.loadmat(matFile)
    
    if a['protocol'] != 'randSingle':
        print('Protocol is {0}, not "randSingle"\n'.format(a['protocol']))
        return -1
    stim = a['stim'][np.where(a['trigger']==1)[0],:] ## excluding first and last samples so that intan & matlab samples match
    psthSize_samples = int(psthSize/1000*sampleRate)
    psthBin_seconds = psthBin/1000
    window_bins = np.int32(np.array(window)/psthBin)
    
    
    output = {}
    output['units'] = units
    
    ## calculating positions (position one is furthest from rig) (in mm)
    output['positions'] = np.zeros([24,2])
    for i in range(24):
        if i % 2 != 0:
            output['positions'][i,0] = 1
        output['positions'][i,1] = (i/24)*4
    
    positionResponse = np.zeros((24, len(units)))
    for i in range(24): # for each of 24 positions
        eventStarts = np.where(stim[1:,i] > stim[:-1,i])[0]
        temp_samples = []
        temp_spikes = []
        #temp_stim = []
        for start in eventStarts:
            #temp_stim.append(stim[int(start - psthSize_samples/2):int(start+psthSize_samples/2)])
            tempStart = int(start - psthSize_samples/2)
            tempEnd = int(start + psthSize_samples/2)
            temp_samples.append(samples[(samples > tempStart) & (samples < tempEnd)] - tempStart)
            temp_spikes.append(spikes[(samples > tempStart) & (samples < tempEnd)])
        psth = makeSweepPSTH(psthBin_seconds, temp_samples, temp_spikes, units=units,duration = psthSize/1000, bs_window=[0,psthSize/1000]) # taking the mean of the overall mean of the psth window for baseline subtraction
        for j in range(len(units)):
            startBin = int(psthSize/psthBin/2)
            positionResponse[i, j] = np.nanmean(psth['psths_bs'][startBin + window_bins[0]:startBin + window_bins[1],j])
            
    output['psth'] = psth
    output['positionResponse'] = positionResponse
    return output
        
    
    
    
    
    
    
    
    
###### helper functions below

def grp(pat, txt):
    r = re.search(pat, txt)
    return r.group(0) if r else '%'