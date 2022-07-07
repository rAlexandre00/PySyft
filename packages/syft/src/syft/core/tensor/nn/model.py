# third party
import numpy as np

# relative
from ...common.serde.serializable import serializable
from ..tensor import Tensor
from .layers.base import Layer
from .loss import BinaryCrossEntropy
from .optimizers import Adamax


@serializable(recursive_serde=True)
class Model:
    __attr_allowlist__ = [
        "layers",
        "loss",
        "optimizer",
    ]

    def __init__(self, layers=None):
        self.layers = [] if layers is None else layers

        self.loss = None
        self.optimizer = Adamax

    def add(self, layer):
        assert isinstance(layer, Layer), "PySyft doesn't recognize this kind of layer."
        self.layers.append(layer)

    def compile(self, loss=BinaryCrossEntropy(), optimizer=Adamax()):
        self.layers[0].first_layer = True

        prev_layer = None
        for _, layer in enumerate(self.layers):
            layer.connect_to(prev_layer)
            prev_layer = layer

        self.loss = loss
        self.optimizer = optimizer

    def fit(
        self,
        X,
        Y,
        max_iter=100,
        batch_size=64,
        shuffle=True,
        validation_split=0.0,
        validation_data=None,
    ) -> None:
        print("Started Training")

        if isinstance(X, Tensor):
            X = X.child
        if isinstance(Y, Tensor):
            Y = Y.child

        # prepare data
        train_X = X  # .astype(get_dtype()) if np.issubdtype(np.float64, X.dtype) else X
        train_Y = Y  # .astype(get_dtype()) if np.issubdtype(np.float64, Y.dtype) else Y

        if 1.0 > validation_split > 0.0:
            split = int(train_Y.shape[0] * validation_split)
            valid_X, valid_Y = train_X[-split:], train_Y[-split:]
            train_X, train_Y = train_X[:-split], train_Y[:-split]
        elif validation_data is not None:
            valid_X, valid_Y = validation_data
        else:
            valid_X, valid_Y = None, None

        iter_idx = 0
        while iter_idx < max_iter:
            iter_idx += 1

            # train
            train_losses, train_predicts, train_targets = [], [], []
            for b in range(train_Y.shape[0] // batch_size):
                batch_begin = b * batch_size
                batch_end = batch_begin + batch_size
                x_batch = train_X[batch_begin:batch_end]
                y_batch = train_Y[batch_begin:batch_end]

                # forward propagation
                y_pred = self.predict(x_batch)

                # backward propagation
                next_grad = self.loss.backward(y_pred, y_batch)
                for layer in self.layers[::-1]:
                    print("Backward layer", layer)
                    next_grad = layer.backward(next_grad)

                # update parameters
                self.optimizer.update(self.layers)

                # got loss and predict
                train_losses.append(self.loss.forward(y_pred, y_batch))
                # train_predicts.extend(y_pred)
                # train_targets.extend(y_batch)

            # output train status
            # runout = "iter %d, train-[loss %.4f, acc %.4f]; " % (
            #     iter_idx,
            #     float(np.mean(train_losses)),
            #     float(self.accuracy(train_predicts, train_targets)),
            # )

            # runout = "iter %d, train-[loss %.4f, ]; " % (
            #     iter_idx, float(np.mean(train_losses)))

            if valid_X is not None and valid_Y is not None:
                # valid
                valid_losses, valid_predicts, valid_targets = [], [], []
                for b in range(valid_X.shape[0] // batch_size):
                    batch_begin = b * batch_size
                    batch_end = batch_begin + batch_size
                    x_batch = valid_X[batch_begin:batch_end]
                    y_batch = valid_Y[batch_begin:batch_end]

                    # forward propagation
                    y_pred = self.predict(x_batch)

                    # got loss and predict
                    valid_losses.append(self.loss.forward(y_pred, y_batch))
                    valid_predicts.extend(y_pred)
                    valid_targets.extend(y_batch)

                # output valid status
                # runout += "valid-[loss %.4f, acc %.4f]; " % (
                #     float(np.mean(valid_losses)),
                #     float(self.accuracy(valid_predicts, valid_targets)),
                # )

    def step(self, x_batch, y_batch):
        # forward propagation
        y_pred = self.predict(x_batch)

        # backward propagation
        next_grad = self.loss.backward(y_pred, y_batch)
        for layer in self.layers[::-1]:
            print("Backward layer", layer)
            next_grad = layer.backward(next_grad)

        # update parameters
        self.optimizer.update(self.layers)

        # got loss and predict
        loss = self.loss.forward(y_pred, y_batch)

        return loss

    def predict(self, X):
        """Calculate an output Y for the given input X."""
        x_next = X
        for layer in self.layers[:]:
            print("Forward layer", layer)
            x_next = layer.forward(x_next)
        y_pred = x_next
        return y_pred

    def accuracy(self, outputs, targets):
        y_predicts = np.argmax(outputs, axis=1)
        y_targets = np.argmax(targets, axis=1)
        acc = y_predicts == y_targets
        return np.mean(acc)

    def evaluate(self, X, Y):
        raise NotImplementedError()
