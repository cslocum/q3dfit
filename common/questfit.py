import numpy as np
import lmfit
import copy
from scipy import constants
from astropy import units as u
from q3dfit.common import interptemp
from q3dfit.common import questfitfcn
from q3dfit.common import questfit_readcf
from lmfit.models import ExpressionModel
from matplotlib import pyplot as plt
from q3dfit.common import interp_temp_quest
from q3dfit.common import writeout_quest
import q3dfit
from matplotlib import pyplot as plt



def questfit(wlambda, flux, weights, singletemplatelambda, singletemplateflux, index,
    z, quiet=True, config_file=None, global_ice_model='None', global_ext_model='None', \
    models_dictionary={}, template_dictionary={}, fitran=None, convert2Flambda=True, \
    outdir=None):
    '''Function defined to fit the MIR continuum

    Parameters
    -----
    wlambda: array
        wavelength array in micron

    flux: array
        Flux values to be fit. Assumed units are Jy; will be transformed to 1e-10 erg/s/cm2/mu/sr below.

    weight: array
        Weights of each individual pixel to be fit

    singletemplatelambda: array
        Disregarded if set to b'0'.
        Otherwise, this is a wavelength array for any continuum template separate from the simple empirical BB, power-law etc. components.

    singletemplateflux: array
        Disregarded if set to b'0'.
        Otherwise, this is a flux array for any continuum template separate from the simple empirical BB, power-law etc. components.

    index: array
        Pixels used in the fit

    z: float
        redshift



    returns
    -------
    continuum: array
        best fit continuum model

    ct_coeff: dictionary or lmfit best fit params structure
        best fit parameters

    '''


    models_dictionary = {}
    template_dictionary = {}

    if fitran:
        flux = flux[ np.logical_and(wlambda>=fitran[0]), np.logical_and(wlambda<=fitran[1]) ]
        wlambda = wlambda[ np.logical_and(wlambda>=fitran[0]), np.logical_and(wlambda<=fitran[1]) ]

    if singletemplatelambda!=b'0':
        print('Trying to pass a single separate template to questfit, which is not implemented ... Halting.')
        import sys; sys.exit()

    else:
        config_file = questfit_readcf.readcf(config_file)
        global_extinction = False
        for key in config_file:
            try:
                if 'global' in config_file[key][3]:
                    global_extinction = True
            except:
                continue

        if global_extinction:
            for key in config_file:
                if 'extinction' in config_file[key]:
                    global_ext_model = key
                if 'absorption' in config_file[key]:
                    global_ice_model = key


        loc_models = q3dfit.__path__[0]+'/data/questfit_templates/'
        n_temp = 0
        for i in config_file.keys(): #populating the models dictionary and setting up lmfit models
            if 'blackbody' in i: #starting with the blackbodies
                model_parameters = config_file[i]
                name_model = 'blackbody'+str(int(float(model_parameters[7])))#i
                extinction_model = config_file[i][3]

                ice_model = config_file[i][9]

                model_temp_BB,param_temp_BB = questfitfcn.set_up_fit_blackbody_model([float(model_parameters[1]),float(model_parameters[7])],[float(model_parameters[2]),float(model_parameters[8])],name_model[:])

                if global_extinction == False and config_file[i][3] != '_' and config_file[i][3] != '-':
                        model_temp_extinction,param_temp_extinction = questfitfcn.set_up_fit_extinction([float(model_parameters[4])],[float(model_parameters[5])],name_model+'_ext',extinction_model,model_parameters[6])

                        model_temp = model_temp_BB*model_temp_extinction
                        param_temp = param_temp_BB + param_temp_extinction

                        models_dictionary[extinction_model] = config_file[extinction_model][0]
                else:
                    model_temp = model_temp_BB
                    param_temp = param_temp_BB

                if 'ice' in i and global_extinction == False: #checking if we need to add ice absorption
                    model_temp_ice,param_temp_ice = questfitfcn.set_up_absorption([float(model_parameters[10])],[float(model_parameters[11])],name_model+'_abs',model_parameters[9])
                    model_temp = model_temp*model_temp_ice
                    param_temp += param_temp_ice
                    models_dictionary[model_parameters[9]] = config_file[model_parameters[9]][0]
                if 'model' not in vars():
                    model,param = model_temp,param_temp

                else:
                    model += model_temp
                    param += param_temp

            if 'powerlaw' in i: #powerlaw model
                model_parameters = config_file[i]
                name_model = 'powerlaw'+str(int(float(model_parameters[7])))
                extinction_model = config_file[i][3]
                ice_model = config_file[i][9]

                model_temp_powerlaw,param_temp_powerlaw = questfitfcn.set_up_fit_powerlaw_model([1,float(model_parameters[7])],[float(model_parameters[2]),float(model_parameters[8])],name_model[:])

                if global_extinction == False and config_file[i][3] != '_' and config_file[i][3] != '-':
                        model_temp_extinction,param_temp_extinction = questfitfcn.set_up_fit_extinction([float(model_parameters[4])],[float(model_parameters[5])],'powerlaw'+str(int(float(model_parameters[7])))+'_ext',extinction_model,model_parameters[6])

                        model_temp = model_temp_powerlaw*model_temp_extinction
                        param_temp = param_temp_powerlaw + param_temp_extinction

                        models_dictionary[extinction_model] = config_file[extinction_model][0]
                else:
                    model_temp = model_temp_powerlaw
                    param_temp = param_temp_powerlaw

                if 'ice' in i and global_extinction == False: #checking if we need to add ice absorption
                    model_temp_ice,param_temp_ice = questfitfcn.set_up_absorption([float(model_parameters[10])],[float(model_parameters[11])],name_model+'_abs',model_parameters[9])
                    model_temp = model_temp*model_temp_ice
                    param_temp += param_temp_ice
                    models_dictionary[model_parameters[9]] = config_file[model_parameters[9]][0]

                if 'model' not in vars():
                    model,param = model_temp,param_temp

                else:
                    model += model_temp
                    param += param_temp


            if 'template' in i: #template model
                model_parameters = config_file[i]
                name_model = 'template_'+str(n_temp)#i
                extinction_model = config_file[i][3]
                ice_model = config_file[i][9]

                if not 'poly' in i:
                    model_temp_template,param_temp_template = questfitfcn.set_up_fit_model_scale([float(model_parameters[1])],[float(model_parameters[2])],name_model,name_model, maxamp=1.05*max(flux[index]) ) #name_model.split('.')[0]template+'_'+str(n_temp)
                else:
                    minamp = float(model_parameters[1]) / 1.25
                    maxamp = float(model_parameters[1]) * 1.25
                    model_temp_template,param_temp_template = questfitfcn.set_up_fit_model_scale_withpoly([float(model_parameters[1])],[float(model_parameters[2])],name_model,name_model, minamp=minamp, maxamp=maxamp)#1.05*max(flux[index])) #name_model.split('.')[0]template+'_'+str(n_temp)

                    testing = False
                    if testing:
                        temp_model = np.load(loc_models+'miri_qsotemplate_flex.npy', allow_pickle=True)
                        temp_model = temp_model[()]
                        wave_ex = temp_model['wave']
                        flux_ex = temp_model['flux']
                        c_scale =  constants.c * u.Unit('m').to('micron') /(wave_ex)**2 *1e-23  *1e10      # [1e-10 erg/s/cm^2/um/sr]]
                        flux_ex = flux_ex * c_scale
                        flux_ex = flux_ex/flux_ex.max()
                        c2 = [1., 0., 0.]
                        c2 = [0.116, 0.224, 147.71]
                        c2 = [0.213, 0.024, 75.794]
                        c2 = [1, 100., 500.71]
                        m1 = model_temp_template.eval(template_0=flux_ex , wave=wave_ex, template_0_amp=1.,template_0_multpolyA=1.,template_0_multpolyB=2.,template_0_multpolyC = 3. )
                        m2 = model_temp_template.eval(template_0=flux_ex , wave=wave_ex, template_0_amp=1.,template_0_multpolyA=c2[0],template_0_multpolyB=c2[1],template_0_multpolyC = c2[2] )

                        ex_poly = lambda lam, p0,p1,p2:  (p0+p1*lam+p2*lam**2)/max(p0+p1*lam+p2*lam**2)
                        ex_poly2 = lambda lam, p0,p1,p2:  (p0+p1*lam+p2*lam**7)/max(p0+p1*lam+p2*lam**7)
                        ex_poly = lambda lam, p0,p1,p2:  (p0+p1*lam+p2*lam**2)/max(p0+p1*lam+p2*lam**2)
                        lin_poly = lambda lam, p0,p1,p2:  (p0+p1*np.arange(len(lam)))/max((p0+p1*np.arange(len(lam))))
                        plt.figure()
                        plt.plot(wave_ex, flux_ex, label='orig', color='k', linewidth=2.5)
                        plt.plot(wave_ex, m1, linewidth=1, label='model.eval() with  A=1, B=2, C=3 (and Amp=1)')
                        plt.plot(wave_ex, m2, linewidth=1, label='model.eval() with  A={}, B={}, C={} (and Amp=1)'.format(c2[0], c2[1], c2[2]))
                        plt.xlabel(r'$\lambda$')
                        plt.ylabel('F_norm')
                        plt.legend()
                        plt.show()

                        breakpoint()


                if 'si' in i:
                    #config_file[i][0].split('.')[0]
                    template_dictionary[name_model] = 'silicatemodels/'+config_file[i][0]
                else:

                    template_dictionary[name_model] = config_file[i][0]

                if global_extinction == False and config_file[i][3] != '_' and config_file[i][3] != '-':

                        model_temp_extinction,param_temp_extinction = questfitfcn.set_up_fit_extinction([float(model_parameters[4])],[float(model_parameters[5])],name_model+'_ext',extinction_model,model_parameters[6])
                        model_temp = model_temp_template*model_temp_extinction
                        param_temp = param_temp_template + param_temp_extinction

                        models_dictionary[extinction_model] = config_file[extinction_model][0]

                else:
                    model_temp = model_temp_template
                    param_temp = param_temp_template

                if 'ice' in i and global_extinction == False: #checking if we need to add ice absorption
                    model_temp_ice,param_temp_ice = questfitfcn.set_up_absorption([float(model_parameters[10])],[float(model_parameters[11])],name_model+'_abs',model_parameters[9])
                    model_temp = model_temp*model_temp_ice
                    param_temp += param_temp_ice
                    models_dictionary[model_parameters[9]] = config_file[model_parameters[9]]

                if 'model' not in vars():
                    model,param = model_temp,param_temp

                else:
                    model += model_temp
                    param += param_temp

                n_temp+=1


        #if qsoflux is not None:
            #model_qso, param_qso = questfitfcn.set_up_fit_model_scale

        if global_extinction == True: #Check to see if we are using global extinction, where the total model flux is extincted by the same ice and dust model.
            model_global_ext,param_global_ext = questfitfcn.set_up_fit_extinction([0],[1],'global_ext',global_ext_model,'S')
            model = model*model_global_ext
            param += param_global_ext
            models_dictionary[global_ext_model] = config_file[global_ext_model][0]
            model_global_ice,param_global_ice = questfitfcn.set_up_absorption([0],[1],'global_ice',global_ice_model)

            model = model*model_global_ice
            param += param_global_ice
            models_dictionary[global_ice_model] = config_file[global_ice_model][0]

        for i in models_dictionary.keys(): #loop over models dictionary, load them in and resample.
            temp_model = np.load(loc_models+models_dictionary[i],allow_pickle=True)

            temp_wave = []
            temp_value = []

            temp_wave=temp_model['WAVE']
            temp_value=temp_model['FLUX']


            temp_value_rebin = interp_temp_quest.interp_lis(wlambda, temp_wave, temp_value)
            models_dictionary[i] = temp_value_rebin


        c_scale =  constants.c * u.Unit('m').to('micron') /(wlambda)**2 *1e-23  *1e10      # [1e-10 erg/s/cm^2/um/sr]]

        for i in template_dictionary.keys(): #loop over template dictionary, load them in and resample.

            temp_model = np.load(loc_models+template_dictionary[i],allow_pickle=True)
            temp_wave = []
            temp_value = []

            try:
                temp_wave=temp_model['WAVE']
                temp_value=temp_model['FLUX']
            except:
                temp_model = temp_model[()]     # if a QSO template generated by makeqsotemplate() is included, that is formatted slightly differently
                temp_wave=temp_model['wave']
                temp_value=temp_model['flux']


            temp_value_rebin = interp_temp_quest.interp_lis(wlambda, temp_wave, temp_value)
            if convert2Flambda:
                models_dictionary[i] = temp_value_rebin*c_scale
            models_dictionary[i] = models_dictionary[i]/models_dictionary[i].max()  # normalise


        models_dictionary['wave'] = wlambda/(1+z)
        models_dictionary['fitFlambda'] = bool(convert2Flambda)

        if convert2Flambda:
            flux *= c_scale


        plot_ini_guess = False
        if plot_ini_guess:
            plt.plot(models_dictionary['wave'], param['template_0_amp'].value * models_dictionary['template_0']/c_scale, color='c', label = 'QSO model init')

            data1 = np.load('../data/questfit_templates/' + 'miri_qsotemplate_flexB.npy', allow_pickle='TRUE').item()
            F1 = data1['flux'][:-1] * c_scale
            plt.plot(models_dictionary['wave'], F1/c_scale, color='b', label = 'QSO real')

            gal_model_comp = [el for el in models_dictionary if 'template' in el and 'template_0' not in el]
            Fgalmodel = 0
            for comp_i in gal_model_comp:
                Fgalmodel += param[comp_i+'_amp'].value * models_dictionary[comp_i]
            plt.plot(models_dictionary['wave'], Fgalmodel/c_scale, color='plum', label = 'host model init')

            data2 = np.load('../data/questfit_templates/' + 'miri_gal_spec.npy', allow_pickle='TRUE').item()
            F2 = data2['flux'][:-1] * c_scale
            plt.plot(models_dictionary['wave'], F2/c_scale, color='darkviolet', label = 'host real')
            plt.yscale("log")
            plt.xlabel(r'$\lambda \ \mathrm{[micron]}$')
            plt.legend()
            plt.show()
            breakpoint()

        flux_cut = flux[index]
        models_dictionary_cut = copy.deepcopy(models_dictionary)
        for el in models_dictionary.keys():
            if not ('fitFlambda' in el):
                models_dictionary_cut[el] = models_dictionary_cut[el][index]

        outpy = '../data/questfit_templates/' + 'miri_qsotemplate_flex.npy'
        data1 = np.load(outpy, allow_pickle=True)
        f_orig = data1.item()['flux'][:-1]




        # from multiprocessing import Pool
        # with Pool() as pool:
        use_emcee = False
        if use_emcee:

            # -- Originally used max_nfev=int(1e5), and method='least_squares'
            emcee_kws = dict(steps=5000, burn=500, thin=20, is_weighted=False, progress=True) #, run_mcmc_kwargs={'skip_initial_state_check': True} )
            #emcee_kws = dict(nwalkers=500, steps=5000, burn=500, thin=20, workers=pool, is_weighted=False, progress=True) #, run_mcmc_kwargs={'skip_initial_state_check': True} )
            # emcee_kws = dict(nwalkers=256, steps=50000, burn=500, thin=5, is_weighted=False, progress=True) #, run_mcmc_kwargs={'skip_initial_state_check': True} )

            param.add('__lnsigma', value=np.log(0.1), min=np.log(0.001), max=np.log(2.0))
            import time
            t1 = time.time()
            result = model.fit(flux_cut,param,**models_dictionary_cut,max_nfev=int(1e5),method='emcee',nan_policy='omit', fit_kws=emcee_kws)#method='least_squares'nan_policy='omit'
            print('Time needed for fitting: ', time.time()-t1)

            import corner
            emcee_plot = corner.corner(result.flatchain, labels=result.var_names,truths=list(result.params.valuesdict().values()))
            plt.savefig(outdir+'corner')

        else:
            result = model.fit(flux_cut,param,**models_dictionary_cut,max_nfev=int(1e5),method='least_squares',nan_policy='omit')#method='least_squares'nan_policy='omit'

        lmfit.report_fit(result.params)
        with open(outdir+'it_result.txt', 'w') as fh:
            fh.write(result.fit_report())
            fh.write('\n')

        best_fit = result.eval(**models_dictionary) # use models_dictionary rather than models_dictionary_cut to evaluate over all wavelengths within fitran (not just [index])
        comp_best_fit = result.eval_components(**models_dictionary)
        # print(result.best_values)

        if convert2Flambda:
            flux /= c_scale
            best_fit /= c_scale
            for el in comp_best_fit.keys():
                if not (global_ext_model in el) and not (global_ice_model in el) and not ('ext' in el) and not ('ice' in el):
                    try:
                        comp_best_fit[el] /= c_scale
                    except Exception as e:
                        print(e)
                        import pdb; pdb.set_trace()

        ct_coeff = {'MIRparams': result.params, 'comp_best_fit': comp_best_fit}

        #return best_fit,comp_best_fit,result
        return best_fit, ct_coeff, z


