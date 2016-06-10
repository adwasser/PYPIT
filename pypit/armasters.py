import astropy.io.fits as pyfits

import armsgs
import arsave


# Logging
msgs = armsgs.get_logger()

try:
    from xastropy.xutils import xdebug as debugger
except:
    import pdb as debugger

class MasterFrames:

    def __init__(self, ndet):
        """
        A Master Calibrations class that carries the information generated for the master calibration
        """

        self._nspec    = [None for all in xrange(ndet)]   # Number of spectral pixels
        self._nspat    = [None for all in xrange(ndet)]   # Number of spatial pixels
        self._ampsec   = [None for all in xrange(ndet)]   # Locations of the amplifiers on each detector
        self._pixlocn  = [None for all in xrange(ndet)]   # Physical locations of each pixel on the detector
        self._lordloc  = [None for all in xrange(ndet)]   # Array of slit traces (left side) in physical pixel coordinates
        self._rordloc  = [None for all in xrange(ndet)]   # Array of slit traces (left side) in physical pixel coordinates
        self._pixcen   = [None for all in xrange(ndet)]   # Central slit traces in apparent pixel coordinates
        self._pixwid   = [None for all in xrange(ndet)]   # Width of slit (at each row) in apparent pixel coordinates
        self._lordpix  = [None for all in xrange(ndet)]   # Array of slit traces (left side) in apparent pixel coordinates
        self._rordpix  = [None for all in xrange(ndet)]   # Array of slit traces (right side) in apparent pixel coordinates
        self._tilts    = [None for all in xrange(ndet)]   # Array of spectral tilts at each position on the detector
        self._satmask  = [None for all in xrange(ndet)]   # Array of Arc saturation streaks
        self._arcparam = [None for all in xrange(ndet)]   #
        self._wvcalib  = [None for all in xrange(ndet)]   #
        self._resnarr  = [None for all in xrange(ndet)]   # Resolution array
        # Initialize the Master Calibration frames
        self._bpix = [None for all in xrange(ndet)]          # Bad Pixel Mask
        self._msarc = [None for all in xrange(ndet)]         # Master Arc
        self._msbias = [None for all in xrange(ndet)]        # Master Bias
        self._mstrace = [None for all in xrange(ndet)]       # Master Trace
        self._mspixflat = [None for all in xrange(ndet)]     # Master pixel flat
        self._mspixflatnrm = [None for all in xrange(ndet)]  # Normalized Master pixel flat
        self._msblaze = [None for all in xrange(ndet)]       # Blaze function
        # Initialize the Master Calibration frame names
        self._msarc_name = [None for all in xrange(ndet)]      # Master Arc Name
        self._msbias_name = [None for all in xrange(ndet)]     # Master Bias Name
        self._mstrace_name = [None for all in xrange(ndet)]    # Master Trace Name
        self._mspixflat_name = [None for all in xrange(ndet)]  # Master Pixel Flat Name


def master_name(mdir, ftype, setup):
    """ Default filenames
    Parameters
    ----------
    mdir : str
      Master directory
    ftype
    Returns
    -------
    """
    name_dict = dict(bias='{:s}/MasterBias_{:s}.fits'.format(mdir,setup),
                     badpix='{:s}/MasterBadPix_{:s}.fits'.format(mdir,setup),
                     trace='{:s}/MasterTrace_{:s}.fits'.format(mdir,setup),
                     normpixflat='{:s}/MasterFlatField_{:s}.fits'.format(mdir,setup),
                     arc='{:s}/MasterArc_{:s}.fits'.format(mdir,setup),
                     wave='{:s}/MasterWave_{:s}.fits'.format(mdir,setup),
                     wave_calib='{:s}/MasterWaveCalib_{:s}.json'.format(mdir,setup),
                     tilts='{:s}/MasterTilts_{:s}.fits'.format(mdir,setup),
                     )
    return name_dict[ftype]

