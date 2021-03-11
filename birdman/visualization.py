import arviz as az
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np


def plot_parameter_estimates(
    inference_object: az.InferenceData,
    parameter: str,
    coord: dict = dict(),
    num_std: float = 1.0
):
    """Plot credible intervals of estimated parameters.

    :param inference_object: Inference object containing posterior draws
    :type inference_object: az.InferenceData

    :param parameter: Name of parameter to plot
    :type parameter: str

    :param coord: Coordinates of parameter to plot
    :type coord: dict, optional

    :param num_std: Number of standard deviations to plot as error bars,
        defaults to 1.0
    :type num_std: float, optional

    :returns: matplotlib axes figure
    """
    posterior = inference_object.posterior
    if len(posterior[parameter].coords) > 3 and not coord:
        raise ValueError(
            "Must provide coordinates if plotting multi-dimensional parameter"
            " estimates!"
        )

    param_means = posterior[parameter].sel(**coord).mean(["chain", "draw"])
    param_stds = posterior[parameter].sel(**coord).std(["chain", "draw"])
    sort_indices = param_means.argsort().data
    param_means = param_means.data[sort_indices]
    param_stds = param_stds.data[sort_indices]

    fig, ax = plt.subplots(1, 1)
    x = np.arange(len(param_means))
    ax.errorbar(x=x, y=param_means, yerr=param_stds*num_std)
    ax.scatter(x=x, y=param_means)

    ax.set_xlabel("Feature")
    ax.set_ylabel("Differential")

    return ax


def plot_posterior_predictive_checks(inference_object: az.InferenceData):
    """Plot posterior predictive checks of fitted model.

    :param inference_object: Inference object containing posterior predictive
        and observed data groups
    :type inference_object: az.InferenceData

    :returns: matplotlib axes figure
    """
    if "posterior_predictive" not in inference_object.groups():
        raise ValueError(
            "Must include posterior predictive values to perform PPC!"
        )
    if "observed_data" not in inference_object.groups():
        raise ValueError("Must include observed data to perform PPC!")

    obs = inference_object.observed_data.to_array().values.ravel()
    ppc = inference_object.posterior_predictive
    ppc_mean = ppc.mean(["chain", "draw"]).to_array().values[0]
    ppc_lower = ppc.quantile(0.025, ["chain", "draw"]).to_array().values[0]
    ppc_upper = ppc.quantile(0.975, ["chain", "draw"]).to_array().values[0]
    ppc_in_ci = (obs < ppc_upper) & (obs > ppc_lower)
    pct_in_ci = ppc_in_ci.sum() / len(ppc_in_ci) * 100

    sort_indices = obs.argsort()
    obs = obs[sort_indices]
    ppc_mean = ppc_mean[sort_indices]
    ppc_lower = ppc_lower[sort_indices]
    ppc_upper = ppc_upper[sort_indices]

    fig, ax = plt.subplots(1, 1)
    x = np.arange(len(obs))
    ax.plot(x, obs, zorder=3, color="black")
    y_min, y_max = ax.get_ylim()
    ax.scatter(x=x, y=ppc_mean, zorder=1, color="gray")
    for i, (lower, upper) in enumerate(zip(ppc_lower, ppc_upper)):
        ax.plot(  # credible interval
            [i, i],
            [lower, upper],
            zorder=0,
            color="lightgray",
        )
    ax.set_ylim([y_min, y_max])

    obs_legend_entry = Line2D([0], [0], color="black", linewidth=2)
    ci_legend_entry = Line2D([0], [0], color="lightgray", linewidth=2)
    ppc_mean_legend_entry = Line2D([0], [0], color="gray", marker="o",
                                   linewidth=0)
    ax.legend(
        handles=[obs_legend_entry, ci_legend_entry, ppc_mean_legend_entry],
        labels=["Observed", "95% Credible Interval", "Mean"],
        bbox_to_anchor=[0.5, -0.2],
        loc="center",
        ncol=3
    )

    ax.set_title(
        f"{round(pct_in_ci, 2)}% of Predictions in 95% Credible Interval"
    )
    ax.set_ylabel("Count")
    ax.set_xlabel("Table Entry")
    plt.tight_layout()

    return ax