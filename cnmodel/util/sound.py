"""
Tools for generating auditory stimuli. 
"""
from __future__ import division
import numpy as np
import scipy


def create(type, **kwds):
    """ Create a Sound instance using a key returned by Sound.key().
    """
    cls = globals()[type]
    return cls(**kwds)


class Sound(object):
    """
    Base class for all sound stimulus generators.
    """
    def __init__(self, duration, rate=100e3, **kwds):
        self.opts = {'rate': rate, 'duration': duration}
        self.opts.update(kwds)
        self._time = None
        self._sound = None

    @property
    def sound(self):
        """ The generated sound array expressed in Pascals.
        """
        if self._sound is None:
            self._sound = self.generate()
        return self._sound
        
    @property
    def time(self):
        """ The array of time values expressed in seconds.
        """
        if self._time is None:
            self._time = np.linspace(0, self.opts['duration'], self.num_samples)
        return self._time

    @property 
    def num_samples(self):
        """ The number of samples in the sound array.
        """
        return 1 + int(self.opts['duration'] * self.opts['rate'])
    
    @property
    def dt(self):
        """ The sample period (time step between samples).
        """
        return 1.0 / self.opts['rate']
    
    @property
    def duration(self):
        return self.opts['duration']

    def key(self):
        """ Return dict of parameters needed to completely describe this sound.
        The sound can be recreated using ``create(**key)``.
        """
        k = self.opts.copy()
        k['type'] = self.__class__.__name__
        return k

    def measure_dbspl(self, tstart, tend):
        """ Return the measured amplitude (dBSPL) of the sound from tstart to tend
        (both specified in seconds). 
        """
        istart = int(tstart * self.opts['rate'])
        iend = int(tend * self.opts['rate'])
        return pa_to_dbspl(self.sound[istart:iend].std())

    def generate(self):
        """
        Generate and return the sound output. This method is defined by subclasses.
        """
        raise NotImplementedError()

    def __getattr__(self, name):
        if 'opts' not in self.__dict__:
            raise AttributeError(name)
        if name in self.opts:
            return self.opts[name]
        else:
            return object.__getattr__(self, name)


class TonePip(Sound):
    """ One or more tone pips with cosine-ramped edges.
    
    Parameters
    ----------
    rate : float
        Sample rate in Hz
    duration : float
        Total duration of the sound
    f0 : float or array-like
        Tone frequency in Hz. Must be less than half of the sample rate.
    dbspl : float
        Maximum amplitude of tone in dB SPL. 
    pip_duration : float
        Duration of each pip including ramp time. Must be at least 
        2 * ramp_duration.
    pip_start : array-like
        Start times of each pip
    ramp_duration : float
        Duration of a single ramp period (from minimum to maximum). 
        This may not be more than half of pip_duration.
    """
    def __init__(self, **kwds):
        for k in ['rate', 'duration', 'f0', 'dbspl', 'pip_duration', 'pip_start', 'ramp_duration']:
            if k not in kwds:
                raise TypeError("Missing required argument '%s'" % k)
        if kwds['pip_duration'] < kwds['ramp_duration'] * 2:
            raise ValueError("pip_duration must be greater than (2 * ramp_duration).")
        if kwds['f0'] > kwds['rate'] * 0.5:
            raise ValueError("f0 must be less than (0.5 * rate).")
        
        Sound.__init__(self, **kwds)
        
    def generate(self):
        o = self.opts
        return piptone(self.time, o['ramp_duration'], o['rate'], o['f0'], 
                       o['dbspl'], o['pip_duration'], o['pip_start'])
    
class FMSweep(Sound):
    """ an FM sweep between to frequenceis.
    
    Parameters
    ----------
    rate : float
        Sample rate in Hz
    duration : float
        Total duration of the sweep
    start : float
        t times of each pip
    freqs : list 
        [f0, f1]: the start and stop times for the sweep
    ramp : string
        valid input for type of sweep (linear, logarithmic, etc)
    dbspl : float
        Maximum amplitude of pip in dB SPL.
    """
    def __init__(self, **kwds):
        for k in ['rate', 'duration', 'start', 'freqs', 'ramp', 'dbspl']:
            if k not in kwds:
                raise TypeError("Missing required argument '%s'" % k)
        
        Sound.__init__(self, **kwds)
        
    def generate(self):
        o = self.opts
        return fmsweep(self.time, o['start'], o['duration'],
                         o['freqs'], o['ramp'], o['rate'], o['dbspl'])