def quest_extract_QSO_contrib(ct_coeff, initdat):
    '''
    This function can be used to recover the QSO-host decomposition after running questfit

    :Params:
        ct_coeff: in, required, type=dict
            dict returned by questfit containing the continuum fitting results
        initdat: in, required, type=dict
            dict that was used to initialize the fit

        qso_out_ext: out, type=array
            spectrum of the QSO component (with dust extinction and ice absorption)
        host_out_ext:  out, type=array
            spectrum of the host component (with dust extinction and ice absorption)
    '''
    comp_best_fit = ct_coeff['comp_best_fit']
    qso_out_ext = np.array([])
    qso_out_intr = np.array([])

    config_file = questfit_readcf.readcf(initdat['argscontfit']['config_file'])
    if not 'qso' in list(config_file.keys())[1]:    ### This function assumes that in the config file the qso temple is the first template. Rudimentary check here.
        print('\n\nWARNING during QSO-host decomposition: \nThe function assumes that in the config file the qso template is the first template, but its name does not contain \"qso\". Pausing here as a checkpoint, press c for continuing.\n')
        import pdb; pdb.set_trace()

    global_extinction = False
    for key in config_file:
        try:
            if 'global' in config_file[key][3]:
                    global_extinction = True
        except:
            continue

    if global_extinction:
        str_global_ext = list(comp_best_fit.keys())[-2]
        str_global_ice = list(comp_best_fit.keys())[-1]
        if len(comp_best_fit[str_global_ext].shape) > 1:  # global_ext is a multi-dimensional array
          comp_best_fit[str_global_ext] = comp_best_fit[str_global_ext] [:,0,0]
        if len(comp_best_fit[str_global_ice].shape) > 1:  # global_ice is a multi-dimensional array
          comp_best_fit[str_global_ice] = comp_best_fit[str_global_ice] [:,0,0]
        host_out_ext = np.zeros(len(comp_best_fit[str_global_ext]))
        host_out_intr = np.zeros(len(comp_best_fit[str_global_ext]))

        for i, el in enumerate(comp_best_fit):
          if (el != str_global_ext) and (el != str_global_ice):
            if len(comp_best_fit[el].shape) > 1:              # component is a multi-dimensional array
              comp_best_fit[el] = comp_best_fit[el] [:,0,0]
            if 'decompose_qso_fit' in initdat:
              if initdat['decompose_qso_fit'] and i==0:     ### NOTE on i==0: This only works is in the config file the qso temple is the first template
                qso_out_ext = comp_best_fit[el]*comp_best_fit[str_global_ext]*comp_best_fit[str_global_ice]
                qso_out_intr = comp_best_fit[el]
              else:
                host_out_ext += comp_best_fit[el]*comp_best_fit[str_global_ext]*comp_best_fit[str_global_ice]
                host_out_intr += comp_best_fit[el]
    else:
        el1 = list(comp_best_fit.keys())[0]
        host_out_ext = np.zeros(len(comp_best_fit[el1]))
        host_out_intr = np.zeros(len(comp_best_fit[el1]))

        spec_i = np.array([])
        for i, el in enumerate(comp_best_fit):
            if len(comp_best_fit[el].shape) > 1:
              comp_best_fit[el] = comp_best_fit[el] [:,0,0]

            if not ('_ext' in el or '_abs' in el):
                spec_i = comp_best_fit[el]
                intr_spec_i = comp_best_fit[el].copy()
                if el+'_ext' in comp_best_fit.keys():
                    spec_i = spec_i*comp_best_fit[el+'_ext']
                if el+'_abs' in comp_best_fit.keys():
                    spec_i = spec_i*comp_best_fit[el+'_abs']

                if 'decompose_qso_fit' in initdat:
                    if initdat['decompose_qso_fit'] and i==0:
                        qso_out_ext = spec_i
                        qso_out_intr = intr_spec_i
                    else:
                        host_out_ext += spec_i
                        host_out_intr += intr_spec_i
                        #breakpoint()

    return qso_out_ext, host_out_ext, qso_out_intr, host_out_intr




