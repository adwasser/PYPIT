import numpy as np
from scipy import ndimage
from scipy import interpolate

from linetools.spectra import xspectrum1d
from astropy.io import fits
from astropy import units as u

import ararc
import arextract
import armsgs
import arutils

# Logging
msgs = armsgs.get_logger()

try:
    from xastropy.xutils import xdebug as debugger
except:
    import pdb as debugger


def flex_shift(slf, det, obj_skyspec, arx_skyspec):
    """ Calculate shift between object sky spectrum and archive sky spectrum

    Parameters
    ----------
    slf
    det
    obj_skyspec
    arx_skyspec

    Returns
    -------
    flex_dict
    """
    #Determine the brightest emission lines
    msgs.warn("If we use Paranal, cut down on wavelength early on")
    arx_amp, arx_cent, arx_wid, arx_w, arx_satsnd, arx_yprep = ararc.detect_lines(slf, det, msarc=None, censpec=arx_skyspec.flux.value, MK_SATMASK=False)
    obj_amp, obj_cent, obj_wid, obj_w, obj_satsnd, obj_yprep = ararc.detect_lines(slf, det, msarc=None, censpec=obj_skyspec.flux.value, MK_SATMASK=False)

    #Keep only 5 brightest amplitude lines (xxx_keep is array of indices within arx_w of the 5 brightest)
    arx_keep = np.argsort(arx_amp[arx_w])[-5:]
    obj_keep = np.argsort(obj_amp[obj_w])[-5:]

    #Calculate wavelength (Angstrom per pixel)
    arx_disp = np.append(arx_skyspec.wavelength.value[1]-arx_skyspec.wavelength.value[0],
                         arx_skyspec.wavelength.value[1:]-arx_skyspec.wavelength.value[:-1])
    #arx_disp = (np.amax(arx_sky.wavelength.value)-np.amin(arx_sky.wavelength.value))/arx_sky.wavelength.size
    obj_disp = np.append(obj_skyspec.wavelength.value[1]-obj_skyspec.wavelength.value[0],
                         obj_skyspec.wavelength.value[1:]-obj_skyspec.wavelength.value[:-1])
    #obj_disp = (np.amax(obj_sky.wavelength.value)-np.amin(obj_sky.wavelength.value))/obj_sky.wavelength.size

    #Calculate resolution (lambda/delta lambda_FWHM)..maybe don't need this? can just use sigmas
    arx_idx = (arx_cent+0.5).astype(np.int)[arx_w][arx_keep]   # The +0.5 is for rounding
    arx_res = arx_skyspec.wavelength.value[arx_idx]/\
              (arx_disp[arx_idx]*(2*np.sqrt(2*np.log(2)))*arx_wid[arx_w][arx_keep])
    obj_idx = (obj_cent+0.5).astype(np.int)[obj_w][obj_keep]   # The +0.5 is for rounding
    obj_res = obj_skyspec.wavelength.value[obj_idx]/ \
              (obj_disp[obj_idx]*(2*np.sqrt(2*np.log(2)))*obj_wid[obj_w][obj_keep])
    #obj_res = (obj_sky.wavelength.value[0]+(obj_disp*obj_cent[obj_w][obj_keep]))/(
    #    obj_disp*(2*np.sqrt(2*np.log(2)))*obj_wid[obj_w][obj_keep])
    msgs.info("Resolution of Archive={:g} and Observation={:g}".format(
        np.median(arx_res), np.median(obj_res)))

    #Determine sigma of gaussian for smoothing
    arx_sig2 = (arx_disp[arx_idx]*arx_wid[arx_w][arx_keep])**2.
    obj_sig2 = (obj_disp[obj_idx]*obj_wid[obj_w][obj_keep])**2.

    arx_med_sig2 = np.median(arx_sig2)
    obj_med_sig2 = np.median(obj_sig2)

    if obj_med_sig2 >= arx_med_sig2:
        smooth_sig = np.sqrt(obj_med_sig2-arx_med_sig2)  # Ang
        smooth_sig_pix = smooth_sig / np.median(arx_disp[arx_idx])
    else:
        msgs.warn("Prefer archival sky spectrum to have higher resolution")
        smooth_sig_pix = 0.
        #smooth_sig = np.sqrt(arx_med_sig**2-obj_med_sig**2)

    #Determine region of wavelength overlap
    min_wave = max(np.amin(arx_skyspec.wavelength.value), np.amin(obj_skyspec.wavelength.value))
    max_wave = min(np.amax(arx_skyspec.wavelength.value), np.amax(obj_skyspec.wavelength.value))

    #Smooth higher resolution spectrum by smooth_sig (flux is conserved!)
    if np.median(obj_res) >= np.median(arx_res):
        msgs.warn("New Sky has higher resolution than Archive.  Not smoothing")
        #obj_sky_newflux = ndimage.gaussian_filter(obj_sky.flux, smooth_sig)
    else:
        #tmp = ndimage.gaussian_filter(arx_sky.flux, smooth_sig)
        arx_skyspec = arx_skyspec.gauss_smooth(smooth_sig_pix*2*np.sqrt(2*np.log(2)))
        #arx_sky.flux = ndimage.gaussian_filter(arx_sky.flux, smooth_sig)

    # Define wavelengths of overlapping spectra
    keep_idx = np.where((obj_skyspec.wavelength.value>=min_wave) &
                         (obj_skyspec.wavelength.value<=max_wave))[0]
    #keep_wave = [i for i in obj_sky.wavelength.value if i>=min_wave if i<=max_wave]

    #Rebin both spectra onto overlapped wavelength range
    if len(keep_idx) <= 50:
        msgs.error("Not enough overlap between sky spectra")

    else: #rebin onto object ALWAYS
        keep_wave = obj_skyspec.wavelength[keep_idx]
        arx_skyspec = arx_skyspec.rebin(keep_wave)
        obj_skyspec = obj_skyspec.rebin(keep_wave)

    #deal with bad pixels
    msgs.work("Need to mask bad pixels")

    #deal with underlying continuum
    msgs.work("Need to deal with underlying continuum")

    #Cross correlation of spectra
    corr = np.correlate(arx_skyspec.flux, obj_skyspec.flux, "same")

    #Create array around the max of the correlation function for fitting for subpixel max
    # Restrict to pixels within max_shift of zero lag
    lag0 = corr.size/2
    mxshft = slf._argflag['reduce']['flexure']['max_shift']
    max_corr = np.argmax(corr[lag0-mxshft:lag0+mxshft]) + lag0-mxshft
    subpix_grid = np.linspace(max_corr-3., max_corr+3., 7.)

    #Fit a 2-degree polynomial to peak of correlation function
    fit = arutils.func_fit(subpix_grid, corr[subpix_grid.astype(np.int)], 'polynomial', 2)
    max_fit = -0.5*fit[1]/fit[2]

    #Calculate and apply shift in wavelength
    shift = float(max_fit)-lag0
    msgs.info("Flexure correction of {:g} pixels".format(shift))
    #model = (fit[2]*(subpix_grid**2.))+(fit[1]*subpix_grid)+fit[0]

    if msgs._debug['flexure']:
        debugger.xplot(arx_skyspec.wavelength, arx_skyspec.flux, xtwo=obj_skyspec.wavelength, ytwo=obj_skyspec.flux)
        #debugger.xplot(arx_sky.wavelength, arx_sky.flux, xtwo=np.roll(obj_sky.wavelength.value,9), ytwo=obj_sky.flux*100)
        debugger.set_trace()

    flex_dict = dict(polyfit=fit, shift=shift, subpix=subpix_grid,
                     corr=corr[subpix_grid.astype(np.int)],
                     sky_spec=obj_skyspec,
                     arx_spec=arx_skyspec,
                     corr_cen=corr.size/2, smooth=smooth_sig_pix)
    # Return
    return flex_dict