def fmsweep(t, start, duration, freqs, ramp, rate, dBSPL):
    """
    """
    sw = scipy.signal.chirp(t, freqs[0], duration, freqs[1],
        method=ramp, phi=0, vertex_zero=True)
    sw = np.sqrt(2) * dbspl_to_pa(dBSPL) * sw
    return sw



class NoisePip(Sound):
    """ One or more gaussian noise pips with cosine-ramped edges.
    
    Parameters
    ----------
    rate : float
        Sample rate in Hz
    duration : float
        Total duration of the sound
    seed : int >= 0
        Random seed
    dbspl : float
        Maximum amplitude of pip in dB SPL. 
    pip_duration : float
        Duration of each pip including ramp time. Must be at least 
        2 * ramp_duration.
    pip_start : array-like
        Start times of each pip
    ramp_duration : float
        Duration of a single ramp period (from minimum to maximum). 
        This may not be more than half of pip_duration.
    """
    def __init__(self, **kwds):
        for k in ['rate', 'duration', 'seed', 'pip_duration', 'pip_start', 'ramp_duration']:
            if k not in kwds:
                raise TypeError("Missing required argument '%s'" % k)
        if kwds['pip_duration'] < kwds['ramp_duration'] * 2:
            raise ValueError("pip_duration must be greater than (2 * ramp_duration).")
        if kwds['seed'] < 0:
            raise ValueError("Random seed must be integer > 0")
        
        Sound.__init__(self, **kwds)
        
    def generate(self):
        o = self.opts
        return pipnoise(self.time, o['ramp_duration'], o['rate'],
                        o['dbspl'], o['pip_duration'], o['pip_start'], o['seed'])
    

class SAMNoise(Sound):
    """ One or more gaussian noise pips with cosine-ramped edges.
    
    Parameters
    ----------
    rate : float
        Sample rate in Hz
    duration : float
        Total duration of the sound
    seed : int >= 0
        Random seed
    dbspl : float
        Maximum amplitude of pip in dB SPL. 
    pip_duration : float
        Duration of each pip including ramp time. Must be at least 
        2 * ramp_duration.
    pip_start : array-like
        Start times of each pip
    ramp_duration : float
        Duration of a single ramp period (from minimum to maximum). 
        This may not be more than half of pip_duration.
    fmod : float
        SAM modulation frequency
    dmod : float
        Modulation depth
    """
    def __init__(self, **kwds):
        parms = ['rate', 'duration', 'seed', 'pip_duration', 
                 'pip_start', 'ramp_duration', 'fmod', 'dmod', 'seed']
        for k in parms:
            if k not in kwds:
                raise TypeError("Missing required argument '%s'" % k)
        if kwds['pip_duration'] < kwds['ramp_duration'] * 2:
            raise ValueError("pip_duration must be greater than (2 * ramp_duration).")
        if kwds['seed'] < 0:
            raise ValueError("Random seed must be integer > 0")
        
        Sound.__init__(self, **kwds)
        
    def generate(self):
        o = self.opts
        o['phaseshift'] = 0.
        return modnoise(self.time, o['ramp_duration'], o['rate'], o['f0'], 
                       o['pip_duration'], o['pip_start'], o['dbspl'],
                       o['fmod'], o['dmod'], 0., o['seed'])

def modnoise(t, rt, Fs, F0, dur, start, dBSPL, FMod, DMod, phaseshift, seed):
    irpts = rt * Fs
    mxpts = len(t)+1
    pin = pipnoise(t, rt, Fs, dBSPL, dur, start, seed)
    env = (1 + (DMod/100.0) * np.sin((2*np.pi*FMod*t) - np.pi/2 + phaseshift)) # envelope...

    pin = ramp(pin, mxpts, irpts)
    env = ramp(env, mxpts, irpts)
    return pin*env

                        
