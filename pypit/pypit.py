#import matplotlib
#matplotlib.use('Agg')  # For Travis

import os
import sys
import getopt
from signal import SIGINT, signal as sigsignal
from warnings import resetwarnings, simplefilter
from time import time
import traceback

# Import PYPIT routines
import ardebug
debug = ardebug.init()
#debug['develop'] = True
#debug['arc'] = True
#debug['sky_sub'] = True
#debug['trace'] = True
#debug['obj_profile'] = True
#debug['tilts'] = True
#debug['flexure'] = True
last_updated = "2 May 2016"
version = '0.6'

try:
    from linetools.spectra.xspectrum1d import XSpectrum1D
except ImportError:
    pass

try:
    from xastropy.xutils import xdebug as debugger
except ImportError:
    import pdb as debugger


def PYPIT(redname, progname=__file__, quick=False, ncpus=1, verbose=1,
          logname=None, use_masters=False):
    """
    Main driver of the PYPIT code. Default settings and
    user-specified changes are made, and passed to the
    appropriate code for data reduction.

    Parameters
    ----------
    redname : string
      Input reduction script
    progname : string
      Name of the program
    quick : bool
      If True, a quick reduction (but possibly less
      accurate) will be performed. This flag is most
      useful for observing at a telescope, but not
      for publication quality results.
    ncpus : int
      Number of CPUs to use for multiprocessing the
      data reduction (sometimes not used)
    verbose : int (0,1,2)
      Level of verbosity:
        0 = No output
        1 = Minimal output (default - suitable for the average user)
        2 = All output
    use_masters : bool, optional
      Load calibration files from MasterFrames directory, if they exist
    logname : string
      The name of an ascii log file which is used to
      save the output details of the reduction
    ---------------------------------------------------
    """
    # Init logger
    import armsgs
    msgs = armsgs.get_logger((logname, debug, last_updated, version, verbose))
    import arload

    # First send all signals to messages to be dealt with (i.e. someone hits ctrl+c)
    sigsignal(SIGINT, msgs.signal_handler)

    # Ignore all warnings given by python
    resetwarnings()
    simplefilter("ignore")

    # Record the starting time
    tstart = time()

    # Load the input file
    parlines, datlines, spclines = arload.load_input(redname)

    # Initialize the arguments and flags
    argflag = arload.argflag_init()
    argflag['run']['ncpus'] = ncpus
    argflag['out']['verbose'] = verbose

    # Determine the name of the spectrograph
    specname = None
    for i in range(len(parlines)):
        parspl = parlines[i].split()
        if len(parspl) < 3:
            msgs.error("There appears to be a missing argument on the following input line" + msgs.newline() +
                       parlines[i])
        if (parspl[0] == 'run') and (parspl[1] == 'spectrograph'):
            specname = parspl[2]
    if specname is None:
        msgs.error("Please specify the spectrograph settings to be used with the command" + msgs.newline() +
                   "run spectrograph <name>")
    msgs.info("Reducing data from the {0:s} spectrograph".format(specname))

    # Load the Spectrograph settings
    spect = arload.load_spect(progname, specname)

    # Load default reduction arguments/flags, and set any command line arguments
    #argflag = arload.optarg(argflag, cmdlnarg, spect['mosaic']['reduction'].lower())
    # Load the default settings
    prgn_spl = progname.split('/')
    tfname = ""
    for i in range(0,len(prgn_spl)-1): tfname += prgn_spl[i]+"/"
    #fname = tfname + prgn_spl[-2] + '/settings.' + spect['mosaic']['reduction'].lower()
    fname = tfname + '/settings.' + spect['mosaic']['reduction'].lower()
    argflag = arload.load_settings(fname, argflag)
    argflag['run']['prognm'] = progname
    argflag['run']['pypitdir'] = tfname

    # Now update the settings based on the user input file
    argflag = arload.set_params(parlines, argflag, setstr="Input ")
    # Check the input file
    arload.check_argflag(argflag)

    # Load any changes to the spectrograph settings based on the user input file
    spect = arload.load_spect(progname, specname, spect=spect, lines=spclines)

    # Command line arguments
    if use_masters:
        argflag['masters']['use'] = True

    # If a quick reduction has been requested, make sure the requested pipeline
    # is the quick implementation (if it exists), otherwise run the standard pipeline.
    if quick:
        # Change to a "quick" settings file
        msgs.work("QUICK REDUCTION TO STILL BE DONE")

    # Load the important information from the fits headers
    fitsdict = arload.load_headers(argflag, spect, datlines)

    # Reduce the data!
    status = 0
    msgs.work("Make appropriate changes to quick reduction")
    if quick:
        msgs.work("define what is needed here for quick reduction")
    # Send the data away to be reduced
    if spect['mosaic']['reduction'] == 'ARMLSD':
        msgs.info("Data reduction will be performed using PYPIT-ARMLSD")
        import armlsd
        status = armlsd.ARMLSD(argflag, spect, fitsdict)
    elif spect['mosaic']['reduction'] == 'ARMED':
        msgs.info("Data reduction will be performed using PYPIT-ARMED")
        import armed
        status = armed.ARMED(argflag, spect, fitsdict)
    # Check for successful reduction
    if status == 0:
        msgs.info("Data reduction complete")
    else:
        msgs.error("Data reduction failed with status ID {0:d}".format(status))
    # Capture the end time and print it to user
    tend = time()
    codetime = tend-tstart
    if codetime < 60.0:
        msgs.info("Data reduction execution time: {0:.2f}s".format(codetime))
    elif codetime/60.0 < 60.0:
        mns = int(codetime/60.0)
        scs = codetime - 60.0*mns
        msgs.info("Data reduction execution time: {0:d}m {1:.2f}s".format(mns, scs))
    else:
        hrs = int(codetime/3600.0)
        mns = int(60.0*(codetime/3600.0 - hrs))
        scs = codetime - 60.0*mns - 3600.0*hrs
        msgs.info("Data reduction execution time: {0:d}h {1:d}m {2:.2f}s".format(hrs, mns, scs))
    return