def flexure_archive(slf, det):
    """  Load archived sky spectrum
    Parameters
    ----------
    slf
    det

    Returns
    -------

    """
    #   latitude = slf._spect['mosaic']['latitude']
    #   longitude = slf._spect['mosaic']['longitude']
    root = slf._argflag['run']['pypitdir']
    if slf._argflag['reduce']['flexure']['archive_spec'] is None:
        # Red or blue?
        if slf._argflag['run']['spectrograph'] in ['kast_blue', 'lris_blue']:
            skyspec_fil = 'sky_kastb_600.fits'
        else:
            skyspec_fil = 'paranal_sky.fits'
    else:
        skyspec_fil = slf._argflag['reduce']['flexure']['archive_spec']
    #
    msgs.info("Using {:s} file for Sky spectrum".format(skyspec_fil))
    arx_sky = xspectrum1d.XSpectrum1D.from_file(root+'/data/sky_spec/'+skyspec_fil)
    #hdu = fits.open(root+'/data/sky_spec/'+skyspec_fil)
    #archive_wave = hdu[0].data
    #archive_flux = hdu[1].data
    #arx_sky = xspectrum1d.XSpectrum1D.from_tuple((archive_wave, archive_flux))
    # Return
    return skyspec_fil, arx_sky


def flexure_slit(slf, det):
    """Correct wavelength down slit center for flexure

    Parameters:
    ----------
    slf :
    det : int
    """
    # Load Archive
    skyspec_fil, arx_sky = flexure_archive(slf, det)

    # Extract
    censpec_wv = arextract.boxcar_cen(slf, det, slf._mswave[det-1])
    censpec_fx = arextract.boxcar_cen(slf, det, slf._bgframe[det-1])
    cen_sky = xspectrum1d.XSpectrum1D.from_tuple((censpec_wv, censpec_fx))
    # Find shift
    fdict = flex_shift(slf, det, cen_sky, arx_sky)
    msgs.work("Flexure shift = {:g} down slit center".format(fdict['shift']))
    # Refit
    #  What if xfit shifts outside of 0-1?
    xshift = fdict['shift']/(slf._msarc[det-1].shape[0]-1)
    mask, fit = arutils.robust_polyfit(np.array(slf._wvcalib[det-1]['xfit'])+xshift,
                                       np.array(slf._wvcalib[det-1]['yfit']),
                                       len(slf._wvcalib[det-1]['fitc']),
                                       function=slf._wvcalib[det-1]['function'], sigma=slf._wvcalib[det-1]['nrej'], minv=slf._wvcalib[det-1]['fmin'], maxv=slf._wvcalib[det-1]['fmax'])
    # Update wvcalib
    slf._wvcalib[det-1]['shift'] = fdict['shift']  # pixels
    slf._wvcalib[det-1]['fitc'] = fit
    msgs.work("Add another QA for wavelengths?")
    # Update mswave
    wv_calib = slf._wvcalib[det-1]
    slf._mswave[det-1] = arutils.func_val(wv_calib['fitc'], slf._tilts[det-1], wv_calib['function'], minv=wv_calib['fmin'], maxv=wv_calib['fmax'])
    # Write to Masters?  Not for now
    # For QA (kludgy..)
    censpec_wv = arextract.boxcar_cen(slf, det, slf._mswave[det-1])
    fdict['sky_spec'] = xspectrum1d.XSpectrum1D.from_tuple((censpec_wv, censpec_fx))
    flex_dict = dict(polyfit=[], shift=[], subpix=[], corr=[],
                     corr_cen=[], spec_file=skyspec_fil, smooth=[],
                     arx_spec=[], sky_spec=[])
    #debugger.set_trace()
    #debugger.xplot(censpec_wv, censpec_fx, xtwo=fdict['arx_spec'].wavelength, ytwo=fdict['arx_spec'].flux*50)
    for key in ['polyfit', 'shift', 'subpix', 'corr', 'corr_cen', 'smooth', 'sky_spec', 'arx_spec']:
        flex_dict[key].append(fdict[key])
    return flex_dict


