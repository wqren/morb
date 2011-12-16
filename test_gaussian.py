import morb
from morb import rbms, stats, param_updaters, trainers, monitors, units, parameters

import theano
import theano.tensor as T

import numpy as np
import time

import matplotlib.pyplot as plt
plt.ion()

from test_utils import generate_data, get_context


# DEBUGGING

from theano import ProfileMode
# mode = theano.ProfileMode(optimizer='fast_run', linker=theano.gof.OpWiseCLinker())
# mode = theano.compile.DebugMode(check_py_code=False, require_matching_strides=False)
mode = None

# generate data
data = generate_data(200)

# use the predefined binary-binary RBM, which has visible units (rbm.v), hidden units (rbm.h),
# a weight matrix W connecting them (rbm.W), and visible and hidden biases (rbm.bv and rbm.bh).
n_visible = data.shape[1]
n_hidden = 100

class CustomGaussianBinaryRBM(morb.base.RBM):
    def __init__(self, n_visible, n_hidden):
        super(CustomGaussianBinaryRBM, self).__init__()
        # data shape
        self.n_visible = n_visible
        self.n_hidden = n_hidden
        # units
        CustomGaussianUnits = units.gaussian_units_type(0.5, mean_field=False)
        self.v = CustomGaussianUnits(self, name='v') # visibles
        self.h = units.BinaryUnits(self, name='h') # hiddens
        # parameters
        self.W = parameters.ProdParameters(self, [self.v, self.h], theano.shared(value = self._initial_W(), name='W'), name='W') # weights
        self.bv = parameters.BiasParameters(self, self.v, theano.shared(value = self._initial_bv(), name='bv'), name='bv') # visible bias
        self.bh = parameters.BiasParameters(self, self.h, theano.shared(value = self._initial_bh(), name='bh'), name='bh') # hidden bias
        
    def _initial_W(self):
        return np.asarray( np.random.uniform(
                   low   = -4*np.sqrt(6./(self.n_hidden+self.n_visible)),
                   high  =  4*np.sqrt(6./(self.n_hidden+self.n_visible)),
                   size  =  (self.n_visible, self.n_hidden)),
                   dtype =  theano.config.floatX)
        
    def _initial_bv(self):
        return np.zeros(self.n_visible, dtype = theano.config.floatX)
        
    def _initial_bh(self):
        return np.zeros(self.n_hidden, dtype = theano.config.floatX)


rbm = CustomGaussianBinaryRBM(n_visible, n_hidden)

initial_vmap = { rbm.v: T.matrix('v') }

# We use single-step contrastive divergence (CD-1) to train the RBM. For this, we can use
# the CDParamUpdater. This requires symbolic CD-1 statistics:
s = stats.cd_stats(rbm, initial_vmap, visible_units=[rbm.v], hidden_units=[rbm.h], k=1)

# We create a ParamUpdater for each Parameters instance.
umap = {}
for params in rbm.params_list:
    pu =  0.001 * param_updaters.CDParamUpdater(params, s) # the learning rate is 0.001
    umap[params] = pu
 
# training
t = trainers.MinibatchTrainer(rbm, umap)
mse = monitors.reconstruction_mse(s, rbm.v)
train = t.compile_function(initial_vmap, mb_size=32, monitors=[mse], name='train', mode=mode)

epochs = 200

start_time = time.time()
for epoch in range(epochs):
    print "Epoch %d" % epoch
    costs = [m for m in train({ rbm.v: data })]
    print "MSE = %.4f" % np.mean(costs)

print "Took %.2f seconds" % (time.time() - start_time)