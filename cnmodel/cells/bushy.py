from neuron import h

from .cell import Cell
from .. import synapses
from ..util import nstomho
from ..util import Params
import numpy as np
from .. import data

__all__ = ['Bushy', 'BushyRothman']


class Bushy(Cell):
    
    type = 'bushy'

    @classmethod
    def create(cls, model='RM03', **kwds):
        if model == 'RM03':
            return BushyRothman(**kwds)
        else:
            raise ValueError ('Bushy model %s is unknown', model)

    def make_psd(self, terminal, psd_type, **kwds):
        """
        Connect a presynaptic terminal to one post section at the specified location, with the fraction
        of the "standard" conductance determined by gbar.
        The default condition is designed to pass the unit test (loc=0.5)
        
        Parameters
        ----------
        terminal : Presynaptic terminal (NEURON object)
        
        psd_type : either simple or multisite PSD for bushy cell
        
        kwds: dictionary of options. 
            Two are currently handled:
            postsite : expect a list consisting of [sectionno, location (float)]
            AMPAScale : float to scale the ampa currents
        
        """
        if 'postsite' in kwds:  # use a defined location instead of the default (soma(0.5)
            postsite = kwds['postsite']
            loc = postsite[1]  # where on the section?
            uname = 'sections[%d]' % postsite[0]  # make a name to look up the neuron section object
            post_sec = self.hr.get_section(uname)  # Tell us where to put the synapse.
        else:
            loc = 0.5
            post_sec = self.soma
        
        if psd_type == 'simple':
            weight = data.get('sgc_synapse', species=self.species,
                        post_type=self.type, field='weight')
            return self.make_exp2_psd(post_sec, terminal, weight=weight, loc=loc)
        elif psd_type == 'multisite':
            if terminal.cell.type == 'sgc':
                # Max conductances for the glu mechanisms are calibrated by 
                # running `synapses/tests/test_psd.py`. The test should fail
                # if these values are incorrect
                self.AMPAR_gmax = data.get('sgc_synapse', species=self.species,
                        post_type=self.type, field='AMPAR_gmax')*1e3
                self.NMDAR_gmax = data.get('sgc_synapse', species=self.species,
                        post_type=self.type, field='NMDAR_gmax')*1e3
                self.Pr = data.get('sgc_synapse', species=self.species,
                        post_type=self.type, field='Pr')
                # adjust gmax to correct for initial Pr
                self.AMPAR_gmax = self.AMPAR_gmax/self.Pr
                self.NMDAR_gmax = self.NMDAR_gmax/self.Pr
#               original values (now in synapses.py):
#                self.AMPA_gmax = 3.314707700918133*1e3  # factor of 1e3 scales to pS (.mod mechanisms) from nS.
#                self.NMDA_gmax = 0.4531929783503451*1e3
                if 'AMPAScale' in kwds:  # normally, this should not be done!
                    self.AMPAR_gmax = self.AMPAR_gmax * kwds['AMPAScale']  # allow scaling of AMPA conductances
                if 'NMDAScale' in kwds:
                    self.NMDAR_gmax = self.NMDAR_gmax * kwds['NMDAScale']  # and NMDA... 
                return self.make_glu_psd(post_sec, terminal, self.AMPAR_gmax, self.NMDAR_gmax, loc=loc)
            elif terminal.cell.type == 'dstellate':
                return self.make_gly_psd(post_sec, terminal, type='glyslow', loc=loc)
            elif terminal.cell.type == 'tuberculoventral':
                return self.make_gly_psd(post_sec, terminal, type='glyslow', loc=loc)
            else:
                raise TypeError("Cannot make PSD for %s => %s" % 
                            (terminal.cell.type, self.type))
        else:
            raise ValueError("Unsupported psd type %s" % psd_type)

    def make_terminal(self, post_cell, term_type, **kwds):
        if term_type == 'simple':
            return synapses.SimpleTerminal(self.soma, post_cell, **kwds)

        elif term_type == 'multisite':
            if post_cell.type == 'mso':
                nzones = data.get('bushy_synapse', species=self.species,
                        post_type=post_cell.type, field='n_rsites')
                delay = 0
            else:
                raise NotImplementedError("No knowledge as to how to connect Bushy cell to cell type %s" %
                                        type(post_cell))
            pre_sec = self.soma
            return synapses.StochasticTerminal(pre_sec, post_cell, nzones=nzones, 
                                            delay=delay, **kwds)
        else:
            raise ValueError("Unsupported terminal type %s" % term_type)


