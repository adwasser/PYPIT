from matplotlib import pyplot as plt
import numpy as np
import armsgs
import arutils
from arplot import get_dimen as get_dimen

# Logging
msgs = armsgs.get_logger()

def basis(xfit, yfit, coeff, npc, pnpc, weights=None, skipx0=True, x0in=None, mask=None, function='polynomial', retmask=False):
    nrow = xfit.shape[0]
    ntrace = xfit.shape[1]
    if x0in is None:
        x0in = np.arange(float(ntrace))

    # Mask out some orders if they are bad
    if mask is None or mask.size == 0:
        usetrace = np.arange(ntrace)
        outmask = np.ones((nrow, ntrace))
    else:
        usetrace = np.where(np.in1d(np.arange(ntrace), mask) == False)[0]
        outmask = np.ones((nrow, ntrace))
        outmask[:,mask] = 0.0

    # Do the PCA analysis
    eigc, hidden = get_pc(coeff[1:npc+1, usetrace], npc)

    modl = arutils.func_vander(xfit[:,0], function, npc)
    eigv = np.dot(modl[:,1:], eigc)

    med_hidden = np.median(hidden, axis=1)
    med_highorder = med_hidden.copy()
    med_highorder[0] = 0

    high_order_matrix = med_highorder.T[np.newaxis,:].repeat(ntrace, axis=0)

    # y = hidden[0,:]
    # coeff0 = arutils.robust_regression(x0in[usetrace], y, pnpc[1], 0.1, function=function)

    # y = hidden[1,:]
    # coeff1 = arutils.robust_regression(x0in[usetrace], y, pnpc[2], 0.1, function=function)

    coeffstr = []
    for i in xrange(1, npc+1):
        # if pnpc[i] == 0:
        #     coeffstr.append([-9.99E9])
        #     continue
        # coeff0 = arutils.robust_regression(x0in[usetrace], hidden[i-1,:], pnpc[i], 0.1, function=function, min=x0in[0], max=x0in[-1])
        if weights is not None:
            tmask, coeff0 = arutils.robust_polyfit(x0in[usetrace], hidden[i-1,:], pnpc[i],
                                                   weights=weights[usetrace], sigma=2.0, function=function,
                                                   minv=x0in[0], maxv=x0in[-1])
        else:
            tmask, coeff0 = arutils.robust_polyfit(x0in[usetrace], hidden[i-1,:], pnpc[i],
                                                   sigma=2.0, function=function, minv=x0in[0], maxv=x0in[-1])
        coeffstr.append(coeff0)
        high_order_matrix[:,i-1] = arutils.func_val(coeff0, x0in, function, minv=x0in[0], maxv=x0in[-1])
    # high_order_matrix[:,1] = arutils.func_val(coeff1, x0in, function)
    high_fit = high_order_matrix.copy()

    high_order_fit = np.dot(eigv, high_order_matrix.T)
    sub = (yfit - high_order_fit) * outmask

    numer = np.sum(sub, axis=0)
    denom = np.sum(outmask, axis=0)
    x0 = np.zeros(float(ntrace))
    fitmask = np.zeros(float(ntrace))
    #fitmask[mask] = 1
    x0fit = np.zeros(float(ntrace))
    chisqnu = 0.0
    chisqold = 0.0
    robust = True
    #svx0 = numer/(denom+(denom == 0).astype(np.int))
    if not skipx0:
        fitmask = (np.abs(denom) > 10).astype(np.int)
        if robust:
            good = np.where(fitmask != 0)[0]
            bad = np.where(fitmask == 0)[0]
            x0[good] = numer[good]/denom[good]
            imask = np.zeros(float(ntrace))
            imask[bad] = 1.0
            ttmask, x0res = arutils.robust_polyfit(x0in, x0, pnpc[0], weights=weights, sigma=2.0,
                                                   function=function, minv=x0in[0], maxv=x0in[-1], initialmask=imask)
            x0fit = arutils.func_val(x0res, x0in, function, minv=x0in[0], maxv=x0in[-1])
            good = np.where(ttmask == 0)[0]
            xstd = 1.0  # This should represent the dispersion in the fit
            chisq = ((x0[good]-x0fit[good])/xstd)**2.0
            chisqnu = np.sum(chisq)/np.sum(ttmask)
            fitmask = 1.0-ttmask
            msgs.prindent("  Reduced chi-squared = {0:E}".format(chisqnu))
        else:
            for i in xrange(1, 5):
                good = np.where(fitmask != 0)[0]
                x0[good] = numer[good]/denom[good]
