.. highlight:: rest

**********************
Wavelength Calibration
**********************


Basic Algorithms
================

These notes will describe the algorithms used to perform
wavelength calibration with PYPIT.

Validation
==========

See the iPython Notebook under test_suite for a comparison of the
wavelength solution for PYPIT vs. LowRedux.

Adding a new grating to existing instrument
===========================================
This section describes how to add a new
wavelength solution for a new instrument and/or
grating.

Open ararc.py to add information to an already
existing instrument.

In the method setup_param, add the new disperser to the
list, under the appropriate instrument. In setup_param,
all the defaults for all instruments and gratings are listed
first:

    # Defaults
    arcparam = dict(llist='',
        disp=0.,           # Ang/unbinned pixel
        b1=0.,               # Pixel fit term (binning independent)
        b2=0.,               # Pixel fit term
        wvmnx=[2900.,12000.],# Guess at wavelength range
        disp_toler=0.1,      # 10% tolerance
        match_toler=3.,      # Matcing tolerance (pixels)
        func='legendre',     # Function for fitting
        n_first=1,           # Order of polynomial for first fit
        n_final=4,           # Order of polynomial for final fit
        nsig_rej=2.,         # Number of sigma for rejection
        nsig_rej_final=3.0,  # Number of sigma for rejection (final fit)
        Nstrong=13)          # Number of lines for auto-analysis

Find the instrument you'd like to add a grating to. For
example, to add the 1200/5000 grating to KAST red, the
section of interest would be:

    elif sname=='kast_red':
        lamps = ['HgI','NeI','ArI']
        #arcparam['llist'] = slf._argflag['run']['pypitdir'] + 'data/arc_lines/kast_red.lst'

And the following lines should be added:

        elif disperser == '1200/5000':
            arcparam['disp']=1.17 # This information is on the instrument's website
            arcparam['b1']= 1./arcparam['disp']/slf._msarc[det-1].shape[0]
            arcparam['wvmnx'][1] = 5000. # This is a guess at max wavelength covered
            arcparam['n_first']=2 # Should be able to lock on

Now in armlsd.py, put a stop after wavelength calibration
to check that the arc lines were correctly identified for
this new disperser. To do this, in method ARMLSD, find:

                # Extract arc and identify lines
                wv_calib = ararc.simple_calib(slf, det)
                slf.SetFrame(slf._wvcalib, wv_calib, det)
                slf._qa.close()
                debugger.set_trace()

Note that the last two lines were added so that the QA
plots can be correctly closed, and the process stopped.
Run PYPIT, and check in the QA plots that the arc lines
identified by PYPIT are consistent with a pre-existing
arc line mapping, and you're done!

Flexure
=======

By default, the code will calculate a flexure shift based on the
extracted sky spectrum (boxcar).  A cross-correlation between this
sky spectrum and an archived spectrum is performed to calculate
a single, pixel shift.  This is then imposed on the wavelength solution
with simple linear interpolation.

An alternate algorithm (reduce flexure spec slit_cen) measures the
flexure from a sky spectrum extracted down the center of the slit.
This is then imposed on the wavelength image so that any extractions
that follow have a flexure correction already applied.  Thus far, this
algorithm has given poorer results than the default.

Blue Spectra
++++++++++++

Presently, we are finding that the sky spectrum at Mauna Kea (measured
with LRIS) is sufficiently variable that a robust solution is challenging.
Fair results are achieved by using the instrument-specific sky spectra
in the LowRedux package.  There is a script pyp_compare_sky.py that
allows the user to plot their extracted sky spectrum against any of
the ones in the PYPIT archive (in data/sky_spec).  Best practice
currently is to use the one that best matches as an optional parameter
in the .pypit reduction file, e.g.::

    reduce flexure archive_spec sky_LRISb_400.fits


Settings File
=============
