from typing import Tuple, Callable, Optional, TypeVar, Any, cast, Union

from ..model import Model
from ..config import registry
from ..util import get_width
from ..types import Ragged, Padded, Array

InT = TypeVar("InT")
OutT = TypeVar("OutT")
Mid1T = TypeVar("Mid1T")
Mid2T = TypeVar("Mid2T")

# TODO: Unhack this when we can
# We currently have an issue with Pydantic when arguments have generic types.
# https://github.com/samuelcolvin/pydantic/issues/1158
# For now we work around the issue by applying the decorator to this blander
# version of the function.
@registry.layers("chain.v0")
def chain_no_types(*layer: Model) -> Model:
    return chains(*layer)

# This implementation is named 'chains' because we have a type-shennanigans
# function 'chain' below.
def chains(layer1: Model[InT, Mid1T], layer2: Model[Mid1T, Any], *layers: Model) -> Model[InT, Any]:
    """Compose two models `f` and `g` such that they become layers of a single
    feed-forward model that computes `g(f(x))`.
    Also supports chaining more than 2 layers.
    """
    layers = (layer1, layer2) + layers
    if layers[0]._func is forward:
        layers[0].layers.extend(layers[1:])
        return layers[0]
    model: Model[InT, Any] = Model(
        ">>".join(layer.name for layer in layers),
        forward,
        init=init,
        dims={"nO": None, "nI": None},
        layers=layers,
    )
    if layers[0].has_dim("nI") and layers[-1].has_dim("nO"):
        model.initialize()
    return model


def forward(model: Model[InT, OutT], X: InT, is_train: bool) -> Tuple[OutT, Callable]:
    """Apply the layers of `model` in sequence, feeding the output from one
    layer into the next.
    """
    callbacks = []
    for layer in model.layers:
        Y, inc_layer_grad = layer(X, is_train=is_train)
        callbacks.append(inc_layer_grad)
        X = Y

    def backprop(dY: OutT) -> InT:
        for callback in reversed(callbacks):
            dX = callback(dY)
            dY = dX
        return dX

    return Y, backprop


def init(model: Model, X: Optional[InT] = None, Y: Optional[OutT] = None) -> None:
    if not model.layers:
        return
    if X is None and Y is None:
        for layer in model.layers:
            layer.initialize()
        if model.layers[0].has_dim("nI"):
            model.set_dim("nI", model.layers[0].get_dim("nI"))
        if model.layers[-1].has_dim("nO"):
            model.set_dim("nO", model.layers[-1].get_dim("nO"))
        return
    # Try to set nO on each layer, where available.
    nO = None
    if Y is not None and isinstance(Y, (Ragged, Padded, Array, list)):
        nO = get_width(Y)
    elif model.has_dim("nO"):
        nO = model.get_dim("nO")
    for layer in reversed(model.layers):
        if nO is not None and layer.has_dim("nO") is None:
            layer.set_dim("nO", nO)
        if layer.has_dim("nI"):
            nO = layer.get_dim("nI")
        else:
            break
    for layer in model.layers[:-1]:
        layer.initialize(X=X)
        if X is not None:
            X = layer.predict(X)
    model.layers[-1].initialize(X=X, Y=Y)
    if model.layers[0].has_dim("nI"):
        model.set_dim("nI", model.layers[0].get_dim("nI"))
    if model.layers[-1].has_dim("nO"):
        model.set_dim("nO", model.layers[-1].get_dim("nO"))


# Unfortunately mypy doesn't support type-level checking on the cardinality
# of variadic arguments: in other words, if you have an *args, you can't have
# a type-checked condition on len(args). But we *can* get sneaky:
# you can have a type-checked condition on *optional* args, and these *will*
# get read by mypy. Hence the trickery below.

Mid3T = TypeVar("Mid3T")
Mid4T = TypeVar("Mid4T")
Mid5T = TypeVar("Mid5T")
Mid6T = TypeVar("Mid6T")
Mid7T = TypeVar("Mid7T")
Mid8T = TypeVar("Mid8T")
Mid9T = TypeVar("Mid9T")


def chain(
    l1: Model[InT, Mid1T],
    l2: Model[Mid1T, Mid2T],
    l3: Optional[Model[Mid2T, Mid3T]] = None,
    l4: Optional[Model[Mid3T, Mid4T]] = None,
    l5: Optional[Model[Mid4T, Mid5T]] = None,
    l6: Optional[Model[Mid5T, Mid6T]] = None,
    l7: Optional[Model[Mid6T, Mid7T]] = None,
    l8: Optional[Model[Mid7T, Mid8T]] = None,
    l9: Optional[Model[Mid8T, Mid9T]] = None,
    *etc: Model
) -> Model[InT, Any]:
    if l3 is None:
        return chains(l1, l2)
    elif l4 is None:
        return chains(l1, l2, l3)
    elif l5 is None:
        return chains(l1, l2, l3, l4)
    elif l6 is None:
        return chains(l1, l2, l3, l4, l5)
    elif l7 is None:
        return chains(l1, l2, l3, l4, l5, l6)
    elif l8 is None:
        return chains(l1, l2, l3, l4, l5, l6, l7)
    elif l9 is None:
        return chains(l1, l2, l3, l4, l5, l6, l7, l8)
    else:
        return chains(l1, l2, l3, l4, l5, l6, l7, l8, l9, *etc)
