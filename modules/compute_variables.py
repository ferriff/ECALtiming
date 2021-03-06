import pandas as pd
import numpy as np

def effective_amplitude(A1, n1, A2, n2):
	A1n = A1.div(n1)
	A2n = A2.div(n2)
	effA = (A1n*A2n)/np.sqrt(np.square(A1n)+np.square(A2n))
	return effA

def relative_response(laser, alpha):
	return np.power(laser, -alpha)

def delta_phi(phi1, phi2):
	delta = phi1-phi2
	delta_modPi = np.where(delta < -3.14, delta + 6.28, 
		np.where(delta < -3.14, delta - 6.28, delta))
	return delta_modPi

#effective sigma
def effs(v):
   n = v.size
   if n < 2:
       return 0.
   v = v.sort_values()
   s = int(round(0.68269 * n))
   d_min = v.iloc[s] - v.iloc[0]
   diff = v.diff(periods = s)
   return min(d_min, diff.min()) / 2.


def corr_time(vtx, eta, t):
	c = 0.0299792458
	# D        = 
	130*np.cosh(eta)
	# costheta = np.tanh(eta)
	tp = t - (np.sqrt(130*np.cosh(eta)*130*np.cosh(eta) + vtx*vtx - 2*(vtx)*130*np.cosh(eta)*np.tanh(eta)) - 130*np.cosh(eta))*c
	return tp