class BushyRothman(Bushy):
    """
    VCN bushy cell models.
        Rothman and Manis, 2003abc (Type II, Type II-I)
        Xie and Manis, 2013
    """

    def __init__(self, morphology=None, decorator=None, nach=None,
                 ttx=False, species='guineapig', modelType=None, debug=False, temperature=None):
        """
        Create a bushy cell, using the default parameters for guinea pig from
        R&M2003, as a type II cell.
        Additional modifications to the cell can be made by calling methods below.
        
        Parameters
        ----------
        morphology : string (default: None)
            Name of a .hoc file representing the morphology. This file is used to constructe
            an electrotonic (cable) model. 
            If None (default), then a "point" (really, single cylinder) model is made, exactly according to RM03.
            
        decorator : Python function (default: None)
            decorator is a function that "decorates" the morphology with ion channels according
            to a set of rules.
            If None, a default set of channels is inserted into the first soma section, and the
            rest of the structure is "bare".
        
        nach : string (default: None)
            nach selects the type of sodium channel that will be used in the model. A channel mechanism
            by that name must exist. The default channel is set to 'nacn' (R&M03)
        
        temperature : float (default: 22)
            temperature to run the cell at. 
                 
        ttx : Boolean (default: False)
            If ttx is True, then the sodium channel conductance is set to 0 everywhere in the cell.
            This flag duplicates the effects of tetrodotoxin in the model. Currently, the flag is not implemented.
        
        species: string (default 'guineapig')
            species defines the pattern of ion channel densities that will be inserted, according to 
            prior measurements in various species. Note that
            if a decorator function is specified, this argument is ignored as the decorator will
            specify the channel density.
            
        modelType: string (default: None)
            modelType specifies the subtype of the cell model that will be used (e.g., "II", "II-I", etc).
            modelType is passed to the decorator, or to species_scaling to adjust point (single cylinder) models.
            
        debug: boolean (default: False)
            When True, there will be multiple printouts of progress and parameters.
            
        Returns
        -------
            Nothing
                 
        """
        super(BushyRothman, self).__init__()
        self.i_test_range={'pulse': (-1, 1, 0.05)}  # note that this gets reset with decorator according to channels
                                                    # Changing the default values will cause the unit tests to fail!
        if modelType == None:
            modelType = 'II'
        if nach == None and species == 'guineapig':
            nach = 'na'
        if nach == None and species == 'mouse':
            nach = 'na'
            self.i_test_range={'pulse': (-1, 1.2, 0.05)}
        
        self.status = {'soma': True, 'axon': False, 'dendrites': False, 'pumps': False, 'hillock': False, 
                       'initialsegment': False, 'myelinatedaxon': False, 'unmyelinatedaxon': False,
                       'na': nach, 'species': species, 'modelType': modelType, 'ttx': ttx, 'name': 'Bushy',
                       'morphology': morphology, 'decorator': decorator, 'temperature': temperature}

        self.spike_threshold = -40
        self.vrange = [-70., -55.]  # set a default vrange for searching for rmp
         # print 'model type, species: ', modelType, species, nach
        if morphology is None:
            """
            instantiate a basic soma-only ("point") model
            """
            # print "<< Bushy model: Creating point cell >>"
            soma = h.Section(name="Bushy_Soma_%x" % id(self))  # one compartment of about 29000 um2
            soma.nseg = 1
            self.add_section(soma, 'soma')
        else:
            """
            instantiate a structured model with the morphology as specified by 
            the morphology file
            """
            # print "<< Bushy model: Creating cell with morphology from %s >>" % morphology
            self.set_morphology(morphology_file=morphology)

        # decorate the morphology with ion channels
        if decorator is None:   # basic model, only on the soma
            self.mechanisms = ['klt', 'kht', 'ihvcn', 'leak', nach]
            for mech in self.mechanisms:
                self.soma.insert(mech)
            self.soma.ena = self.e_na
            self.soma.ek = self.e_k
            self.soma().ihvcn.eh = self.e_h
            self.soma().leak.erev = self.e_leak
            self.c_m = 0.9
            self.species_scaling(silent=True, species=species, modelType=modelType)  # set the default type II cell parameters
        else:  # decorate according to a defined set of rules on all cell compartments
            self.decorate()
        self.save_all_mechs()  # save all mechanisms inserted, location and gbar values...
        self.get_mechs(self.soma)
        if debug:
            print "   << Bushy cell model created >>"

    def get_cellpars(self, dataset, species='guineapig', celltype='II'):
        cellcap = data.get(dataset, species=species, cell_type=celltype,
            field='soma_Cap')
        chtype = data.get(dataset, species=species, cell_type=celltype,
            field='soma_na_type')
        pars = Params(cap=cellcap, natype=chtype)
        for g in ['soma_na_gbar', 'soma_kht_gbar', 'soma_klt_gbar', 'soma_ih_gbar', 'soma_leak_gbar']:
            pars.additem(g,  data.get(dataset, species=species, cell_type=celltype,
            field=g))
        return pars

    def species_scaling(self, species='guineapig', modelType='II', silent=True):
        """
        Adjust all of the conductances and the cell size according to the species requested.
        This scaling should be used ONLY for point models, as no other compartments
        are scaled.
        
        This scaling routine also sets the temperature for the model to a default value. Some models
        can be run at multiple temperatures, and so a default from one of the temperatures is used.
        The calling cell.set_temperature(newtemp) will change the conductances and reinitialize
        the cell to the new temperature settings.
        
        Parameters
        ----------
        species : string (default: 'guineapig')
            name of the species to use for scaling the conductances in the base point model
            Must be one of mouse, cat, guineapig
        
        modelType: string (default: 'II')
            definition of model type from RM03 models, type II or type II-I
        
        silent : boolean (default: True)
            run silently (True) or verbosely (False)
        
        """
        #print '\nSpecies scaling: %s   %s' % (species, type)
        knownspecies = ['mouse', 'guineapig', 'cat']
        
        soma = self.soma
        if modelType == 'II':
            celltype = 'bushy-II'
        elif modelType == 'II-I':
            celltype = 'bushy-II-I'
        elif modelType == 'I-II':
            celltype = 'bushy-I-II'
        else:
            raise ValueError('model type not recognized')

        if species == 'mouse':
            # use conductance levels determined from Cao et al.,  J. Neurophys., 2007. as 
            # model description in Xie and Manis 2013. Note that
            # conductances were not scaled for temperature (rates were)
            # so here we reset the default Q10's for conductance (g) to 1.0
            if celltype not in ['bushy-II', 'bushy-II-I']:
                raise ValueError('\nCell type %s is not implemented for mouse bushy cells' % celltype)
            # print '  Setting conductances for mouse bushy cell (%s), Xie and Manis, 2013' % celltype
            dataset = 'XM13_channels'
            self.vrange = [-68., -55.]  # set a default vrange for searching for rmp
            self.i_test_range = {'pulse': (-1., 1., 0.05)}
            self._valid_temperatures = (34., )
            if self.status['temperature'] is None:
                self.status['temperature'] = 34. 

            pars = self.get_cellpars(dataset, species=species, celltype=celltype)
            self.set_soma_size_from_Cm(pars.cap)
            self.status['na'] = pars.natype
            self.adjust_na_chans(soma, sf=1.0)
            soma().kht.gbar = nstomho(pars.soma_kht_gbar, self.somaarea)
            soma().klt.gbar = nstomho(pars.soma_klt_gbar, self.somaarea)
            soma().ihvcn.gbar = nstomho(pars.soma_ih_gbar, self.somaarea)
            soma().leak.gbar = nstomho(pars.soma_leak_gbar, self.somaarea)
            self.axonsf = 0.57
            
        elif species == 'guineapig':
            # print '  Setting conductances for guinea pig %s bushy cell, Rothman and Manis, 2003' % modelType
            self._valid_temperatures = (22., 38.)
            if self.status['temperature'] is None:
                self.status['temperature'] = 22. 
            self.i_test_range = {'pulse': (-0.4, 0.4, 0.02)}
            sf = 1.0
            if self.status['temperature'] == 38.:  # adjust for 2003 model conductance levels at 38
                sf = 2  # Q10 of 2, 22->38C. (p3106, R&M2003c)
                # note that kinetics are scaled in the mod file.
            dataset = 'RM03_channels'
            pars = self.get_cellpars(dataset, species=species, celltype=celltype)
            self.set_soma_size_from_Cm(pars.cap)
            self.status['na'] = pars.natype
            self.adjust_na_chans(soma, sf=sf)
            soma().kht.gbar = nstomho(pars.soma_kht_gbar, self.somaarea)
            soma().klt.gbar = nstomho(pars.soma_klt_gbar, self.somaarea)
            soma().ihvcn.gbar = nstomho(pars.soma_ih_gbar, self.somaarea)
            soma().leak.gbar = nstomho(pars.soma_leak_gbar, self.somaarea)

            self.axonsf = 0.57
            
        else:
            errmsg = 'Species "%s" or model type "%s" is not recognized for Bushy cells.' %  (species, modelType)
            errmsg += '\n  Valid species are: \n'
            for s in knownspecies:
                errmsg += '    %s\n' % s
            errmsg += '-'*40
            raise ValueError(errmsg)

        self.status['species'] = species
        self.status['modelType'] = modelType
        self.check_temperature()