do_test = False
if do_test:
    directory = '../test/test_questfit/'
    loc_models = '../data/questfit_templates/'
    models_dictionary = {}
    template_dictionary = {}
    extinction_absorption_dictionary = {}

    global_extinction = True
    global_ice_model = 'ice_hc'
    global_ext_model = 'Chiar06'



    #For testing MRK 231
    # z=0.04147
    # filename = '../test/test_questfit/4978688_0.ideos.cf'
    # config_file = questfit_readcf.readcf(filename)
    # data_to_fit = np.load(directory+config_file['source'][0],allow_pickle=True)
    # wave = data_to_fit['WAVE'].astype('float')[37:350]#np.arange(6,30,0.01)
    # flux = data_to_fit['FLUX'].astype('float')[37:350]
    # weights = data_to_fit['eflux'].astype('float')[37:350]

    #For testing IRAS21219
    filename = '../test/test_questfit/IRAS21219m1757_dlw_qst.cf'
    config_file = questfit_readcf.readcf(filename)
    z=0.112
    global_ext_model = 'CHIAR06'
    data_to_fit = np.load(directory+config_file['source'][0],allow_pickle=True)[0]
    wave = data_to_fit['WAVE'].astype('float')
    wave_min = np.where(wave>=float(config_file['source'][1]))[0][0]
    wave_max = np.where(wave>=float(config_file['source'][2]))[0][0]

    wave = data_to_fit['WAVE'].astype('float')[wave_min:wave_max]
    flux = data_to_fit['FLUX'].astype('float')[wave_min:wave_max]
    weights = data_to_fit['stdev'].astype('float')[wave_min:wave_max]



    singletemplatelambda = b'0'
    singletemplateflux = b'0'
    index = None
    best_fit, MIRct_coeff, MIRz = questfit(wave,flux,weights,singletemplatelambda, singletemplateflux, \
        index,z, quiet=True, config_file=filename, global_ice_model=global_ice_model, global_ext_model=global_ext_model, \
        models_dictionary={}, template_dictionary={}, fitran=None)

    if len(best_fit)==1:    best_fit=best_fit[0]

    comp_best_fit = MIRct_coeff['comp_best_fit']



    #eval = model.eval(param,**models_dictionary)

    #model_temp_extinction.eval(params=param_temp_extinction,DRAINE03 = models_dictionary['DRAINE03'])

    #comp=dict(model.eval_components(params=param,**models_dictionary))
    #
    #fig = plt.figure(figsize=(12, 7))
    #gs = fig.add_gridspec(2,1)
    #ax1 = fig.add_subplot(gs[0, :])
    #ax1.plot(wave,np.log10(eval),label='total_model')
    #for i in comp.keys():
    #    ax1.plot(wave,np.log10(comp[i]),label=i,linestyle='--',alpha=0.5)


    #plt.plot(wave_temp,np.log10(comp['blackbody_cold_DRAINE03_H2ice_']),label='blackbody_cold_DRAINE03_H2ice_')
    #plt.plot(wave_temp,np.log10(comp['blackbody_hot_DRAINE03_H2ice_']),label='blackbody_hot_DRAINE03_H2ice_')
    #ax1.legend()
    #ax1.set_xlabel('wavelength [micron]')




    #plt.close("all")



    fig = plt.figure(figsize=(6, 7))
    gs = fig.add_gridspec(4,1)
    ax1 = fig.add_subplot(gs[:3, :])

    ax1.plot(wave,flux,color='black')
    ax1.plot(wave,best_fit)

    if global_extinction == True:
       for i in np.arange(0,len(comp_best_fit.keys())-2,1):
           try:
              ax1.plot(wave,comp_best_fit[list(comp_best_fit.keys())[i]]*comp_best_fit[list(comp_best_fit.keys())[-2]]*comp_best_fit[list(comp_best_fit.keys())[-1]],label=list(comp_best_fit.keys())[i],linestyle='--',alpha=0.5)
           except:
              ax1.plot(wave,comp_best_fit[list(comp_best_fit.keys())[i]][0]*comp_best_fit[list(comp_best_fit.keys())[-2]][0]*comp_best_fit[list(comp_best_fit.keys())[-1]][0],label=list(comp_best_fit.keys())[i],linestyle='--',alpha=0.5)

    if global_extinction == False:
       for i in np.arange(0,len(comp_best_fit.keys()),3):
           ax1.plot(wave,comp_best_fit[list(comp_best_fit.keys())[i]]*comp_best_fit[list(comp_best_fit.keys())[i+1]]*comp_best_fit[list(comp_best_fit.keys())[i+2]],label=list(comp_best_fit.keys())[i],linestyle='--',alpha=0.5)

    counter = 0

    # while counter < len(comp_best_fit.keys()):
    #     if list(comp_best_fit.keys())[counter]+'_abs' in list(comp_best_fit.keys()):
    #         ax1.plot(wave,comp_best_fit[list(comp_best_fit.keys())[counter]]*comp_best_fit[list(comp_best_fit.keys())[counter+1]]*comp_best_fit[list(comp_best_fit.keys())[counter+2]],label=list(comp_best_fit.keys())[counter],linestyle='--',alpha=0.5)
    #         counter+=3

    #     else:
    #         ax1.plot(wave,comp_best_fit[list(comp_best_fit.keys())[counter]]*comp_best_fit[list(comp_best_fit.keys())[counter+1]],label=list(comp_best_fit.keys())[counter],linestyle='--',alpha=0.5)
    #         counter+=2


    ax1.legend(ncol=2)

    #plt.plot(wave,comp_best_fit['template_smith_nftemp3'])
    #plt.plot(wave,comp_best_fit['template_smith_nftemp4'])


    ax1.set_xscale('log')
    ax1.set_yscale('log')
    ax1.set_xticklabels([])
    ax1.set_ylim(1e-4,1e2)
    #template    smith_nftemp3.npy    1.0    1.    Chiar06    0.0    1.0    S    0.0    0.0 ice_hc    0.0    1.0
    #template    smith_nftemp4.npy    1.0    1.    Chiar06    0.0    1.0    S    0.0    0.0 ice_hc    0.0    1.0

    ax2 = fig.add_subplot(gs[-1, :], sharex=ax1)
    ax2.plot(wave,flux/best_fit,color='black')
    ax2.axhline(1, color='grey', linestyle='--', alpha=0.7, zorder=0)
    ax2.set_ylabel('Data/Model')
    ax2.set_xlabel('Wavelength [micron]')
    gs.update(wspace=0.0, hspace=0.05)

    plt.show()

    # fig = gcf()
    # gs = fig.add_gridspec(2,1)
    # ax2 = fig.add_subplot(222, sharex=ax1, sharey=ax1)

    # -- Save output --

    #writeout_quest.save_spectral_comp(wave, flux, best_fit, comp_best_fit, filename)
    #writeout_quest.save_params(result, filename)


    # Reset
    models_dictionary = {}
    template_dictionary = {}
    extinction_absorption_dictionary = {}

