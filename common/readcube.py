from astropy.constants import c
from astropy.io import fits
from astropy import units as u
from q3dfit.exceptions import CubeError
from scipy import interpolate
from sys import stdout

import copy
import numpy as np
import pdb
import re
import warnings


'''
CUBE: the main class of ifs data cube

Extract data and information from an IFS data cube FITS file.

:Categories:
   IFSFIT

:Usage:
from readcube import *
cube = CUBE(fp='/path/to/data/', infile='datafits')

:Returns:
    python class CUBE
    attributes:
        phu: primary fits extension
        dat: data array
        var: variance array
        err: error array, the values are recorded as nan when the
             variances are negative.
        dq: dq array
        wave: wavelength array
        header_phu: header for the primary fits extension
        header_dat: eader for the data extension
        header_var: header for the variance extension
        header_dq: header for the dq extension
        ncols: number of columns in the cube
        nrows: number of rows in the cube
        nz: number of elements in wavelength array
:Params:
    infile: in, required, type=string
     Name of input FITS file.
:Keywords:
    fp: in, required, type=string
      Path of input FITS file.
    datext: in, optional, type=integer, default=1
      Extension # of data plane. Set to a negative number if the correct
      extension is 0, since an extension of 0 ignores the keyword.
    dqext: in, optional, type=integer, default=3
      Extension # of DQ plane. Set to a negative number if there is no DQ; DQ
      plane is then set to 0.
    error: in, optional, type=byte, default=False
      If the data cube contains errors rather than variance, the routine will
      convert to variance.
    invvar: in, optional, type=byte
      Set if the data cube holds inverse variance instead of variance. The
      output structure will still contain the variance.
    linearize: in, optional, type=byte, default=False
      If set, resample the input wavelength scale so it is linearized.
    quiet: in, optional, type=byte
      Suppress progress messages.
    varext: in, optional, type=integer, default=2
      Extension # of variance plane.
    wavext: in, optional, type=integer
      The extention number of a wavelength array.
    zerodq: in, optional, type=byte
      Zero out the DQ array.
    vormap: in, optional, 2D array for the voronoi binning map
    waveunit: in, optional
      Default is micron; other option is Angstrom
    fluxunit: in, optional
      the flux unit input by the user to be multiplide to the flux
      (The fluxunit is assumed to be JWST default and then converted to
       erg/s/cm^s/um/sr)
; :Author:
;    David S. N. Rupke::
;      Rhodes College
;      Department of Physics
;      2000 N. Parkway
;      Memphis, TN 38104
;      drupke@gmail.com
;
; :History:
;    ChangeHistory::
;      2010jun08, DSNR, created as GMOS_READCUBE
;      2013dec17, DSNR, ported to IFSF_READCUBE
;      2014jan29, DSNR, added ability to change default extensions
;      2014aug05, DSNR, small tweak to allow single spectra and no DQ
;      2015may20, DSNR, updated logic in reading # of rows, cols, and wavelength
;                       points to be more flexible; added wavedim to output
;                       structure
;      2016sep12, DSNR, fixed DATEXT logic so can specify an extension of 0;
;                       added warning when correct wavelength keywords not found;
;                       added second dispersion keyword option.
;      2018feb08, DSNR, added WAVEEXT, INVVAR, and ZERODQ keywords
;      2018feb23, DSNR, added LINEARIZE keyword
;      2018aug12, DSNR, ensure values of DATEXT, VAREXT, DQEXT don't get changed
;      2020may05, DSNR, new treatment of default axes in 2D images; added CUNIT
;                       and BUNIT to output
;      2020may31, Weizhe, translated into python 3
;      2021feb22, DSNR, can now output print statements to log file
;
; :Copyright:
;    Copyright (C) 2013--2021 David S. N. Rupke
;
;    This program is free software: you can redistribute it and/or
;    modify it under the terms of the GNU General Public License as
;    published by the Free Software Foundation, either version 3 of
;    the License or any later version.
;
;    This program is distributed in the hope that it will be useful,
;    but WITHOUT ANY WARRANTY; without even the implied warranty of
;    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
;    General Public License for more details.
;
;    You should have received a copy of the GNU General Public License
;    along with this program.  If not, see
;    http://www.gnu.org/licenses/.
;
'''