#        self.cell_initialize(vrange=self.vrange)  # no need to do this just yet.
        if not silent:
           print ' set cell as: ', species
           print ' with Vm rest = %6.3f' % self.vm0

    def channel_manager(self, modelType='RM03'):
        """
        This routine defines channel density maps and distance map patterns
        for each type of compartment in the cell. The maps
        are used by the ChannelDecorator class (specifically, its private
        \_biophys function) to decorate the cell membrane.
        These settings are only used if the decorator is called; otherwise
        for point cells, the species_scaling routine defines the channel
        densities.
        
        Parameters
        ----------
        modelType : string (default: 'RM03')
            A string that defines the type of the model. Currently, 3 types are implemented:
            RM03: Rothman and Manis, 2003 somatic densities for guinea pig
            XM13: Xie and Manis, 2013, somatic densities for mouse
            mGBC: experimental mouse globular bushy cell with dendrites, axon, hillock and initial segment, for
            use with fully reconstructed neurons.
        
        Returns
        -------
        Nothing
        
        Notes
        -----
        This routine defines the following variables for the class:
        
            * conductances (gBar)
            * a channelMap (dictonary of channel densities in defined anatomical compartments)
            * a current injection range for IV's (used for testing)
            * a distance map, which defines how each conductance in a selected compartment
              changes with distance from the soma. The current implementation includes both
              linear and exponential gradients,
              the minimum conductance at the end of the gradient, and the space constant or
              slope for the gradient.
        
        """
        
        self.c_m = 1E-6  # default in units of F/cm^2
        if modelType == 'RM03':
            #
            # Create a model based on the Rothman and Manis 2003 conductance set from guinea pig
            # 
            self.c_m = 0.9E-6  # default in units of F/cm^2
            self._valid_temperatures = (22., 38.)
            sf = 1.0
            if self.status['temperature'] == None:
                self.status['temperature'] = 22.
            if self.status['temperature'] == 38:
                sf = 3.03
            dataset = 'RM03_channels'
            pars = self.get_cellpars(dataset, species=self.status['species'], celltype='bushy-II')
            refarea = 1e-3*pars.cap / self.c_m
            self.gBar = Params(nabar=sf*pars.soma_na_gbar/refarea, # 1000.0E-9/refarea,
                               khtbar=sf*pars.soma_kht_gbar/refarea,
                               kltbar=sf*pars.soma_klt_gbar/refarea,
                               ihbar=sf*pars.soma_ih_gbar/refarea,
                               leakbar=sf*pars.soma_leak_gbar/refarea,
                              )
            # print 'RM03 gbar:\n', self.gBar.show()
            
            self.channelMap = {
                'axon': {'nacn': self.gBar.nabar, 'klt': self.gBar.kltbar, 'kht': self.gBar.khtbar, 'ihvcn': 0.,
                         'leak': self.gBar.leakbar / 2.},
                'hillock': {'nacn': self.gBar.nabar, 'klt': self.gBar.kltbar, 'kht': self.gBar.khtbar, 'ihvcn': 0.,
                            'leak': self.gBar.leakbar, },
                'initseg': {'nacn': self.gBar.nabar, 'klt': self.gBar.kltbar, 'kht': self.gBar.khtbar,
                            'ihvcn': self.gBar.ihbar / 2., 'leak': self.gBar.leakbar, },
                'soma': {'nacn': self.gBar.nabar, 'klt': self.gBar.kltbar, 'kht': self.gBar.khtbar,
                         'ihvcn': self.gBar.ihbar, 'leak': self.gBar.leakbar, },
                'dend': {'nacn': self.gBar.nabar, 'klt': self.gBar.kltbar * 0.5, 'kht': self.gBar.khtbar * 0.5,
                         'ihvcn': self.gBar.ihbar / 3., 'leak': self.gBar.leakbar * 0.5, },
                'apic': {'nacn': self.gBar.nabar, 'klt': self.gBar.kltbar * 0.2, 'kht': self.gBar.khtbar * 0.2,
                         'ihvcn': self.gBar.ihbar / 4., 'leak': self.gBar.leakbar * 0.2, },
            }
