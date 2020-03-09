import sys
import os
import time

import numpy as np
from numpy.lib.recfunctions import append_fields
import fitsio

from astropy.time import Time
import sep

from trm.pgplot import *
import hipercam as hcam
from hipercam import core, cline, utils, spooler, defect
from hipercam.cline import Cline
from hipercam.extraction import findStars

__all__ = ['ftargets',]

########################################################
#
# ftargets --uses sep to find targets in a set of images
#
########################################################

def ftargets(args=None):
    """``ftargets [source device width height] (run first [twait tmax] |
    flist) trim ([ncol nrow]) (ccd (nx)) [pause] thresh output bias
    flat msub iset (ilo ihi | plo phi) xlo xhi ylo yhi``

    Plots a sequence of images, runs source extraction on them, 
    save results to disk.

    Parameters:

        source : string [hidden]
           Data source, five options:

             |  'hs' : HiPERCAM server
             |  'hl' : local HiPERCAM FITS file
             |  'us' : ULTRACAM server
             |  'ul' : local ULTRACAM .xml/.dat files
             |  'hf' : list of HiPERCAM hcm FITS-format files

           'hf' is used to look at sets of frames generated by 'grab' or
           converted from foreign data formats.

        device : string [hidden]
          Plot device. PGPLOT is used so this should be a PGPLOT-style name,
          e.g. '/xs', '1/xs' etc. At the moment only ones ending /xs are
          supported.

        width : float [hidden]
           plot width (inches). Set = 0 to let the program choose.

        height : float [hidden]
           plot height (inches). Set = 0 to let the program choose. BOTH width
           AND height must be non-zero to have any effect

        run : string [if source ends 's' or 'l']
           run number to access, e.g. 'run034'

        flist : string [if source ends 'f']
           name of file list

        first : int [if source ends 's' or 'l']
           exposure number to start from. 1 = first frame; set = 0 to always
           try to get the most recent frame (if it has changed).  For data
           from the |hiper| server, a negative number tries to get a frame not
           quite at the end.  i.e. -10 will try to get 10 from the last
           frame. This is mainly to sidestep a difficult bug with the
           acquisition system.

        twait : float [if source ends 's' or 'l'; hidden]
           time to wait between attempts to find a new exposure, seconds.

        tmax : float [if source ends 's' or 'l'; hidden]
           maximum time to wait between attempts to find a new exposure,
           seconds.

        trim : bool [if source starts with 'u']
           True to trim columns and/or rows off the edges of windows nearest
           the readout which can sometimes contain bad data.

        ncol : int [if trim, hidden]
           Number of columns to remove (on left of left-hand window, and right
           of right-hand windows)

        nrow : int [if trim, hidden]
           Number of rows to remove (bottom of windows)

        ccd : string
           CCD(s) to plot, '0' for all, '1 3' to plot '1' and '3' only, etc.

        nx : int [if more than 1 CCD]
           number of panels across to display.

        pause : float [hidden]
           seconds to pause between frames (defaults to 0)

        thresh : float
           threshold (mutiple of RMS) to use for object detection. Typical
           values 2.5 to 4. The higher it is, the fewer objects will be located,
           but the fewer false detections will be made.

        fwhm : float
           FWHM to use for smoothing during object detection. Should be
           comparable to the seeing.

        minpix : int
           Minimum number of pixels above threshold before convolution to count
           as a detection. Useful in getting rid of cosmics and high dark count
           pixels.

        bias : string
           Name of bias frame to subtract, 'none' to ignore.

        flat : string
           Name of flat field to divide by, 'none' to ignore. Should normally
           only be used in conjunction with a bias, although it does allow you
           to specify a flat even if you haven't specified a bias.

        output: string
           Name of file for storage of results. Will be a fits file, with
           results saved to the HDU 1 as a table.

        iset : string [single character]
           determines how the intensities are determined. There are three
           options: 'a' for automatic simply scales from the minimum to the
           maximum value found on a per CCD basis. 'd' for direct just takes
           two numbers from the user. 'p' for percentile dtermines levels
           based upon percentiles determined from the entire CCD on a per CCD
           basis.

        ilo : float [if iset='d']
           lower intensity level

        ihi : float [if iset='d']
           upper intensity level

        plo : float [if iset='p']
           lower percentile level

        phi : float [if iset='p']
           upper percentile level

        xlo : float
           left-hand X-limit for plot

        xhi : float
           right-hand X-limit for plot (can actually be < xlo)

        ylo : float
           lower Y-limit for plot

        yhi : float
           upper Y-limit for plot (can be < ylo)

    """

    command, args = utils.script_args(args)

    # get the inputs
    with Cline('HIPERCAM_ENV', '.hipercam', command, args) as cl:

        # register parameters
        cl.register('source', Cline.GLOBAL, Cline.HIDE)
        cl.register('device', Cline.LOCAL, Cline.HIDE)
        cl.register('width', Cline.LOCAL, Cline.HIDE)
        cl.register('height', Cline.LOCAL, Cline.HIDE)
        cl.register('run', Cline.GLOBAL, Cline.PROMPT)
        cl.register('first', Cline.LOCAL, Cline.PROMPT)
        cl.register('trim', Cline.GLOBAL, Cline.PROMPT)
        cl.register('ncol', Cline.GLOBAL, Cline.HIDE)
        cl.register('nrow', Cline.GLOBAL, Cline.HIDE)
        cl.register('twait', Cline.LOCAL, Cline.HIDE)
        cl.register('tmax', Cline.LOCAL, Cline.HIDE)
        cl.register('flist', Cline.LOCAL, Cline.PROMPT)
        cl.register('ccd', Cline.LOCAL, Cline.PROMPT)
        cl.register('nx', Cline.LOCAL, Cline.PROMPT)
        cl.register('pause', Cline.LOCAL, Cline.HIDE)
        cl.register('thresh', Cline.LOCAL, Cline.PROMPT)
        cl.register('fwhm', Cline.LOCAL, Cline.PROMPT)
        cl.register('minpix', Cline.LOCAL, Cline.PROMPT)
        cl.register('bias', Cline.GLOBAL, Cline.PROMPT)
        cl.register('flat', Cline.GLOBAL, Cline.PROMPT)
        cl.register('output', Cline.LOCAL, Cline.PROMPT)
        cl.register('iset', Cline.GLOBAL, Cline.PROMPT)
        cl.register('ilo', Cline.GLOBAL, Cline.PROMPT)
        cl.register('ihi', Cline.GLOBAL, Cline.PROMPT)
        cl.register('plo', Cline.GLOBAL, Cline.PROMPT)
        cl.register('phi', Cline.LOCAL, Cline.PROMPT)
        cl.register('xlo', Cline.GLOBAL, Cline.PROMPT)
        cl.register('xhi', Cline.GLOBAL, Cline.PROMPT)
        cl.register('ylo', Cline.GLOBAL, Cline.PROMPT)
        cl.register('yhi', Cline.GLOBAL, Cline.PROMPT)

        # get inputs
        source = cl.get_value('source', 'data source [hs, hl, us, ul, hf]',
                              'hl', lvals=('hs','hl','us','ul','hf'))

        # set some flags
        server_or_local = source.endswith('s') or source.endswith('l')

        # plot device stuff
        device = cl.get_value('device', 'plot device', '1/xs')
        width = cl.get_value('width', 'plot width (inches)', 0.)
        height = cl.get_value('height', 'plot height (inches)', 0.)

        if server_or_local:
            resource = cl.get_value('run', 'run name', 'run005')
            if source == 'hs':
                first = cl.get_value('first', 'first frame to plot', 1)
            else:
                first = cl.get_value('first', 'first frame to plot', 1, 0)

            twait = cl.get_value(
                'twait', 'time to wait for a new frame [secs]', 1., 0.)
            tmax = cl.get_value(
                'tmax', 'maximum time to wait for a new frame [secs]', 10., 0.)

        else:
            resource = cl.get_value(
                'flist', 'file list', cline.Fname('files.lis',hcam.LIST)
            )
            first = 1

        trim = cl.get_value(
            'trim', 'do you want to trim edges of windows?',
            True
        )
        if trim:
            ncol = cl.get_value(
                'ncol', 'number of columns to trim from windows', 0)
            nrow = cl.get_value(
                'nrow', 'number of rows to trim from windows', 0)

        # define the panel grid. first get the labels and maximum dimensions
        ccdinf = spooler.get_ccd_pars(source, resource)

        try:
            nxdef = cl.get_default('nx')
        except:
            nxdef = 3

        if len(ccdinf) > 1:
            ccd = cl.get_value('ccd', 'CCD(s) to plot [0 for all]', '0')
            if ccd == '0':
                ccds = list(ccdinf.keys())
            else:
                ccds = ccd.split()
                check = set(ccdinf.keys())
                if not set(ccds) <= check:
                    raise hcam.HipercamError(
                        'At least one invalid CCD label supplied'
                    )

            if len(ccds) > 1:
                nxdef = min(len(ccds), nxdef)
                cl.set_default('nx', nxdef)
                nx = cl.get_value('nx', 'number of panels in X', 3, 1)
            else:
                nx = 1
        else:
            nx = 1
            ccds = list(ccdinf.keys())

        cl.set_default('pause', 0.)
        pause = cl.get_value(
            'pause', 'time delay to add between'
            ' frame plots [secs]', 0., 0.
        )

        thresh = cl.get_value(
            'thresh', 'source detection threshold [RMS]', 3.
        )
        fwhm = cl.get_value(
            'fwhm', 'FWHM for source detection [binned pixels]', 4.
        )
        minpix = cl.get_value(
            'minpix', 'minimum number of pixels above threshold (no convolution)', 3
        )

        # bias frame (if any)
        bias = cl.get_value(
            'bias', "bias frame ['none' to ignore]",
            cline.Fname('bias', hcam.HCAM), ignore='none'
        )
        if bias is not None:
            # read the bias frame
            bias = hcam.MCCD.read(bias)
            fprompt = "flat frame ['none' to ignore]"
        else:
            fprompt = "flat frame ['none' is normal choice with no bias]"

        # flat (if any)
        flat = cl.get_value(
            'flat', fprompt,
            cline.Fname('flat', hcam.HCAM), ignore='none'
        )
        if flat is not None:
            # read the flat frame
            flat = hcam.MCCD.read(flat)

        output = cl.get_value(
            'output', "output file for results",
            cline.Fname('sources', hcam.SEP, cline.Fname.NEW),
        )

        iset = cl.get_value(
            'iset', 'set intensity a(utomatically),'
            ' d(irectly) or with p(ercentiles)?',
            'a', lvals=['a','d','p'])
        iset = iset.lower()

        plo, phi = 5, 95
        ilo, ihi = 0, 1000
        if iset == 'd':
            ilo = cl.get_value('ilo', 'lower intensity limit', 0.)
            ihi = cl.get_value('ihi', 'upper intensity limit', 1000.)
        elif iset == 'p':
            plo = cl.get_value('plo', 'lower intensity limit percentile',
                               5., 0., 100.)
            phi = cl.get_value('phi', 'upper intensity limit percentile',
                               95., 0., 100.)

        # region to plot
        for i, cnam in enumerate(ccds):
            nxtot, nytot, nxpad, nypad = ccdinf[cnam]
            if i == 0:
                xmin, xmax = float(-nxpad), float(nxtot + nxpad + 1)
                ymin, ymax = float(-nypad), float(nytot + nypad + 1)
            else:
                xmin = min(xmin, float(-nxpad))
                xmax = max(xmax, float(nxtot + nxpad + 1))
                ymin = min(ymin, float(-nypad))
                ymax = max(ymax, float(nytot + nypad + 1))

        xlo = cl.get_value('xlo', 'left-hand X value', xmin, xmin, xmax)
        xhi = cl.get_value('xhi', 'right-hand X value', xmax, xmin, xmax)
        ylo = cl.get_value('ylo', 'lower Y value', ymin, ymin, ymax)
        yhi = cl.get_value('yhi', 'upper Y value', ymax, ymin, ymax)


    ################################################################
    #
    # all the inputs have now been obtained. Get on with doing stuff

    # open image plot device
    imdev = hcam.pgp.Device(device)
    if width > 0 and height > 0:
        pgpap(width,height/width)

    # set up panels and axes
    nccd = len(ccds)
    ny = nccd // nx if nccd % nx == 0 else nccd // nx + 1

    # slice up viewport
    pgsubp(nx,ny)

    # plot axes, labels, titles. Happens once only
    for cnam in ccds:
        pgsci(hcam.pgp.Params['axis.ci'])
        pgsch(hcam.pgp.Params['axis.number.ch'])
        pgenv(xlo, xhi, ylo, yhi, 1, 0)
        pglab('X','Y','CCD {:s}'.format(cnam))

    # initialisations. 'last_ok' is used to store the last OK frames of each
    # CCD for retrieval when coping with skipped data.

    total_time = 0 # time waiting for new frame

    nhdu = len(ccds)*[0]
    thetas = np.linspace(0,2*np.pi,100)

    # open the output file for results
    with fitsio.FITS(output, 'rw', clobber=True) as fout:

        # plot images
        with spooler.data_source(source, resource, first, full=False) as spool:

            # 'spool' is an iterable source of MCCDs
            n = 0
            for nf, mccd in enumerate(spool):

                if server_or_local:
                    # Handle the waiting game ...
                    give_up, try_again, total_time = spooler.hang_about(
                        mccd, twait, tmax, total_time
                    )

                    if give_up:
                        print('ftargets stopped')
                        break
                    elif try_again:
                        continue

                # Trim the frames: ULTRACAM windowed data has bad columns
                # and rows on the sides of windows closest to the readout
                # which can badly affect reduction. This option strips
                # them.
                if trim:
                    hcam.ccd.trim_ultracam(mccd, ncol, nrow)

                # indicate progress
                tstamp = Time(mccd.head['TIMSTAMP'], format='isot', precision=3)
                print(
                    '{:d}, utc= {:s} ({:s}), '.format(
                        mccd.head['NFRAME'], tstamp.iso,
                        'ok' if mccd.head.get('GOODTIME', True) else 'nok'),
                    end=''
                )

                # accumulate errors
                emessages = []

                if n == 0:
                    if bias is not None:
                        # crop the bias on the first frame only
                        bias = bias.crop(mccd)

                    if flat is not None:
                        # crop the flat on the first frame only
                        flat = flat.crop(mccd)

                # display the CCDs chosen
                message = ''
                pgbbuf()
                for nc, cnam in enumerate(ccds):
                    ccd = mccd[cnam]

                    if ccd.is_data():
                        # this should be data as opposed to a blank frame
                        # between data frames that occur with nskip > 0

                        # subtract the bias
                        if bias is not None:
                            ccd -= bias[cnam]

                        # divide out the flat
                        if flat is not None:
                            ccd /= flat[cnam]

                        # estimate sky background, look for stars
                        objs = []
                        for wnam in ccd:
                            try:
                                # chop window, find objects
                                wind = ccd[wnam].window(xlo,xhi,ylo,yhi)
                                wind.data = wind.data.astype('float')
                                objects, bkg = findStars(
                                    wind, thresh, fwhm, True
                                )

                                # remove dodgy rows
                                objects = objects[objects['tnpix'] >= minpix]

                                # subtract background
                                bkg.subfrom(wind.data)
                                ccd[wnam] = wind

                                # tack on frame number
                                data = (nf+first)*np.ones(len(objects),
                                                          dtype=np.int32)
                                objects = append_fields(objects,'nframe',data)

                                # remove some less useful fields to save a bit more space
                                objects = remove_field_names(
                                    objects,
                                    ('xmin','xmax','ymin','ymax','x2','y2','xy')
                                )

                                objs.append(objects)
                            except hcam.HipercamError:
                                # window may have no overlap with xlo, xhi
                                # ylo, yhi
                                pass

                        objs = np.concatenate(objs)

                        # write to disk
                        if nhdu[nc]:
                            fout[nhdu[nc]].append(objs)
                        else:
                            fout.write(objs)
                            nhdu[nc] = nc+1

                        # set to the correct panel and then plot CCD
                        ix = (nc % nx) + 1
                        iy = nc // nx + 1
                        pgpanl(ix,iy)
                        vmin, vmax = hcam.pgp.pCcd(
                            ccd,iset,plo,phi,ilo,ihi,
                            xlo=xlo, xhi=xhi, ylo=ylo, yhi=yhi
                        )

                        pgsci(core.CNAMS['red'])
                        As,Bs,Thetas,Xs,Ys = objs['a'], objs['b'], objs['theta'], objs['x'], objs['y']
                        for a,b,theta0,x,y in zip(As,Bs,Thetas,Xs,Ys):
                            xs = x + 3*a*np.cos(thetas+theta0)
                            ys = y + 3*b*np.sin(thetas+theta0)
                            pgline(xs,ys)

                        # accumulate string of image scalings
                        if nc:
                            message += ', ccd {:s}: {:.1f}, {:.1f}, exp: {:.4f}'.format(
                                cnam,vmin,vmax,mccd.head['EXPTIME']
                            )
                        else:
                            message += 'ccd {:s}: {:.1f}, {:.1f}, exp: {:.4f}'.format(
                                cnam,vmin,vmax,mccd.head['EXPTIME']
                            )

                pgebuf()
                # end of CCD display loop
                print(message)
                for emessage in emessages:
                    print(emessage)

                if pause > 0.:
                    # pause between frames
                    time.sleep(pause)

                # update the frame number
                n += 1

def remove_field_names(a, names):
    """
    Removes the fields in names from the structured array a
    """
    anames = list(a.dtype.names)
    for name in names:
        if name in anames:
            anames.remove(name)
    b = a[anames]
    return b