def flexure_obj(slf, det):
    """Correct wavelengths for flexure

    Parameters:
    ----------
    slf :
    det : int
      detector number
    center : bool, optional
      Extract arc down the center?

    Returns:
    ----------
    flex_dict: dict
      dict on flexure results

    """
    msgs.work("Consider doing 2 passes in flexure as in LowRedux")
    # Load Archive
    skyspec_fil, arx_sky = flexure_archive(slf, det)

    # Loop on objects
    flex_dict = dict(polyfit=[], shift=[], subpix=[], corr=[],
                     corr_cen=[], spec_file=skyspec_fil, smooth=[],
                     arx_spec=[], sky_spec=[])

    for specobj in slf._specobjs[det-1]:  # for convenience

        # Using boxcar
        if slf._argflag['reduce']['flexure']['spec'] in ['boxcar', 'slit_cen']:
            sky_wave = specobj.boxcar['wave'].to('AA').value
            sky_flux = specobj.boxcar['sky']
        else:
            msgs.error("Not ready for this flexure method: {}".format(
                    slf._argflag['reduce']['flexure']))

        # Generate 1D spectrum for object
        obj_sky = xspectrum1d.XSpectrum1D.from_tuple((sky_wave, sky_flux))

        # Calculate the shift
        fdict = flex_shift(slf, det, obj_sky, arx_sky)

        # Simple interpolation to apply
        npix = len(sky_wave)
        x = np.linspace(0., 1., npix)
        # Apply
        for attr in ['boxcar', 'optimal']:
            if not hasattr(specobj,attr):
                continue
            if 'wave' in getattr(specobj, attr).keys():
                msgs.info("Applying flexure correction to {:s} extraction for object {:s}".format(
                    attr, str(specobj)))
                f = interpolate.interp1d(x, sky_wave, bounds_error=False, fill_value="extrapolate")
                getattr(specobj, attr)['wave'] = f(x+fdict['shift']/(npix-1))*u.AA
        # Shift sky spec too
        cut_sky = fdict['sky_spec']
        x = np.linspace(0., 1., cut_sky.npix)
        f = interpolate.interp1d(x, cut_sky.wavelength.value, bounds_error=False, fill_value="extrapolate")
        twave = f(x+fdict['shift']/(cut_sky.npix-1))*u.AA
        new_sky = xspectrum1d.XSpectrum1D.from_tuple((twave, cut_sky.flux))

        # Update dict
        for key in ['polyfit','shift','subpix','corr','corr_cen', 'smooth', 'arx_spec']:
            flex_dict[key].append(fdict[key])
        flex_dict['sky_spec'].append(new_sky)

    return flex_dict


