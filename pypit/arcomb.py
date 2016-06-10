import numpy as np
import arcycomb
import armsgs

# Logging
msgs = armsgs.get_logger()

def comb_frames(frames_arr, det, method='weightmean', spect=None, weight=None, frametype='<None>',
                rej_cosmicray=-1.0, rej_lowhigh=[0,0], rej_level=[0.0,0.0],
                sat_pix='ignore', weights=None, set_allrej='median',
                maskvalue=1048577):
    """
    Combine several frames
    frames: Array of frames to be combined
    det: int
      Detector index
    method: How to combine? Allowed values are 'mean', 'median', 'weightmean'
    weight: How to weight the combination ('counts', 'exptime', None)
    frametype: What type of frame are you combining? (only used for screen printout)
    rej_cosmicray: Sigma level to reject cosmic rays (< 0.0 means no CR removal)
    rej_lowhigh: Number of low/high pixels to reject, [low,high]
    rej_level: Rejection level (in standard deviations), where < 0.0 means no rejection [low,high]
    sat_pix: What to do with saturated pixels (options are: 'reject', 'force', 'nothing')
    set_allrej: What to do if all pixels are rejected (options are: 'min', 'max', 'mean', 'median', 'weightmean')
    maskvalue: What should the masked values be set to (should be greater than the detector's saturation value -- Default = 1 + 2**20)
    """
    ###########
    # FIRST DO SOME CHECKS ON THE INPUT
    ###########
    # Do we know the frametype?
    if frametype == 'None': msgs.warn("'frametype' is unknown for combining frames")
    # Check the number of frames
    if frames_arr is None:
        msgs.error("No '{0:s}' frames were given to comb_frames to combine".format(frametype))
    (sz_x, sz_y, num_frames) = np.shape(frames_arr)
    if num_frames == 1:
        msgs.info("Only one frame to combine!")
        msgs.info("Returning input frame")
        return frames_arr[:,:,0]
    else:
        msgs.info("Combining {0:d} {1:s} frames".format(num_frames, frametype))
    # Check if the user has allowed the combination of long and short frames (e.g. different exposure times)
    msgs.work("lscomb feature has not been included here yet...")
    # Check that the type of weights to use is given if the uses wishes to apply a weighted average
#	if method == 'weightmean' and weights == None:
#		msgs.error("You must specify the weights if you want a weighted mean combination")
    # Check the user hasn't requested to reject more frames than available
    if rej_lowhigh[0] > 0 and rej_lowhigh[1] > 0 and rej_lowhigh[0]+rej_lowhigh[1] >= num_frames:
        msgs.error("You cannot reject more frames than is available with 'rej_lowhigh'."+msgs.newline()+
                    "There are {0:d} frames and rej_lowhigh will reject {1:d} low and {2:d} high".format(num_frames, rej_lowhigh[0], rej_lowhigh[1]))
    # Check that some information on the frames was supplied
    if spect is None:
        msgs.error("When combining the {0:s} frames, spectrograph information".format(frametype)+msgs.newline()+"was not provided")
    # Calculate the values to be used if all frames are rejected in some pixels
    if set_allrej == 'min':
        allrej_arr = arcycomb.minmax(frames_arr, 0)
    elif set_allrej == 'max':
        allrej_arr = arcycomb.minmax(frames_arr, 1)
    elif set_allrej == 'mean':
        allrej_arr = arcycomb.mean(frames_arr)
    elif set_allrej == 'median':
        allrej_arr = arcycomb.median(frames_arr)
    elif set_allrej == 'weightmean':
        msgs.work("No weights are implemented yet")
        allrej_arr = arcycomb.masked_weightmean(frames_arr, maskvalue)
    elif set_allrej == 'maxnonsat':
        allrej_arr = arcycomb.maxnonsat(frames_arr, spect['det'][det-1]['saturation']*spect['det'][det-1]['nonlinear'])
    else:
        msgs.error("You must specify what to do in case all pixels are rejected")
    ################
    # Saturated Pixels
    msgs.info("Finding saturated and non-linear pixels")
    if sat_pix == 'force':
        # If a saturated pixel is in one of the frames, force them to all have saturated pixels
#		satw = np.zeros_like(frames_arr)
#		satw[np.where(frames_arr > spect['det']['saturation']*spect['det']['nonlinear'])] = 1.0
#		satw = np.any(satw,axis=2)
        setsat = arcycomb.masked_limitget(frames_arr, spect['det'][det-1]['saturation']*spect['det'][det-1]['nonlinear'], 2)