#				x0res = arutils.robust_regression(x0in[good],x0[good],pnpc[0],0.2,function=function)
                x0res = arutils.func_fit(x0in[good], x0[good], function, pnpc[0],
                                         weights=weights, minv=x0in[0], maxv=x0in[-1])
                x0fit = arutils.func_val(x0res, x0in, function, minv=x0in[0], maxv=x0in[-1])
                chisq = (x0[good]-x0fit[good])**2.0
                fitmask[good] *= (chisq < np.sum(chisq)/2.0).astype(np.int)
                chisqnu = np.sum(chisq)/np.sum(fitmask)
                msgs.prindent("  Reduced chi-squared = {0:E}".format(chisqnu))
                if chisqnu == chisqold:
                    break
                else:
                    chisqold = chisqnu
        if chisqnu > 2.0:
            msgs.warn("PCA has very large residuals")
        elif chisqnu > 0.5:
            msgs.warn("PCA has fairly large residuals")
        #bad = np.where(fitmask==0)[0]
        #x0[bad] = x0fit[bad]
    else:
        x0res = 0.0
    x3fit = np.dot(eigv,high_order_matrix.T) + np.outer(x0fit,np.ones(nrow)).T
    outpar = dict({'high_fit': high_fit, 'x0': x0, 'x0in': x0in, 'x0fit': x0fit, 'x0res': x0res, 'x0mask': fitmask,
                   'hidden': hidden, 'usetrc': usetrace, 'eigv': eigv, 'npc': npc, 'coeffstr': coeffstr})
    if retmask:
        return x3fit, outpar, tmask
    else:
        return x3fit, outpar


def do_pca(data, cov=False):
    tolerance = 1.0E-5
    Nobj, Mattr = data.shape

    if cov:
        colmean = (np.sum(data,0)/Nobj)[:,np.newaxis]
        temp = np.ones((Nobj,1))
        X = data - np.dot(temp,colmean.T)
    else:
        msgs.bug("PCA without cov=True is not implemented")
        msgs.error("Unable to continue")
    A = np.dot(X.T,X)
    eigva, eigve = np.linalg.eig(A)
    indx = np.where(np.abs(eigva) <= tolerance*np.max(eigva))[0]
    if np.size(indx) != 0: eigva[indx] = 0.0
    indx = np.where(np.abs(eigve) <= tolerance*np.max(eigve))[0]
    if np.size(indx) != 0: eigve[indx] = 0.0

    # Sort by increasing eigenvalue
    indx = np.argsort(eigva)
    eigva = eigva[indx]
    eigve = eigve[:,indx]
    eigva = eigva[::-1]
    eigve = eigve.T[::-1,:]

    return eigva, eigve


def extrapolate(outpar, ords, function='polynomial'):
    nords = ords.size

    x0ex = arutils.func_val(outpar['x0res'], ords, function,
                            minv=outpar['x0in'][0], maxv=outpar['x0in'][-1])

    # Order centre
    high_matr = np.zeros((nords, outpar['npc']))
    for i in xrange(1, outpar['npc']+1):
        if outpar['coeffstr'][i-1][0] == -9.99E9:
            high_matr[:,i-1] = np.ones(nords)*outpar['high_fit'][0,i-1]
            continue
        high_matr[:,i-1] = arutils.func_val(outpar['coeffstr'][i-1], ords, function,
                                            minv=outpar['x0in'][0], maxv=outpar['x0in'][-1])
    extfit = np.dot(outpar['eigv'], high_matr.T) + np.outer(x0ex, np.ones(outpar['eigv'].shape[0])).T
    outpar['high_matr'] = high_matr
    return extfit, outpar