#            self.irange = np.linspace(-1., 1., 21)
            self.distMap = {'dend': {'klt': {'gradient': 'linear', 'gminf': 0., 'lambda': 100.},
                                     'kht': {'gradient': 'linear', 'gminf': 0., 'lambda': 100.},
                                     'nacn': {'gradient': 'exp', 'gminf': 0., 'lambda': 100.}}, # linear with distance, gminf (factor) is multiplied by gbar
                            'apic': {'klt': {'gradient': 'linear', 'gminf': 0., 'lambda': 100.},
                                     'kht': {'gradient': 'linear', 'gminf': 0., 'lambda': 100.},
                                     'nacn': {'gradient': 'exp', 'gminf': 0., 'lambda': 100.}}, # gradients are: flat, linear, exponential
                            }

        elif modelType == 'XM13':
            #
            # Create a model for a mouse bushy cell from Xie and Manis, 2013
            # based on Cao and Oertel mouse conductance values
            # and Rothman and Manis kinetics.
            self.c_m = 0.9E-6  # default in units of F/cm^2
            self._valid_temperatures = (34., )
            if self.status['temperature'] == None:
                self.status['temperature'] = 34.
            dataset = 'XM13_channels'
            pars = self.get_cellpars(dataset, species=self.status['species'], celltype='bushy-II')
            refarea = 1e-3*pars.cap / self.c_m
            self.gBar = Params(nabar=pars.soma_na_gbar/refarea, # 1000.0E-9/refarea,
                               khtbar=pars.soma_kht_gbar/refarea,
                               kltbar=pars.soma_klt_gbar/refarea,
                               ihbar=pars.soma_ih_gbar/refarea,
                               leakbar=pars.soma_leak_gbar/refarea,
                              )
            # print 'XM13 gbar:\n', self.gBar.show()
            self.channelMap = {
                'axon': {'nav11': self.gBar.nabar*1, 'klt': self.gBar.kltbar * 1.0, 'kht': self.gBar.khtbar, 'ihvcn': 0.,
                         'leak': self.gBar.leakbar * 0.25},
                'hillock': {'nav11': self.gBar.nabar*2, 'klt': self.gBar.kltbar, 'kht': self.gBar.khtbar*2.0, 'ihvcn': 0.,
                            'leak': self.gBar.leakbar, },
                'initseg': {'nav11': self.gBar.nabar*3.0, 'klt': self.gBar.kltbar*1, 'kht': self.gBar.khtbar*2,
                            'ihvcn': self.gBar.ihbar * 0.5, 'leak': self.gBar.leakbar, },
                'soma': {'nav11': self.gBar.nabar*0.5, 'klt': self.gBar.kltbar, 'kht': self.gBar.khtbar,
                         'ihvcn': self.gBar.ihbar, 'leak': self.gBar.leakbar, },
                'dend': {'nav11': self.gBar.nabar * 0.25, 'klt': self.gBar.kltbar *0.5, 'kht': self.gBar.khtbar *0.5,
                         'ihvcn': self.gBar.ihbar *0.5, 'leak': self.gBar.leakbar * 0.5, },
                'dendrite': {'nav11': self.gBar.nabar * 0.25, 'klt': self.gBar.kltbar *0.5, 'kht': self.gBar.khtbar *0.5,
                         'ihvcn': self.gBar.ihbar *0.5, 'leak': self.gBar.leakbar * 0.5, },
                'apic': {'nav11': self.gBar.nabar * 0.25, 'klt': self.gBar.kltbar * 0.25, 'kht': self.gBar.khtbar * 0.25,
                         'ihvcn': self.gBar.ihbar *0.25, 'leak': self.gBar.leakbar * 0.25, },
            }
            self.irange = np.linspace(-0.6, 1, 9)
            self.distMap = {'dend': {'klt': {'gradient': 'exp', 'gminf': 0., 'lambda': 50.},
                                     'kht': {'gradient': 'exp', 'gminf': 0., 'lambda': 50.},
                                     'nav11': {'gradient': 'exp', 'gminf': 0., 'lambda': 50.}}, # linear with distance, gminf (factor) is multiplied by gbar
                            'dendrite': {'klt': {'gradient': 'linear', 'gminf': 0., 'lambda': 100.},
                                     'kht': {'gradient': 'linear', 'gminf': 0., 'lambda': 100.},
                                     'nav11': {'gradient': 'linear', 'gminf': 0., 'lambda': 100.}}, # linear with distance, gminf (factor) is multiplied by gbar
                            'apic': {'klt': {'gradient': 'linear', 'gminf': 0., 'lambda': 100.},
                                     'kht': {'gradient': 'linear', 'gminf': 0., 'lambda': 100.},
                                     'nav11': {'gradient': 'exp', 'gminf': 0., 'lambda': 200.}}, # gradients are: flat, linear, exponential
                            }

        elif modelType == 'mGBC':
            # bushy from Xie and Manis, 2013, based on Cao and Oertel mouse conductances,
            # BUT modified ad hoc for SBEM reconstructions.
            dataset = 'mGBC_channels'
            
            self._valid_temperatures = (34.,)
            if self.status['temperature'] == None:
                self.status['temperature'] = 34.
            pars = self.get_cellpars(dataset, species=self.status['species'], celltype='bushy-II')
            refarea = 1e-3*pars.cap / self.c_m
            # print (pars.cap, pars.soma_kht_gbar, refarea)  # refarea should be about 30e-6
            
            self.gBar = Params(nabar=pars.soma_na_gbar/refarea, # 1000.0E-9/refarea,
                               khtbar=pars.soma_kht_gbar/refarea,
                               kltbar=pars.soma_klt_gbar/refarea,
                               ihbar=pars.soma_ih_gbar/refarea,
                               leakbar=pars.soma_leak_gbar/refarea,
                              )
            # print 'mGBC gbar:\n', self.gBar.show()
            sodiumch = 'jsrna'
            self.channelMap = {
                'axon': {sodiumch: self.gBar.nabar*1., 'klt': self.gBar.kltbar * 1.0, 'kht': self.gBar.khtbar, 'ihvcn': 0.,
                         'leak': self.gBar.leakbar * 0.25},
                'unmyelinatedaxon': {sodiumch: self.gBar.nabar*3.0, 'klt': self.gBar.kltbar * 2.0,
                         'kht': self.gBar.khtbar*3.0, 'ihvcn': 0.,
                         'leak': self.gBar.leakbar * 0.25},
                'myelinatedaxon': {sodiumch: self.gBar.nabar*0, 'klt': self.gBar.kltbar * 1e-2,
                         'kht': self.gBar.khtbar*1e-2, 'ihvcn': 0.,
                         'leak': self.gBar.leakbar * 0.25*1e-3},
                'hillock': {sodiumch: self.gBar.nabar*4.0, 'klt': self.gBar.kltbar*1.0, 'kht': self.gBar.khtbar*3.0,
                             'ihvcn': 0., 'leak': self.gBar.leakbar, },
                'initseg': {sodiumch: self.gBar.nabar*3.0, 'klt': self.gBar.kltbar*2, 'kht': self.gBar.khtbar*2,
                            'ihvcn': self.gBar.ihbar * 0.5, 'leak': self.gBar.leakbar, },
                'soma': {sodiumch: self.gBar.nabar*0.65, 'klt': self.gBar.kltbar, 'kht': self.gBar.khtbar*1.5,
                         'ihvcn': self.gBar.ihbar, 'leak': self.gBar.leakbar, },
                'dend': {sodiumch: self.gBar.nabar * 0.2, 'klt': self.gBar.kltbar *1, 'kht': self.gBar.khtbar *1,
                         'ihvcn': self.gBar.ihbar *0.5, 'leak': self.gBar.leakbar * 0.5, },
                'dendrite': {sodiumch: self.gBar.nabar * 0.2, 'klt': self.gBar.kltbar *1, 'kht': self.gBar.khtbar *1,
                         'ihvcn': self.gBar.ihbar *0.5, 'leak': self.gBar.leakbar * 0.5, },
                'apic': {sodiumch: self.gBar.nabar * 0.25, 'klt': self.gBar.kltbar * 0.25, 'kht': self.gBar.khtbar * 0.25,
                         'ihvcn': self.gBar.ihbar *0.25, 'leak': self.gBar.leakbar * 0.25, },
            }
            self.irange = np.arange(-1.5, 2.1, 0.25 )
            self.distMap = {'dend': {'klt': {'gradient': 'linear', 'gminf': 0., 'lambda': 100.},
                                     'kht': {'gradient': 'linear', 'gminf': 0., 'lambda': 100.},
                                     sodiumch: {'gradient': 'linear', 'gminf': 0., 'lambda': 100.}}, # linear with distance, gminf (factor) is multiplied by gbar
                            'dendrite': {'klt': {'gradient': 'linear', 'gminf': 0., 'lambda': 20.},
                                      'kht': {'gradient': 'linear', 'gminf': 0., 'lambda': 20.},
                                      sodiumch: {'gradient': 'linear', 'gminf': 0., 'lambda': 20.}}, # linear with distance, gminf (factor) is multiplied by gbar
                            'apic': {'klt': {'gradient': 'linear', 'gminf': 0., 'lambda': 100.},
                                     'kht': {'gradient': 'linear', 'gminf': 0., 'lambda': 100.},
                                     sodiumch: {'gradient': 'exp', 'gminf': 0., 'lambda': 200.}}, # gradients are: flat, linear, exponential
                            }
        else:
            raise ValueError('model type %s is not implemented' % modelType)
        self.check_temperature()

    def adjust_na_chans(self, soma, sf=1.0, gbar=1000., debug=False):
        """
        adjust the sodium channel conductance
        
        Parameters
        ----------
        soma : neuron section object
            A soma object whose sodium channel complement will have its 
            conductances adjusted depending on the channel type
        
        gbar : float (default: 1000.)
            The maximal conductance for the sodium channel
        
        debug : boolean (false):
            Verbose printing
            
        Returns
        -------
            Nothing :
        
        """
        
        if self.status['ttx']:
            gnabar = 0.0
        else:
            gnabar = nstomho(gbar, self.somaarea)*sf
        nach = self.status['na']
        if nach == 'jsrna':
            soma().jsrna.gbar = gnabar
            soma.ena = self.e_na
            if debug:
                print 'jsrna gbar: ', soma().jsrna.gbar
        elif nach == 'nav11':
            soma().nav11.gbar = gnabar
            soma.ena = 50 # self.e_na
