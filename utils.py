
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf

import collections
import hashlib
import numbers

from tensorflow.python.framework import constant_op
from tensorflow.python.framework import dtypes
from tensorflow.python.framework import ops
from tensorflow.python.framework import tensor_shape
from tensorflow.python.framework import tensor_util
from tensorflow.python.layers import base as base_layer
from tensorflow.python.ops import array_ops
from tensorflow.python.ops import clip_ops
from tensorflow.python.ops import init_ops
from tensorflow.python.ops import math_ops
from tensorflow.python.ops import nn_ops
from tensorflow.python.ops import partitioned_variables
from tensorflow.python.ops import random_ops
from tensorflow.python.ops import variable_scope as vs
from tensorflow.python.ops import variables as tf_variables
from tensorflow.python.platform import tf_logging as logging
from tensorflow.python.util import nest


class ResidualWrapper(tf.contrib.rnn.RNNCell):
  """RNNCell wrapper that ensures cell inputs are added to the outputs."""

  def __init__(self, cell, residual_fn=None):
    """Constructs a `ResidualWrapper` for `cell`.
    Args:
      cell: An instance of `RNNCell`.
      residual_fn: (Optional) The function to map raw cell inputs and raw cell
        outputs to the actual cell outputs of the residual network.
        Defaults to calling nest.map_structure on (lambda i, o: i + o), inputs
        and outputs.
    """
    self._cell = cell
    self._residual_fn = residual_fn

  @property
  def state_size(self):
    return self._cell.state_size

  @property
  def output_size(self):
    return self._cell.output_size

  def zero_state(self, batch_size, dtype):
    with ops.name_scope(type(self).__name__ + "ZeroState", values=[batch_size]):
      return self._cell.zero_state(batch_size, dtype)

  def __call__(self, inputs, state, scope=None):
    """Run the cell and then apply the residual_fn on its inputs to its outputs.
    Args:
      inputs: cell inputs.
      state: cell state.
      scope: optional cell scope.
    Returns:
      Tuple of cell outputs and new state.
    Raises:
      TypeError: If cell inputs and outputs have different structure (type).
      ValueError: If cell inputs and outputs have different structure (value).
    """
    outputs, new_state = self._cell(inputs, state, scope=scope)
    # Ensure shapes match
    def assert_shape_match(inp, out):
      inp.get_shape().assert_is_compatible_with(out.get_shape())
    def default_residual_fn(inputs, outputs):
      nest.assert_same_structure(inputs, outputs)
      nest.map_structure(assert_shape_match, inputs, outputs)
      return nest.map_structure(lambda inp, out: inp + out, inputs, outputs)
    res_outputs = (self._residual_fn or default_residual_fn)(inputs, outputs)
    return (res_outputs, new_state)