def refine_iter(outpar, orders, mask, irshft, relshift, fitord, function='polynomial'):
    fail = False
    x0ex = arutils.func_val(outpar['x0res'], orders, function,  minv=outpar['x0in'][0], maxv=outpar['x0in'][-1])
    # Make the refinement
    x0ex[irshft] += relshift
    # Refit the data to improve the refinement
    good = np.where(mask != 0.0)[0]
#	x0res = arutils.robust_regression(x0in[good],x0[good],pnpc[0],0.2,function=function)
    null, x0res = arutils.robust_polyfit(orders[good], x0ex[good], fitord, sigma=2.0, function=function,
                                         minv=outpar['x0in'][0], maxv=outpar['x0in'][-1])
    #x0res = arutils.func_fit(orders[good], x0ex[good], function, fitord, min=outpar['x0in'][0], max=outpar['x0in'][-1])
    x0fit = arutils.func_val(x0res, orders, function, minv=outpar['x0in'][0], maxv=outpar['x0in'][-1])
    chisq = (x0ex[good]-x0fit[good])**2.0
    chisqnu = np.sum(chisq)/np.sum(mask)
    msgs.prindent("  Reduced chi-squared = {0:E}".format(chisqnu))
    if chisqnu > 0.5: # The refinement went wrong, ignore the refinement
        fail = True
    outpar['x0res'] = x0res
    extfit = np.dot(outpar['eigv'], outpar['high_matr'].T) + np.outer(x0fit, np.ones(outpar['eigv'].shape[0])).T
    return extfit, outpar, fail


def get_pc(data, k, tol=0.0, maxiter=20, nofix=False, noortho=False):

    p = data.shape[0]
    if p == 0:
        msgs.error("You need to supply more components in the PCA")
    #n = np.size(data)/p
    if k > p:
        msgs.error("The number of principal components must be less than or equal" + msgs.newline() +
                   "to the order of the fitting function")

    # Set the initial conditions
    eigv = np.zeros((p, k))
    eigv[:k, :k] = np.identity(k)

    niter = 0
    diff = tol*2.0 + 1.0

    while (niter < maxiter) and (diff > tol):
        hidden = np.dot(np.dot(np.linalg.inv(np.dot(eigv.T, eigv)), eigv.T), data)
        oldeigv = eigv.copy()
        eigv = np.dot(data, np.dot(hidden.T, np.linalg.inv(np.dot(hidden, hidden.T))))
        if tol > 0.0:
            diff = 0.0
            for i in xrange(k):
                diff += np.abs( 1.0 - np.sum(oldeigv[:,i]*eigv[:,i])/np.sqrt(np.sum(oldeigv[:,i]**2)*np.sum(eigv[:,i]**2)) )
        niter += 1

    # Orthonormalize?
    if not noortho:
        for b in xrange(k):
            # Orthogonalize
            for bp in xrange(b):
                dot = np.sum(eigv[:,b]*eigv[:,bp])
                eigv[:,b] -= dot*eigv[:,bp]
            # Normalize
            dot = np.sum(eigv[:,b]**2)
            dot = 1.0/np.sqrt(dot)
            eigv[:,b] *= dot
        # Project variables onto new coordinates?
        if not nofix:
            hidden = np.dot(eigv.T, data)
            eval_hidden, evec_hidden = do_pca(hidden.T, cov=True)
            eigv = np.dot(eigv, evec_hidden.T)
        hidden = np.dot(eigv.T, data)
    return eigv, hidden

