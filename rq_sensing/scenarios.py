"""Synthetic benchmark fixtures; truth is never provided to the matcher."""
import numpy as np
from .navigation import MagneticMap

def environment_field(x,y):
    # Fictional fixed-axis field, not a surveyed terrestrial magnetic map.
    return 60+10*np.sin(x/55)+8*np.cos(y/42)+7*np.sin((x+y)/80)+12*np.exp(-((x-350)**2+(y-280)**2)/(2*70**2))

def make_map(flat=False):
    x=np.arange(0,801,5.); y=np.arange(0,601,5.); xx,yy=np.meshgrid(x,y)
    return MagneticMap(x,y,np.full_like(xx,60.) if flat else environment_field(xx,yy))

def trajectory(steps=60):
    if not isinstance(steps,int) or steps<2: raise ValueError('At least two steps needed')
    u=np.linspace(0,1,steps)
    return np.column_stack([120+420*u,200+70*np.sin(2*np.pi*u)+100*u])

def displacement_stream(truth,seed):
    rng=np.random.default_rng(seed)
    delta=np.vstack([np.zeros(2),np.diff(truth,axis=0)])
    delta[1:]+=np.array([.65,-.4])+rng.normal(0,.35,delta[1:].shape)
    return delta