class ClickTrain(Sound):
    """
    Parameters
    ----------
    rate : float
        sample frequency (Hz)
    click_starts : float (seconds)
        array of start time for clicks 
    click_duration : float (seconds)
        duration of each click
    dbspl : float
        maximum sound pressure level of pip    
    
    """
    def __init__(self, **kwds):
        for k in ['click_starts', 'click_duration', 'dbspl', 'rate']:
            if k not in kwds:
                raise TypeError("Missing rquired argument '%s'" % k)
        Sound.__init__(self, **kwds)
        
    def generate(self):
        o = self.opts
        return clicks(self.time, o['rate'], o['click_starts'], o['click_duration'], o['dbspl'])


def pa_to_dbspl(pa, ref=20e-6):
    """ Convert Pascals (rms) to dBSPL. By default, the reference pressure is
    20 uPa.
    """
    return 20 * np.log10(pa / ref)


def dbspl_to_pa(dbspl, ref=20e-6):
    """ Convert dBSPL to Pascals (rms). By default, the reference pressure is
    20 uPa.
    """
    return ref * 10**(dbspl / 20)


class SAMTone(Sound):
    """ SAM tones with cosine-ramped edges.
    
    Parameters
    ----------
    rate : float
        Sample rate in Hz
    duration : float
        Total duration of the sound
    f0 : float or array-like
        Tone frequency in Hz. Must be less than half of the sample rate.
    dbspl : float
        Maximum amplitude of tone in dB SPL. 
    pip_duration : float
        Duration of each pip including ramp time. Must be at least 
        2 * ramp_duration.
    pip_start : array-like
        Start times of each pip
    ramp_duration : float
        Duration of a single ramp period (from minimum to maximum). 
        This may not be more than half of pip_duration.
    fMod : float
        SAM modulation frequency
    fMod : float
        Modulation depth
        
    """
    def __init__(self, **kwds):
        for k in ['rate', 'duration', 'f0', 'dbspl', 'ramp_duration', 'fmod', 'dmod']:
            if k not in kwds:
                raise TypeError("Missing required argument '%s'" % k)
        if kwds['pip_duration'] < kwds['ramp_duration'] * 2:
            raise ValueError("pip_duration must be greater than (2 * ramp_duration).")
        if kwds['f0'] > kwds['rate'] * 0.5:
            raise ValueError("f0 must be less than (0.5 * rate).")
        
        Sound.__init__(self, **kwds)
        
    def generate(self):
        o = self.opts
        return modtone(self.time, o['ramp_duration'], o['rate'], o['f0'], 
                       o['dbspl'], o['fmod'], o['dmod'], 0.) # o['pip_duration'], o['pip_start'],)

def modtone(t, rt, Fs, F0, dBSPL, FMod, DMod, phaseshift):
    """
    Generate an amplitude-modulated tone with linear ramps.
    
    Parameters
    ----------
    t : array
        array of waveform time values
    rt : float
        ramp duration
    Fs : float
        sample rate
    F0 : float
        tone frequency
    FMod : float
        modulation frequency
    DMod : float
        modulation depth percent
    phaseshift : float
        modulation phase
    
    Original (adapted from Manis; makeANF_CF_RI.m)::
    
        function [pin, env] = modtone(t, rt, Fs, F0, dBSPL, FMod, DMod, phaseshift)
            % fprintf(1, 'Phase: %f\n', phaseshift)
            irpts = rt*Fs;
            mxpts = length(t);
            env = (1 + (DMod/100.0)*sin((2*pi*FMod*t)-pi/2+phaseshift)); % envelope...
            pin = np.sqrt(2)*20e-6*10^(dBSPL/20)*(sin((2*pi*F0*t)-pi/2).*env); % unramped stimulus

            pin = ramp(pin, mxpts, irpts);
            env = ramp(env, mxpts, irpts);
            %pin(1:irpts)=pin(1:irpts).*(0:(irpts-1))/irpts;
            %pin((mxpts-irpts):mxpts)=pin((mxpts-irpts):mxpts).*(irpts:-1:0)/irpts;
            return
        end
    """
    irpts = rt * Fs
    mxpts = len(t)+1
    
    # TODO: is this envelope correct? For dmod=100, the envelope max is 2.
    # I would have expected something like  (dmod/100) * 0.5 * (sin + 1)
    env = (1 + (DMod/100.0) * np.sin((2*np.pi*FMod*t) - np.pi/2 + phaseshift)) # envelope...
    
    pin = (np.sqrt(2) * dbspl_to_pa(dBSPL)) * np.sin((2*np.pi*F0*t) - np.pi/2) * env # unramped stimulus
    pin = ramp(pin, mxpts, irpts)
    env = ramp(env, mxpts, irpts)
    return pin*env