def airtovac(wave):
    """Convert air-based wavelengths to vacuum

    Parameters:
    ----------
    wave: Quantity array
      Wavelengths 

    Returns:
    ----------
    wave: Quantity array
      Wavelength array corrected to vacuum wavelengths
    """
    # Convert to AA
    wave = wave.to(u.AA)
    wavelength = wave.value

    # Standard conversion format
    sigma_sq = (1.e4/wavelength)**2. #wavenumber squared
    factor = 1 + (5.792105e-2/(238.0185-sigma_sq)) + (1.67918e-3/(57.362-sigma_sq))
    factor = factor*(wavelength>=2000.) + 1.*(wavelength<2000.) #only modify above 2000A

    # Convert
    wavelength = wavelength*factor
    # Units
    new_wave = wavelength*u.AA
    new_wave.to(wave.unit)

    return new_wave

def vactoair(wave):
    """Convert to air-based wavelengths from vacuum

    Parameters:
    ----------
    wave: Quantity array
      Wavelengths 

    Returns:
    ----------
    wave: Quantity array
      Wavelength array corrected to air
    """
    # Convert to AA
    wave = wave.to(u.AA)
    wavelength = wave.value

    # Standard conversion format
    sigma_sq = (1.e4/wavelength)**2. #wavenumber squared
    factor = 1 + (5.792105e-2/(238.0185-sigma_sq)) + (1.67918e-3/(57.362-sigma_sq))
    factor = factor*(wavelength>=2000.) + 1.*(wavelength<2000.) #only modify above 2000A

    # Convert
    wavelength = wavelength/factor
    new_wave = wavelength*u.AA
    new_wave.to(wave.unit)

    return new_wave