class CUBE:
    def __init__(self, **kwargs):
        warnings.filterwarnings("ignore")

        # file path
        fp = kwargs.get('fp', '')
        self.fp = fp
        # input file
        infile = kwargs.get('infile', '')
        self.infile = infile
        # log file; default STDOUT
        logfile = kwargs.get('logfile', stdout)
        # input file
        try:
            hdu = fits.open(fp+infile, ignore_missing_end=True)
        except FileNotFoundError:
            raise CubeError(infile+' does not exist')
        # fits extensions labels
        datext = kwargs.get('datext', 1)  # data
        varext = kwargs.get('varext', 2)  # variance
        dqext = kwargs.get('dqext', 3)   # DQ
        wmapext = kwargs.get('wmapext', 4)  # WMAP; assume for JWST
        self.datext = datext
        self.varext = varext
        self.dqext = dqext
        self.wmapext = wmapext

        # other keyword arguments
        error = kwargs.get('error', False)
        invvar = kwargs.get('invvar', False)
        quiet = kwargs.get('quiet', True)
        linearize = kwargs.get('linearize', False)
        wavext = kwargs.get('wavext', None)
        zerodq = kwargs.get('zerodq', False)
        vormap = kwargs.get('vormap', None)

        # populate hdus
        self.hdu = hdu
        self.phu = hdu[0]
        try:
            self.dat = np.array((hdu[datext].data).T, dtype='float64')
        except (IndexError or KeyError):
            raise CubeError('Data extension not properly specified or absent')

        if varext is not None:
            try:
                self.var = np.array((hdu[varext].data).T, dtype='float64')
            except (IndexError or KeyError):
                raise CubeError('Variance extension not properly specified ' +
                                'or absent')
            if invvar:
                self.var = 1./self.var
            if error:
                self.err = self.var
                self.var = self.var**2.
            else:
                badvar = np.where(self.var < 0)
                if np.size(badvar) > 0:
                    print('CUBE: Negative values encountered in variance ' +
                          'array. Taking absolute value.', file=logfile)
                self.var = np.abs(self.var)
                self.err = np.array(copy.copy(self.var) ** 0.5)
        else:
            self.var = None
            self.err = None

        if dqext is not None:
            try:
                self.dq = np.array((hdu[dqext].data).T)
            except (IndexError or KeyError):
                raise CubeError('DQ extension not properly specified ' +
                                'or absent')
        else:
            self.dq = None
        # put all dq to good (0)
        if zerodq:
            self.dq = np.zeros(np.shape(self.dat))

        if wmapext is not None:
            try:
                self.wmap = (hdu[wmapext].data).T
            except (IndexError or KeyError):
                raise CubeError('WMAP extension not properly specified ' +
                                'or absent')
        else:
            self.wmap = None

        # headers
        self.header_phu = hdu[0].header
        self.header_dat = hdu[datext].header
        self.header_var = hdu[varext].header
        self.header_dq = hdu[dqext].header
        header = copy.copy(self.header_dat)

        # Get shape of cube
        datashape = np.shape(self.dat)
        if np.size(datashape) == 3:
            ncols = (datashape)[0]
            nrows = (datashape)[1]
            nw = (datashape)[2]
            if np.max([nrows, ncols]) > nw:
                raise CubeError('Data cube dimensions not in ' +
                                '[nw, nrows, ncols] format')
            CDELT = 'CDELT3'
            CRVAL = 'CRVAL3'
            CRPIX = 'CRPIX3'
            CDELT = 'CDELT3'
            CD = 'CD3_3'
            CUNIT = 'CUNIT3'
            BUNIT = 'BUNIT'
        elif np.size(datashape) == 2:
            if not quiet:
                print('CUBE: Reading 2D image. Assuming dispersion ' +
                      'is along rows.', file=logfile)
            nrows = 1
            ncols = (datashape)[1]
            nw = (datashape)[-1]
            CDELT = 'CDELT1'
            CRVAL = 'CRVAL1'
            CRPIX = 'CRPIX1'
            CDELT = 'CDELT1'
            CD = 'CD1_1'
            CUNIT = 'CUNIT1'
            BUNIT = 'BUNIT'
        elif np.size(datashape) == 1:
            nrows = 1
            ncols = 1
            nw = (datashape)[0]
            CDELT = 'CDELT1'
            CRVAL = 'CRVAL1'
            CRPIX = 'CRPIX1'
            CDELT = 'CDELT1'
            CD = 'CD1_1'
            CUNIT = 'CUNIT1'
            BUNIT = 'BUNIT'
        self.ncols = int(ncols)
        self.nrows = int(nrows)
        self.nw = int(nw)

        # The current default input and working wavelengths are um
        # The current default input flux is MJy/sr; working flux is
        # erg/s/cm2/micron/sr'
        waveunit_tmp = kwargs.get('waveunit_in', 'micron')
        self.waveunit_out = kwargs.get('waveunit_out', 'micron')
        fluxunit_tmp = kwargs.get('fluxunit_in', 'MJy/sr')
        self.fluxunit_out = kwargs.get('fluxunit_out', 'erg/s/cm2/micron/sr')
        try:
            self.waveunit_in = header[CUNIT]
        except KeyError:
            self.waveunit_in = waveunit_tmp
            if not quiet:
                print('CUBE: No wavelength units in header; assuming micron.',
                      file=logfile)
        try:
            self.fluxunit_in = header[BUNIT]
        except KeyError:
            self.fluxunit_in = fluxunit_tmp
            if not quiet:
                print('CUBE: No flux units in header; assuming MJy/sr',
                      file=logfile)
        # Remove whitespace from units
        self.waveunit_in.strip()
        self.fluxunit_in.strip()

        # cases of weirdo flux units
        # remove string literal '/A/'
        if self.fluxunit_in.find('/A/') != -1:
            self.fluxunit_in = self.fluxunit_in.replace('/A/', '/Angstrom/')
        # remove string literal '/Ang' if it's at the end of the string
        if self.fluxunit_in.find('/Ang') != -1 and \
            self.fluxunit_in.find('/Ang') == len(self.fluxunit_in)-4:
            self.fluxunit_in = self.fluxunit_in.replace('/Ang', '/Angstrom')
        # remove scientific notation # and trailing whitespace
        # https://stackoverflow.com/questions/18152597/extract-scientific-number-from-string
        match_number = re.compile('-?\ *[0-9]+\.?[0-9]*(?:[Ee]' +
                                  '\ *-?\ *[0-9]+)\ *')
        self.fluxunit_in = re.sub(match_number, '', self.fluxunit_in)

        # reading wavelength from wavelength extention
        if wavext is not None:
            try:
                self.wave = hdu[wavext].data
            except (IndexError or KeyError):
                raise CubeError('Wave extension not properly specified ' +
                                'or absent')
            self.crval = 0
            self.crpix = 1
            self.cdelt = 1
        else:
            try:
                self.crval = header[CRVAL]
                self.crpix = header[CRPIX]
            except KeyError:
                raise CubeError('Cannot compute wavelengths; ' +
                                'CRVAL and/or CRPIX missing')
            if CDELT in header:
                self.wav0 = header[CRVAL] - (header[CRPIX] - 1) * header[CDELT]
                self.wave = self.wav0 + np.arange(nw)*header[CDELT]
                self.cdelt = header[CDELT]
            elif CD in header:
                self.wav0 = header[CRVAL] - (header[CRPIX] - 1) * header[CD]
                self.wave = self.wav0 + np.arange(nw)*header[CD]
                self.cdelt = header[CD]
            else:
                raise CubeError('Cannot find or compute wavelengths')

        # convert wavelengths if requested
        if self.waveunit_in != self.waveunit_out:
            wave_in = self.wave * u.Unit(self.waveunit_in)
            self.wave = wave_in.to(u.Unit(self.waveunit_out)).value

        # indexing of Voronoi-tessellated data
        if vormap:
            ncols = np.max(vormap)
            nrows = 1
            vordat = np.zeros((ncols, nrows, nw))
            vorvar = np.zeros((ncols, nrows, nw))
            vordq = np.zeros((ncols, nrows, nw))
            vorcoords = np.zeros((ncols, 2), dtype=int)
            nvor = np.zeros((ncols))
            for i in np.arange(ncols):
                ivor = np.where(vormap == i+1)
                xyvor = [ivor[0][0], ivor[0][1]]
                vordat[i, 0, :] = self.dat[xyvor[0], xyvor[1], :]
                vorvar[i, 0, :] = self.var[xyvor[0], xyvor[1], :]
                vordq[i, 0, :] = self.dq[xyvor[0], xyvor[1], :]
                vorcoords[i, :] = xyvor
                nvor[i] = (np.shape(ivor))[1]
            self.dat = vordat
            self.var = vorvar
            self.dq = vordq

        # Flux unit conversions
        # default working flux unit is erg/s/cm^2/um/sr or erg/s/cm^2/um
        convert_flux = np.float64(1.)
        if u.Unit(self.fluxunit_in) == u.Unit('MJy/sr') or \
            u.Unit(self.fluxunit_in) == u.Unit('MJy'):
            # IR units: https://coolwiki.ipac.caltech.edu/index.php/Units
            # default input flux unit is MJy/sr
            # 1 Jy = 10^-26 W/m^2/Hz
            # first fac: MJy to Jy
            # second fac: 10^-26 W/m^2/Hz / Jy * 10^-4 m^2/cm^-2 * 10^7 erg/W
            # third fac: c/lambda**2 Hz/micron, with lambda^2 in m*micron
            wave_out = self.wave * u.Unit(self.waveunit_out)
            convert_flux = 1e6 * 1e-23 * c.value / wave_out.to('m').value / \
                wave_out.to('micron').value

        # case of input flux units: erg/s/cm^2/Anstrom (/arcsec2/sr)
        elif u.Unit(self.fluxunit_in) == u.Unit('erg/s/cm2/Angstrom/sr') or \
            u.Unit(self.fluxunit_in) == u.Unit('erg/s/cm2/Angstrom') or \
            u.Unit(self.fluxunit_in) == \
                u.Unit('erg/s/cm2/Angstrom/arcsec2/sr') or \
            u.Unit(self.fluxunit_in) == \
                u.Unit('erg/s/cm2/Angstrom/arcsec2'):
            convert_flux = np.float64(1e4)

        # case of output flux units: erg/s/cm^2/Anstrom (/arcsec2/sr)
        if u.Unit(self.fluxunit_out) == u.Unit('erg/s/cm2/Angstrom/sr') or \
            u.Unit(self.fluxunit_out) == u.Unit('erg/s/cm2/Angstrom') or \
            u.Unit(self.fluxunit_out) == \
                u.Unit('erg/s/cm2/Angstrom/arcsec2/sr') or \
            u.Unit(self.fluxunit_out) == \
                u.Unit('erg/s/cm2/Angstrom/arcsec2'):
            convert_flux /= np.float64(1e4)

        #self.dat = self.dat * convert_flux
        #self.var = self.var * convert_flux**2
        #self.err = self.err * convert_flux

        # linearize in the wavelength direction
        if linearize:
            waveold = copy.copy(self.wave)
            datold = copy.copy(self.dat)
            varold = copy.copy(self.var)
            dqold = copy.copy(self.dq)
            self.crpix = 1
            self.cdelt = (waveold[-1]-waveold[0]) / (self.nz-1)
            wave = np.linspace(waveold[0], waveold[-1], num=self.nz)
            self.wave = wave
            spldat = interpolate.splrep(waveold, datold, s=0)
            self.dat = interpolate.splev(waveold, spldat, der=0)
            splvar = interpolate.splrep(waveold, varold, s=0)
            self.var = interpolate.splev(waveold, splvar, der=0)
            spldq = interpolate.splrep(waveold, dqold, s=0)
            self.dq = interpolate.splev(waveold, spldq, der=0)
            if not quiet:
                print('CUBE: Interpolating DQ; values > 0.01 set to 1.',
                      file=logfile)
            ibd = np.where(self.dq > 0.01)
            if np.size(ibd) > 0:
                self.dq[ibd] = 1

        # close the fits file
        hdu.close()


if __name__ == "__main__":
    cube = CUBE(fp='/path/to/data/', infile='data.fits')
