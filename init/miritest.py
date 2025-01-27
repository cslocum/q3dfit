#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
; docformat = 'rst'
;
;+
;
; This function initializes the fitting parameters for PG1411+442
;
; :Categories:
;    IFSF
;
; :Returns:
;    A structure with tags specified in INITTAGS.txt.
;
; :Params:
;
; :Keywords:
;    initmaps: out, optional, type=structure
;      Parameters for map making.
;    initnad: out, optional, type=structure
;      Parameters for NaD fitting.
;
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
;      2015aug25, DSNR, created
;
; :Copyright:
;    Copyright (C) 2015 David S. N. Rupke
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
;-
"""
import os.path
import numpy as np
from q3dfit.common import questfit_readcf

def miritest():

    # bad=1e99
    gal = 'miritest'
    outstr = ''
    ncols = 16
    nrows = 25
    # centcol = 9.002
    # centrow = 14.002
    platescale = 0.3
    fitrange = [11.53050463,13.47485667]

#   These are unique to the user
    #volume = '/Users/Endeavour/Projects/Q3D_dev/MIRI_ETC_sim/'
    volume = '../../../MIRISIM/MIRI-ETC-SIM/'
    infile = volume+'miri_etc_cube_quasar.fits'
    infile = volume+'miri_etc_cube.fits'
    # infile = volume+'miri_etc_cube_galaxy.fits'
    
    #mapdir = volume+'maps/'
    
    outdir = volume+'outputs/'
    #outdir = volume+'miri_etc_cube_quasar_outputs/'

    #qsotemplate = volume+'miri_qsotemplate_B.npy'
    #stellartemplates = \
    #    '/Users/caroline/Documents/ARI-Heidelberg/Q3D/Q3DFIT/q3dfit/Test_GMOS_DATA/pg1411/'+'pg1411hosttemplate.npy'
    logfile = outdir+gal+'_fitlog.txt'
    #batchfile = '../common/fitloop.pro'
    #batchdir = '/Users/drupke/src/idl/batch/'

    #
    # Required pars
    #

    if not os.path.isfile(infile): print('Data cube not found.')


    ### more MIR settings
    #cffilename = '../test/test_questfit/IRAS21219m1757_dlw_qst.cf'
    # cffilename = '../test/test_questfit/miritest_NoQSO.cf'
    cffilename = '../test/test_questfit/miritest.cf'


    config_file = questfit_readcf.readcf(cffilename)


# Lines to fit.
    lines = ['[NeII]12.81']
#    nlines = len(lines)

# Max no. of components.
    maxncomp = 1

# Initialize line ties, n_comps, z_inits, and sig_inits.
    linetie = dict()
    ncomp = dict()
    zinit_gas = dict()
    siginit_gas = dict()
    for i in lines:
        linetie[i] = '[NeII]12.81'
        ncomp[i] = np.full((ncols,nrows),maxncomp)
        zinit_gas[i] = np.full((ncols,nrows,maxncomp),0.)
        siginit_gas[i] = np.full(maxncomp, 500.) #0.1) #1000.)
        zinit_stars=np.full((ncols,nrows),0.0)

#
# Optional pars
#

# Tweaked regions are around HeII,Hb/[OIII],HeI5876/NaD,[OI],Halpha, and [SII]
# Lower and upper wavelength for re-fit
    tw_lo = [4600,5200,6300,6800,7000,7275]
    tw_hi = [4800,5500,6500,7000,7275,7375]
# Number of wavelength regions to re-fit
    tw_n = len(tw_lo)
# Fitting orders
    deford = 1
    tw_ord = np.full(tw_n,deford)
# Parameters for continuum fit
# In third dimension:
#   first element is lower wavelength limit
#   second element is upper
#   third is fit order
    tweakcntfit = np.full((ncols,nrows,3,tw_n),0)
    tweakcntfit[:,:,0,:] = tw_lo
    tweakcntfit[:,:,1,:] = tw_hi
    tweakcntfit[:,:,2,:] = tw_ord

    # Parameters for emission line plotting
    linoth = np.full((1, 1), '', dtype=object)
    linoth[0, 0] = '[[NeII]12.81]'
    argspltlin1 = {'nx': 1,
               'ny': 1,
               'line': lines,
               'size': [1.]}


    # Velocity dispersion limits and fixed values
    siglim_gas = np.array([5., 1000.])
    # lratfix = {'[NI]5200/5198': [1.5]}

    #
    # Output structure
    #

    init = { \
            # Required pars
            'fcninitpar': 'parinit',#gmos
            'fitran': fitrange,
            'fluxunits': 1,  # erg/s/cm^2/sr
            'infile': infile,
            'label': config_file['source'][0].replace('.ideos','').replace('.npy', ''),
            'lines': lines,
            'linetie': linetie,
            'maxncomp': maxncomp,
            'name': 'PG1411+442',
            'ncomp': ncomp,
            'outdir': outdir,
            'zinit_stars': zinit_stars,
            'zinit_gas': zinit_gas,
            'zsys_gas': 0.0,


            # Optional pars
            'argscontfit': {'config_file': cffilename,
                            'models_dictionary': {},
                            'template_dictionary': {},
                            'outdir': outdir},
            'argslinelist': {'vacuum': False},
            'argspltlin1': argspltlin1,
            'decompose_qso_fit': 1,
            'compare_to_real_decomp':   {'on': 1,   ### Option to compare recovered QSO-host decomposition from mock ETC cube to "real" one (only makes sense when running on the combined QSO+host cube)
                                        'file_host': volume+'miri_etc_cube_galaxy.fits', 
                                        'file_qso': volume+'miri_etc_cube_quasar.fits'}, 
            'fcncontfit': 'questfit',
            
            'fcncheckcomp': 'checkcomp',            
            'maskwidths_def': 2000,
            'emlsigcut': 2,
            'logfile': logfile,
            'siglim_gas': siglim_gas,
            'siginit_gas': siginit_gas,
            'siginit_stars': 50,
            'nocvdf': 1,
            # 'plotMIR': True,
            'wmapext': None,
            'argsreadcube': {'fluxunit_in': 'Jy',
                            'waveunit_in': 'angstrom',
                            'waveunit_out': 'micron',
                            'wmapext': None}        

            }

    return(init)