################################################
# 2D Image PCA

def image_basis(img, numpc=0):
    """
    img is a masked array
    numpc is the number of principal components
    """
    # Compute the eigenvalues and eigenvectors of the covariance matrix
    # First, subtract the median (along the spatial direction)
    #imgmed = (img.data - img.mean(axis=1).data.reshape((img.data.shape[0],1))).T
    imgmed = (img.data - np.median(img.data,axis=1).reshape((img.data.shape[0],1))).T
    imgmed[np.where(img.mask.T)] = 0.0
    eigval, eigvec = np.linalg.eig(np.cov(imgmed))
    p = np.size(eigvec, axis=1)
    # Sort the eigenvalues in ascending order
    idx = np.argsort(eigval,kind='mergesort')
    idx = idx[::-1]
    # Sort eigenvectors according to the sorted eigenvalues
    eigvec = eigvec[:, idx]
    eigval = eigval[idx]
    # Select the first few principal components
    if (numpc < p) and (numpc >= 0):
        eigvec = eigvec[:,range(numpc)]
    # Project the data
    imgmed[np.where(img.mask.T)] = 0.0
    score = np.dot(eigvec.T, imgmed)
    return eigvec, eigval, score


def pca2d(img, numpc, mask=None, maskval=-999999.9):
    img = img.T
    # Check if the number of principle components is within bounds
    if (numpc<0) or (numpc > img.shape[0]): numpc = img.shape[0]/2
    # Obtain the principal components
    if mask is None:
        mask = np.zeros_like(img)
        mask[np.where(img == maskval)] = 1
    mimg = np.ma.array(img, mask=mask)
    eigvec, eigval, score = image_basis(mimg, numpc)
    # Reconstruct the image
    imgpca = np.dot(eigvec, score).T + mimg.mean(axis=0).data
    return imgpca.astype(np.float).T


################################################