def ramp(pin, mxpts, irpts):
    """
    Apply linear ramps to *pin*.
    
    Original (adapted from Manis; makeANF_CF_RI.m)::
    
        function [out] = ramp(pin, mxpts, irpts)
            out = pin;
            out(1:irpts)=pin(1:irpts).*(0:(irpts-1))/irpts;
            out((mxpts-irpts):mxpts)=pin((mxpts-irpts):mxpts).*(irpts:-1:0)/irpts;
            return;
        end
    """
    out = pin.copy()
    r = np.linspace(0, 1, irpts)
    out[:irpts] = out[:irpts]*r
    out[mxpts-irpts:mxpts] = out[mxpts-irpts:mxpts] * r[::-1]
    return out

def pipnoise(t, rt, Fs, dBSPL, pip_dur, pip_start, seed):
    """
    Create a waveform with multiple sine-ramped noise pips. Output is in 
    Pascals.
    
    Parameters
    ----------
    t : array
        array of time values
    rt : float
        ramp duration 
    Fs : float
        sample rate
    dBSPL : float
        maximum sound pressure level of pip
    pip_dur : float
        duration of pip including ramps
    pip_start : float
        list of starting times for multiple pips
    seed : int
        random seed
    """
    rng = np.random.RandomState(seed)
    pin = np.zeros(t.size)
    for start in pip_start:
        # make pip template
        pip_pts = int(pip_dur * Fs) + 1
        pip = dbspl_to_pa(dBSPL) * rng.randn(pip_pts)  # unramped stimulus

        # add ramp
        ramp_pts = int(rt * Fs) + 1
        ramp = np.sin(np.linspace(0, np.pi/2., ramp_pts))**2
        pip[:ramp_pts] *= ramp
        pip[-ramp_pts:] *= ramp[::-1]
        
        ts = int(np.floor(start * Fs))
        pin[ts:ts+pip.size] += pip

    return pin
        
   
def piptone(t, rt, Fs, F0, dBSPL, pip_dur, pip_start):
    """
    Create a waveform with multiple sine-ramped tone pips. Output is in 
    Pascals.
    
    Parameters
    ----------
    t : array
        array of time values
    rt : float
        ramp duration 
    Fs : float
        sample rate
    F0 : float
        pip frequency
    dBSPL : float
        maximum sound pressure level of pip
    pip_dur : float
        duration of pip including ramps
    pip_start : float
        list of starting times for multiple pips
    """
    # make pip template
    pip_pts = int(pip_dur * Fs) + 1
    pip_t = np.linspace(0, pip_dur, pip_pts)
    pip = np.sqrt(2) * dbspl_to_pa(dBSPL) * np.sin(2*np.pi*F0*pip_t)  # unramped stimulus

    # add ramp
    ramp_pts = int(rt * Fs) + 1
    ramp = np.sin(np.linspace(0, np.pi/2., ramp_pts))**2
    pip[:ramp_pts] *= ramp
    pip[-ramp_pts:] *= ramp[::-1]
    
    # apply template to waveform
    pin = np.zeros(t.size)
    for start in pip_start:
        ts = int(np.floor(start * Fs))
        pin[ts:ts+pip.size] += pip

    return pin


def clicks(t, Fs, click_starts, click_duration, dbspl):
    """
    Create a waveform with clicks. Output is in 
    Pascals.

    Parameters
    ----------
    t : array
        array of time values
    Fs : float
        sample frequency (Hz)
    click_starts : float (seconds)
        array of start time for clicks 
    click)duration : float (seconds)
        duration of each click
    dspl : float
        maximum sound pressure level of pip
    """
    totdur = np.max(click_starts) + click_duration
    click_pts = int(totdur * Fs) + 1
    swave = np.zeros(t.size)
    for start_time in click_starts:
        t0 = int(np.floor(start_time * Fs))
        t1 = t0 + int(np.floor(click_duration * Fs))
        swave[t0:t1] = dbspl_to_pa(dbspl)
    return swave

    