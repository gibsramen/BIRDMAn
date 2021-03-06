import numpy as np
import pytest
import xarray as xr

from birdman import model_util as mu


class TestToInference:
    def dataset_comparison(self, model, ds):
        coord_names = ds.coords._names
        assert coord_names == {"feature", "draw", "covariate", "chain"}
        assert set(ds["beta"].shape) == {2, 28, 4, 100}
        assert set(ds["phi"].shape) == {28, 4, 100}

        exp_feature_names = model.table.ids(axis="observation")
        ds_feature_names = ds.coords["feature"]
        assert (exp_feature_names == ds_feature_names).all()

        exp_coord_names = [
            "Intercept",
            "host_common_name[T.long-tailed macaque]"
        ]
        ds_coord_names = ds.coords["covariate"]
        assert (exp_coord_names == ds_coord_names).all()

        assert (ds.coords["draw"] == np.arange(100)).all()
        assert (ds.coords["chain"] == [0, 1, 2, 3]).all()

    def test_serial_to_inference(self, example_model):
        inf = mu.single_fit_to_inference(
            fit=example_model.fit,
            coords={
                "feature": example_model.feature_names,
                "covariate": example_model.colnames
            },
            dims={
                "beta": ["covariate", "feature"],
                "phi": ["feature"]
            },
            params=["beta", "phi"],
            alr_params=["beta"]
        )
        self.dataset_comparison(example_model, inf.posterior)

    def test_parallel_to_inference(self, example_parallel_model):
        inf = mu.multiple_fits_to_inference(
            fits=example_parallel_model.fit,
            params=["beta", "phi"],
            coords={
                "feature": example_parallel_model.feature_names,
                "covariate": example_parallel_model.colnames
            },
            dims={
                "beta": ["covariate", "feature"],
                "phi": ["feature"]
            },
            concatenation_name="feature",
            feature_names=example_parallel_model.feature_names
        )
        self.dataset_comparison(example_parallel_model, inf.posterior)

    def test_parallel_to_inference_wrong_concat(self, example_parallel_model):
        with pytest.raises(ValueError) as excinfo:
            mu.multiple_fits_to_inference(
                fits=example_parallel_model.fit,
                params=["beta", "phi"],
                coords={
                    "feature": example_parallel_model.feature_names,
                    "covariate": example_parallel_model.colnames
                },
                dims={
                    "beta": ["covariate", "feature"],
                    "phi": ["feature"]
                },
                concatenation_name="mewtwo",
                feature_names=example_parallel_model.feature_names
            )
        assert str(excinfo.value) == ("concatenation_name must match "
                                      "dimensions in dims")


# Posterior predictive & log likelihood
class TestPPLL:
    def test_serial_ppll(self, example_model):
        inf = mu.single_fit_to_inference(
            fit=example_model.fit,
            coords={
                "feature": example_model.feature_names,
                "covariate": example_model.colnames
            },
            dims={
                "beta": ["covariate", "feature"],
                "phi": ["feature"]
            },
            params=["beta", "phi"],
            alr_params=["beta"],
            posterior_predictive="y_predict",
            log_likelihood="log_lik",
            sample_names=example_model.sample_names
        )

        d = {"posterior_predictive": "y_predict", "log_likelihood": "log_lik"}
        for k, v in d.items():
            inf_data = inf[k][v].values
            nb_data = example_model.fit.stan_variable(v)
            nb_data = np.array(np.split(nb_data, 4, axis=0))
            np.testing.assert_array_almost_equal(nb_data, inf_data)

    def test_parallel_ppll(self, example_parallel_model):
        inf = mu.multiple_fits_to_inference(
            fits=example_parallel_model.fit,
            coords={
                "feature": example_parallel_model.feature_names,
                "covariate": example_parallel_model.colnames
            },
            dims={
                "beta": ["covariate", "feature"],
                "phi": ["feature"]
            },
            params=["beta", "phi"],
            posterior_predictive="y_predict",
            log_likelihood="log_lik",
            concatenation_name="feature",
            sample_names=example_parallel_model.sample_names,
            feature_names=example_parallel_model.feature_names
        )

        dim_order = ("chain", "draw", "sample", "feature")

        nb_ll_data = np.stack([
            x.stan_variable("log_lik")
            for x in example_parallel_model.fit
        ], axis=2)
        nb_ll_data = np.array(np.split(nb_ll_data, 4, axis=0))

        nb_ll = xr.Dataset(
            {"log_lik": (dim_order, nb_ll_data)},
            coords={
                "chain": np.arange(4),
                "draw": np.arange(100),
                "sample": example_parallel_model.sample_names,
                "feature": example_parallel_model.feature_names
            }
        )

        nb_pp_data = np.stack([
            x.stan_variable("y_predict")
            for x in example_parallel_model.fit
        ], axis=2)
        nb_pp_data = np.array(np.split(nb_pp_data, 4, axis=0))

        nb_pp = xr.Dataset(
            {"y_predict": (dim_order, nb_pp_data)},
            coords={
                "chain": np.arange(4),
                "draw": np.arange(100),
                "sample": example_parallel_model.sample_names,
                "feature": example_parallel_model.feature_names
            }
        )

        inf_ll = inf.log_likelihood["log_lik"]
        inf_ll_data = inf_ll.transpose(*dim_order)
        np.testing.assert_array_almost_equal(inf_ll_data, nb_ll.log_lik.values)

        inf_pp = inf.posterior_predictive["y_predict"]
        inf_pp_data = inf_pp.transpose(*dim_order)
        np.testing.assert_array_almost_equal(inf_pp_data,
                                             nb_pp.y_predict.values)