def pc_plot(slf, inpar, ofit, maxp=25, pcadesc="", addOne=True):
    """
    Saves quality control plots for a PCA analysis
    """
    npc = inpar['npc']+1
    pages, npp = get_dimen(npc, maxp=maxp)
    x0 = inpar['x0']
    ordernum = inpar['x0in']
    x0fit = inpar['x0fit']
    usetrc = inpar['usetrc']
    hidden = inpar['hidden']
    high_fit = inpar['high_fit']
    nc = np.max(ordernum[usetrc])
    # Loop through all pages and plot the results
    ndone = 0
    for i in xrange(len(pages)):
        plt.clf()
        f, axes = plt.subplots(pages[i][1], pages[i][0])
        ipx, ipy = 0, 0
        if i == 0:
            if pages[i][1] == 1: ind = (0,)
            elif pages[i][0] == 1: ind = (0,)
            else: ind = (0,0)
            axes[ind].plot(ordernum[usetrc], x0[usetrc], 'bx')
            axes[ind].plot(ordernum, x0fit, 'k-')
            amn, amx = np.min(x0fit), np.max(x0fit)
            diff = x0[usetrc]-x0fit[usetrc]
            tdiffv = np.median(diff)
            mdiffv = 1.4826*np.median(np.abs(tdiffv-diff))
            amn -= 2.0*mdiffv
            amx += 2.0*mdiffv
            mval = amn-0.15*(amx-amn)
            dmin, dmax = tdiffv-2.0*mdiffv, tdiffv+2.0*mdiffv
            diff = mval + diff*0.20*(amx-amn)/(dmax-dmin)
            wign = np.where(np.abs(diff-np.median(diff))<4.0*1.4826*np.median(np.abs(diff-np.median(diff))))[0]
            dmin, dmax = np.min(diff[wign]), np.max(diff[wign])
            axes[ind].plot(ordernum[usetrc], diff, 'rx')
            if addOne:
                axes[ind].plot([0, nc+1], [mval,mval], 'k-')
                axes[ind].axis([0, nc+1, dmin-0.5*(dmax-dmin), amx + 0.05*(amx-amn)])
            else:
                axes[ind].plot([0, nc], [mval, mval], 'k-')
                axes[ind].axis([0, nc, dmin-0.5*(dmax-dmin), amx + 0.05*(amx-amn)])
            axes[ind].set_title("Mean Value")
            ipx += 1
            if ipx == pages[i][0]:
                ipx = 0
                ipy += 1
            npp[0] -= 1
        for j in xrange(npp[i]):
            if pages[i][1] == 1: ind = (ipx,)
            elif pages[i][0] == 1: ind = (ipy,)
            else: ind = (ipy, ipx)
            axes[ind].plot(ordernum[usetrc], hidden[j+ndone,:], 'bx')
            axes[ind].plot(ordernum, high_fit[:,j+ndone], 'k-')
            vmin, vmax = np.min(hidden[j+ndone,:]), np.max(hidden[j+ndone,:])
            if ofit[1+j+ndone] != -1:
                cmn, cmx = np.min(high_fit[:,j+ndone]), np.max(high_fit[:,j+ndone])
                diff = hidden[j+ndone,:]-high_fit[:,j+ndone][usetrc]
                tdiffv = np.median(diff)
                mdiffv = 1.4826*np.median(np.abs(tdiffv-diff))
                cmn -= 2.0*mdiffv
                cmx += 2.0*mdiffv
                mval = cmn-0.15*(cmx-cmn)
                dmin, dmax = tdiffv-2.0*mdiffv, tdiffv+2.0*mdiffv
                #dmin, dmax = np.min(diff), np.max(diff)
                diff = mval + diff*0.20*(cmx-cmn)/(dmax-dmin)
                wign = np.where(np.abs(diff-np.median(diff))<4.0*1.4826*np.median(np.abs(diff-np.median(diff))))[0]
                dmin, dmax = np.min(diff[wign]), np.max(diff[wign])
                #vmin, vmax = np.min(hidden[j+ndone,:][wign]), np.max(hidden[j+ndone,:][wign])
                axes[ind].plot(ordernum[usetrc], diff, 'rx')
                axes[ind].plot([0, 1+nc], [mval, mval], 'k-')
#				ymin = np.min([(3.0*dmin-dmax)/2.0,vmin-0.1*(vmax-dmin),dmin-0.1*(vmax-dmin)])
#				ymax = np.max([np.max(high_fit[:,j+ndone]),vmax+0.1*(vmax-dmin),dmax+0.1*(vmax-dmin)])
                ymin = dmin-0.5*(dmax-dmin)
                ymax = cmx + 0.05*(cmx-cmn)
                if addOne: axes[ind].axis([0, nc+1, ymin, ymax])
                else: axes[ind].axis([0, nc, ymin, ymax])
            else:
                if addOne: axes[ind].axis([0, nc+1, vmin-0.1*(vmax-vmin), vmax+0.1*(vmax-vmin)])
                else: axes[ind].axis([0, nc, vmin-0.1*(vmax-vmin), vmax+0.1*(vmax-vmin)])
            axes[ind].set_title("PC {0:d}".format(j+ndone))
            ipx += 1
            if ipx == pages[i][0]:
                ipx = 0
                ipy += 1
        if i == 0: npp[0] = npp[0] + 1
        # Delete the unnecessary axes
        for j in xrange(npp[i], axes.size):
            if pages[i][1] == 1: ind = (ipx,)
            elif pages[i][0] == 1: ind = (ipy,)
            else: ind = (ipy, ipx)
            f.delaxes(axes[ind])
            if ipx == pages[i][0]:
                ipx = 0
                ipy += 1
        ndone += npp[i]
        # Save the figure
        if pages[i][1] == 1 or pages[i][0] == 1: ypngsiz = 11.0/axes.size
        else: ypngsiz = 11.0*axes.shape[0]/axes.shape[1]
        f.set_size_inches(11.0, ypngsiz)
        if pcadesc != "":
            pgtxt = ""
            if len(pages) != 1:
                pgtxt = ", page {0:d}/{1:d}".format(i+1, len(pages))
            f.suptitle(pcadesc + pgtxt, y=1.02, size=16)
        f.tight_layout()
        slf._qa.savefig(dpi=200, orientation='landscape', bbox_inches='tight')
        plt.close()
        f.clf()
    del f
    return