'''
def load_masters(slf, det, setup):
    """ Load master frames
    Parameters
    ----------
    slf
    det
    setup
    Returns
    -------
    """
    def load_master(file, exten=0):
        hdu = pyfits.open(file)
        data = hdu[exten].data
        return data
    # Bias
    slf._msbias[det-1] = load_master(master_name('bias', setup))
    # Bad Pixel
    slf._bpix[det-1] = load_master(master_name('badpix', setup))
    # Trace
    slf._mstrace[det-1] = load_master(master_name('trace', setup))
    slf._pixcen[det-1] = load_master(master_name('trace', setup), exten=1)
    slf._pixwid[det-1] = load_master(master_name('trace', setup), exten=2)
    slf._lordpix[det-1] = load_master(master_name('trace', setup), exten=3)
    slf._rordpix[det-1] = load_master(master_name('trace', setup), exten=4)
    # Flat
    slf._mspixflatnrm[det-1] = load_master(master_name('normpixflat', setup))
    # Arc/wave
    slf._msarc[det-1] = load_master(master_name('arc', setup))
    slf._mswave[det-1] = load_master(master_name('wave', setup))
    # Tilts
    slf._tilts[det-1] = load_master(master_name('tilts', setup))
'''

def save_masters(slf, det, setup):
    """ Save Master Frames
    Parameters
    ----------
    slf
    setup
    Returns
    -------
    """
    from linetools import utils as ltu
    import io, json

    # MasterFrame directory
    mdir = slf._argflag['run']['masterdir']
    # Bias
    if 'bias'+slf._argflag['masters']['setup'] not in slf._argflag['masters']['loaded']:
        if not isinstance(slf._msbias[det-1], (basestring)):
            arsave.save_master(slf, slf._msbias[det-1],
                               filename=master_name(mdir, 'bias', setup),
                               frametype='bias')
    # Bad Pixel
    if 'badpix'+slf._argflag['masters']['setup'] not in slf._argflag['masters']['loaded']:
        arsave.save_master(slf, slf._bpix[det-1],
                               filename=master_name(mdir, 'badpix', setup),
                               frametype='badpix')
    # Trace
    if 'trace'+slf._argflag['masters']['setup'] not in slf._argflag['masters']['loaded']:
        extensions = [slf._lordloc[det-1], slf._rordloc[det-1],
                      slf._pixcen[det-1], slf._pixwid[det-1],
                      slf._lordpix[det-1], slf._rordpix[det-1]]
        arsave.save_master(slf, slf._mstrace[det-1],
                           filename=master_name(mdir, 'trace', setup),
                           frametype='trace', extensions=extensions)
    # Pixel Flat
    if 'normpixflat'+slf._argflag['masters']['setup'] not in slf._argflag['masters']['loaded']:
        arsave.save_master(slf, slf._mspixflatnrm[det-1],
                           filename=master_name(mdir, 'normpixflat', setup),
                           frametype='normpixflat')
    # Arc/Wave
    if 'arc'+slf._argflag['masters']['setup'] not in slf._argflag['masters']['loaded']:
        arsave.save_master(slf, slf._msarc[det-1],
                           filename=master_name(mdir, 'arc', setup),
                           frametype='arc', keywds=dict(transp=slf._transpose))
    if 'wave'+slf._argflag['masters']['setup'] not in slf._argflag['masters']['loaded']:
        # Wavelength image
        arsave.save_master(slf, slf._mswave[det-1],
                           filename=master_name(mdir, 'wave', setup),
                           frametype='wave')
        # Wavelength fit
        gddict = ltu.jsonify(slf._wvcalib[det-1])
        json_file=master_name(mdir, 'wave_calib', setup)
        with io.open(json_file, 'w', encoding='utf-8') as f:
            f.write(unicode(json.dumps(gddict, sort_keys=True, indent=4,
                                       separators=(',', ': '))))
    if 'tilts'+slf._argflag['masters']['setup'] not in slf._argflag['masters']['loaded']:
        arsave.save_master(slf, slf._tilts[det-1],
                           filename=master_name(mdir, 'tilts', setup),
                           frametype='tilts')

def user_master_name(mdir, input_name):
    """ Convert user-input filename for master into full name
    Mainly used to append MasterFrame directory

    Parameters
    ----------
    mdir : str
    input_name : str

    Returns
    -------
    full_name : str

    """
    islash = input_name.find('/')
    if islash >= 0:
        full_name = input_name
    else:
        full_name = mdir+'/'+input_name
    # Return
    return full_name