#            print('gnabar: ', soma().nav11.gbar, ' vs: 0.0192307692308')
            soma().nav11.vsna = 4.3
            if debug:
                print "bushy using inva11"
        elif nach in ['na', 'nacn']:
            soma().na.gbar = gnabar
            soma.ena = self.e_na
            if debug:
                print 'na gbar: ', soma().na.gbar
        else:
            raise ValueError('Sodium channel %s is not recognized for Bushy cells', nach)

    def add_axon(self):
        """
        Add a default axon from the generic cell class to the bushy cell (see cell class).
        """
        Cell.add_axon(self, self.c_m, self.R_a, self.axonsf)

    def add_pumps(self):
        """
        Insert mechanisms for potassium ion management, sodium ion management, and a
        sodium-potassium pump at the soma.
        """
        soma = self.soma
        soma.insert('k_conc')

        ki0_k_ion = 140
        soma().ki = ki0_k_ion
        soma().ki0_k_conc = ki0_k_ion
        soma().beta_k_conc = 0.075

        soma.insert('na_conc')
        nai0_na_ion = 5
        soma().nai = nai0_na_ion
        soma().nai0_na_conc = nai0_na_ion
        soma().beta_na_conc = 0.075

        soma.insert('nakpump')
        soma().nakpump.inakmax = 8
        soma().nao = 145
        soma().ko = 5
        soma().nakpump.Nai_inf = 5
        soma().nakpump.Ki_inf = 140
        soma().nakpump.ATPi = 5
        self.status['pumps'] = True

    def add_dendrites(self, debug=False):
        """
        Add a simple dendrite to the bushy cell.
        """
        if debug:
            print 'Adding dendrite to Bushy model'
        section = h.Section
        maindend = section(cell=self.soma)
        maindend.connect(self.soma)
        maindend.nseg = 10
        maindend.L = 100.0
        maindend.diam = 2.5
        maindend.insert('klt')
        maindend.insert('ihvcn')
        maindend().klt.gbar = self.soma().klt.gbar / 2.0
        maindend().ihvcn.gbar = self.soma().ihvcn.gbar / 2.0

        maindend.cm = self.c_m
        maindend.Ra = self.R_a
        nsecd = range(0, 5)
        secdend = []
        for ibd in nsecd:
            secdend.append(section(cell=self.soma))
        for ibd in nsecd:
            secdend[ibd].connect(maindend)
            secdend[ibd].diam = 1.0
            secdend[ibd].L = 15.0
            secdend[ibd].cm = self.c_m
            secdend[ibd].Ra = self.R_a
        self.maindend = maindend
        self.secdend = secdend
        self.status['dendrite'] = True
        if debug:
            print 'Bushy: added dendrite'
            h.topology()
        self.add_section(maindend, 'maindend')
        self.add_section(secdend, 'secdend')