def pc_plot_arctilt(tiltang, centval, tilts, plotsdir="Plots", pcatype="<unknown>", maxp=25, prefix=""):
    """
    Saves a few output png files of the PCA analysis for the arc tilts
    """
    npc = tiltang.shape[1]
    pages, npp = get_dimen(npc,maxp=maxp)
    x0=np.arange(tilts.shape[0])
    # First calculate the min and max values for the plotting axes, to make sure they are all the same
    ymin, ymax = None, None
    for i in xrange(npc):
        w = np.where(tiltang[:,i]!=-999999.9)
        if np.size(w[0]) == 0: continue
        medv = np.median(tiltang[:,i][w])
        madv = 1.4826*np.median(np.abs(medv-tiltang[:,i][w]))
        vmin, vmax = medv-3.0*madv, medv+3.0*madv
        tymin = min(vmin,np.min(tilts[:,i]))
        tymax = max(vmax,np.max(tilts[:,i]))
        if ymin is None: ymin = tymin
        else:
            if tymin < ymin: ymin = tymin
        if ymax is None: ymax = tymax
        else:
            if tymax > ymax: ymax = tymax
    # Check that ymin and ymax are set, if not, return without plotting
    if ymin is None or ymax is None:
        msgs.warn("Arc tilt fits were not plotted")
        return
    # Generate the plots
    ndone=0
    for i in xrange(len(pages)):
        f, axes = plt.subplots(pages[i][1], pages[i][0])
        ipx, ipy = 0, 0
        for j in xrange(npp[i]):
            if pages[i][1] == 1: ind = (ipx)
            elif pages[i][0] == 1: ind = (ipy)
            else: ind = (ipy,ipx)
            w = np.where(tiltang[:,ndone]!=-999999.9)
            if np.size(w[0]) != 0:
                axes[ind].plot(centval[:,ndone][w],tiltang[:,ndone][w],'bx')
                axes[ind].plot(x0,tilts[:,ndone],'r-')
            axes[ind].axis([0,tilts.shape[0]-1,ymin,ymax])
            axes[ind].set_title("Order {0:d}".format(1+ndone))
            ipx += 1
            if ipx == pages[i][0]:
                ipx = 0
                ipy += 1
            ndone += 1
        # Delete the unnecessary axes
        for j in xrange(npp[i],axes.size):
            if pages[i][1] == 1: ind = (ipx)
            elif pages[i][0] == 1: ind = (ipy)
            else: ind = (ipy,ipx)
            f.delaxes(axes[ind])
            if ipx == pages[i][0]:
                ipx = 0
                ipy += 1
        # Save the figure
        if pages[i][1] == 1 or pages[i][0] == 1: ypngsiz = 11.0/axes.size
        else: ypngsiz = 11.0*axes.shape[0]/axes.shape[1]
        f.set_size_inches(11.0, ypngsiz)
        f.tight_layout()
        if prefix != "":
            f.savefig("{0:s}/{1:s}_PCA_arc{2:s}_page-{3:d}.png".format(plotsdir,prefix,pcatype,i+1), dpi=200, orientation='landscape')
        else:
            f.savefig("{0:s}/PCA_arc{1:s}_page-{2:d}.png".format(plotsdir,pcatype,i+1), dpi=200, orientation='landscape')
    f.clf()
    del f
    return