#		del satw
    elif sat_pix == 'reject':
        # Ignore saturated pixels in frames if possible
        frames_arr = arcycomb.masked_limitset(frames_arr, spect['det'][det-1]['saturation']*spect['det'][det-1]['nonlinear'], 2, maskvalue)
    elif sat_pix == 'nothing':
        # Don't do anything special for saturated pixels (Hopefully the user has specified how to deal with them below!)
        pass
    else:
        msgs.error("Option '{0:s}' for dealing with saturated pixels was not recognised".format(sat_pix))
    # Delete unecessary arrays
    # None!
    ################
    # Cosmic Rays
    if rej_cosmicray > 0.0:
        msgs.info("Rejecting cosmic rays") # Use a robust statistic
        medarr = arcycomb.masked_median(frames_arr,maskvalue)
        stdarr = 1.4826*arcycomb.masked_median(np.abs(frames_arr-medarr[:,:,np.newaxis]),maskvalue) # 1.4826 approximately converts Median Absolute Deviation to a Standard Deviation
        frames_arr = arcycomb.masked_limitsetarr(frames_arr, (medarr + rej_cosmicray*stdarr), 2, maskvalue)
        # Delete unecessary arrays
        del medarr, stdarr
    else:
        msgs.info("Not rejecting cosmic rays")
    ################
    # Low and High pixel rejection --- Masks *additional* pixels
    rejlo, rejhi = rej_lowhigh
    if rej_lowhigh[0] > 0 or rej_lowhigh[1] > 0:
        # First reject low pixels
        frames_arr = np.sort(frames_arr, axis=2)
        if rej_lowhigh[0] > 0:
            msgs.info("Rejecting {0:d} deviant low pixels".format(rej_lowhigh[0]))
            while rejlo > 0:
                xi, yi = np.indices(sz_x, sz_y)
                frames_arr[xi, yi, np.argmin(frames_arr, axis=2)] = maskvalue
                del xi, yi
                rejlo -= 1
        # Now reject high pixels
        if rej_lowhigh[1] > 0:
            msgs.info("Rejecting {0:d} deviant high pixels".format(rej_lowhigh[1]))
            frames_arr[np.where(frames_arr == maskvalue)] *= -1
            while rejhi > 0:
                xi, yi = np.indices(sz_x, sz_y)
                frames_arr[xi, yi, np.argmax(frames_arr, axis=2)] = -maskvalue
                del xi, yi
                rejhi -= 1
            frames_arr[np.where(frames_arr) == -maskvalue] *= -1
# The following is an example of *not* masking additional pixels
#		if rej_lowhigh[1] > 0:
#			msgs.info("Rejecting {0:d} deviant high pixels".format(rej_lowhigh[1]))
#			masktemp[:,:,-rej_lowhigh[0]:] = True
    else:
        msgs.info("Not rejecting any low/high pixels")
    ################
    # Deviant Pixels
    if rej_level[0] > 0.0 or rej_level[1] > 0.0:
        msgs.info("Rejecting deviant pixels") # Use a robust statistic
        medarr = arcycomb.masked_median(frames_arr, maskvalue)
        stdarr = 1.4826*arcycomb.masked_median(np.abs(frames_arr-medarr[:,:,np.newaxis]), maskvalue)  # 1.4826 approximately converts Median Absolute Deviation to a Standard Deviation
        frames_arr = arcycomb.masked_limitsetarr(frames_arr, (medarr - rej_level[0]*stdarr), -2, maskvalue)
        frames_arr = arcycomb.masked_limitsetarr(frames_arr, (medarr + rej_level[1]*stdarr), 2, maskvalue)
        # Delete unecessary arrays
        del medarr, stdarr
    else:
        msgs.info("Not rejecting deviant pixels")
    ##############
    # Combine the arrays
    msgs.info("Combining frames with a {0:s} operation".format(method))
    if method == 'mean':
        frames_arr = arcycomb.masked_mean(frames_arr, maskvalue)
    elif method == 'median':
        frames_arr = arcycomb.masked_median(frames_arr, maskvalue)
    elif method == 'weightmean':
        frames_arr = arcycomb.masked_weightmean(frames_arr, maskvalue)
    else:
        msgs.error("Combination type '{0:s}' is unknown".format(method))
    ##############
    # If any pixels are completely masked, apply user-specified function
    msgs.info("Replacing completely masked pixels with the {0:s} value of the input frames".format(set_allrej))
    frames_arr = arcycomb.masked_replace(frames_arr, allrej_arr, maskvalue)
    # Delete unecessary arrays
    del allrej_arr
    ##############
    # Apply the saturated pixels:
    if sat_pix == 'force':
        msgs.info("Applying saturated pixels to final combined image")
        frames_arr[setsat] = spect['det'][det]['saturation']
    ##############
    # And return a 2D numpy array
    msgs.info("{0:d} {1:s} frames combined successfully!".format(num_frames,frametype))
    # Make sure the returned array is the correct type
    frames_arr = np.array(frames_arr, dtype=np.float)
    return frames_arr
