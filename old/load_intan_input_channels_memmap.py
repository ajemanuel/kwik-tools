import glob
import re
import numpy as np
import sys
import os

def load_intan_input_channels(matchString='*', savePath = None):
    """
    usage:  [di,ai] = load_intan_input_channels() with ai/di files in the path
    save digital inputs
    savePath is the path where the file will be stored for memmap and future reference
    """
    if savePath == None:
        savePath = os.getcwd()
    p = re.compile('chan(\d+).di')  #extract digital input channel ids
    channel_ids = set(p.findall(' '.join(sorted(glob.glob(matchString+'.di')))))
    #load in each channel and concatenate.
    digital_inputs = {}
    for ch in channel_ids:
        files = glob.glob(matchString+'chan' + ch + '.di')
        files.sort(key=os.path.getmtime)  ## sorting based on modification time
        for f in files:
            print(f)
            if ch in digital_inputs: #concatenation used to rely on alphabetical ordering corresponding to temporal order
                digital_inputs[ch] = np.append(digital_inputs[ch],(np.fromfile(f, dtype=np.uint32)))
            else:  #load first array
                digital_inputs[ch] = np.fromfile(f, dtype=np.uint32)
    #save analog inputs
    p = re.compile('chan(\d+).ai')  #extract analog input channel ids
    channel_ids = set(p.findall(' '.join(sorted(glob.glob(matchString+'.ai')))))
    #load in each channel and concatenate.
    analog_inputs = {}
    for ch in channel_ids:
        files = glob.glob(matchString+'chan' + ch + '.ai')
        files.sort(key=os.path.getmtime)
        for f in files:
            print(f)
            if ch in analog_inputs: #load first array
                analog_inputs[ch] = np.append(analog_inputs[ch],(np.fromfile(f, dtype=np.float64)))  
            else:  #concatenation relies on alphabetical ordering corresponding to temporal order
                analog_inputs[ch] = np.fromfile(f, dtype=np.float64)
    np.save(os.path.join(savePath,'digital_inputs.npy'), digital_inputs)
    np.save(os.path.join(savePath,'analog_inputs.npy'), analog_inputs)
    
    di = np.load(savePath+'\\digital_inputs.npy',mmap_mode='r')
    ai = np.load(savePath+'\\analog_inputs.npy',mmap_mode='r')
    
    return di, ai