def pc_plot_extcenwid(tempcen, cenwid, binval, plotsdir="Plots", pcatype="<unknown>", maxp=25, prefix=""):
    """
    Saves a few output png files of the PCA analysis for the target centroid/width definition
    """
    npc = tempcen.shape[1]
    pages, npp = get_dimen(npc,maxp=maxp)
    x0=binval*np.arange(cenwid.shape[0])
    # First calculate the min and max values for the plotting axes, to make sure they are all the same
    ymin, ymax = None, None
    """
    for i in xrange(npc):
        w = np.where(tempcen[:,i]!=-999999.9)
        if np.size(w[0]) == 0: continue
        medv = np.median(tempcen[:,i][w])
        madv = 1.4826*np.median(np.abs(medv-tempcen[:,i][w]))
        vmin, vmax = medv-3.0*madv, medv+3.0*madv
        tymin = min(vmin,np.min(cenwid[:,i]))
        tymax = max(vmax,np.max(cenwid[:,i]))
        if ymin is None: ymin = tymin
        else:
            if tymin < ymin: ymin = tymin
        if ymax is None: ymax = tymax
        else:
            if tymax > ymax: ymax = tymax
    """
    w = np.where(tempcen!=-999999.9)
    if np.size(w[0]) != 0:
        medv = np.median(tempcen[w])
        madv = 1.4826*np.median(np.abs(medv-tempcen[w]))
        vmin, vmax = medv-3.0*madv, medv+3.0*madv
        tymin = min(vmin,np.min(cenwid))
        tymax = max(vmax,np.max(cenwid))
        if ymin is None: ymin = tymin
        else:
            if tymin < ymin: ymin = tymin
        if ymax is None: ymax = tymax
        else:
            if tymax > ymax: ymax = tymax

    # Check that ymin and ymax are set, if not, return without plotting
    if ymin is None or ymax is None:
        msgs.warn("{0:s} fits were not plotted".format(pcatype))
        return
    # Generate the plots
    ndone=0
    for i in xrange(len(pages)):
        f, axes = plt.subplots(pages[i][1], pages[i][0])
        ipx, ipy = 0, 0
        for j in xrange(npp[i]):
            if pages[i][1] == 1: ind = (ipx)
            elif pages[i][0] == 1: ind = (ipy)
            else: ind = (ipy,ipx)
            w = np.where(tempcen[:,ndone]!=-999999.9)
            if np.size(w[0]) != 0:
                rowplt = binval*(0.5 + np.arange(tempcen.shape[0]))
                axes[ind].plot(rowplt[w],tempcen[:,ndone][w],'bx')
                axes[ind].plot(x0,cenwid[:,ndone],'r-')
            axes[ind].axis([0,binval*tempcen.shape[0],ymin,ymax])
            axes[ind].set_title("Order {0:d}".format(1+ndone))
            ipx += 1
            if ipx == pages[i][0]:
                ipx = 0
                ipy += 1
            ndone += 1
        # Delete the unnecessary axes
        for j in xrange(npp[i],axes.size):
            if pages[i][1] == 1: ind = (ipx)
            elif pages[i][0] == 1: ind = (ipy)
            else: ind = (ipy,ipx)
            f.delaxes(axes[ind])
            if ipx == pages[i][0]:
                ipx = 0
                ipy += 1
        # Save the figure
        if pages[i][1] == 1 or pages[i][0] == 1: ypngsiz = 11.0/axes.size
        else: ypngsiz = 11.0*axes.shape[0]/axes.shape[1]
        f.set_size_inches(11.0, ypngsiz)
        f.tight_layout()
        if prefix != "":
            f.savefig("{0:s}/{1:s}_PCA_{2:s}_page-{3:d}.png".format(plotsdir,prefix,pcatype,i+1), dpi=200, orientation='landscape')
        else:
            f.savefig("{0:s}/PCA_{1:s}_page-{2:d}.png".format(plotsdir,pcatype,i+1), dpi=200, orientation='landscape')
    f.clf()
    del f
    return