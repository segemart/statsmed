# Statsmed

Statsmed is designed to perform statistical analysis of medical data, but may also be used for various other datasets. It gives you a fast overview of your data and allows you to perform tests and create figures. 
There are examples for some functions.

- [Example 1](https://github.com/segemart/statsmed/blob/main/examples/example1/Tests_normal_distribution.ipynb) - Test for normal distribution
- [Example 2](https://github.com/segemart/statsmed/blob/main/examples/example2/DescriptiveStatistic.ipynb) - Descriptive Statistic - Mean; Confidence Interval - Median; Inter-quartile range
- [Example 3](https://github.com/segemart/statsmed/blob/main/examples/example3/Correlations.ipynb) - Pearson's and Spearman's correlation with figures
- [Example 4](https://github.com/segemart/statsmed/blob/main/examples/example4/Comparision_continuous.ipynb) - Comparison of two groups with continuous variables
- [Example 5](https://github.com/segemart/statsmed/blob/main/examples/example5/Bland-Altman-Plots.ipynb) - Bland-Altman plots
- [Example 6](https://github.com/segemart/statsmed/blob/main/examples/example6/Boxplots.ipynb) - Boxplots
- [Example 7](https://github.com/segemart/statsmed/blob/main/examples/example7/ROC-Curves.ipynb) - ROC curves and AUC
- [Example 8](https://github.com/segemart/statsmed/blob/main/examples/example8/Accuracy.ipynb) - Classification accuracy
- [Example 9](https://github.com/segemart/statsmed/blob/main/examples/example9/multivariate_linear_lasso.ipynb) - Multivariate linear regression and Lasso
- [Example 10](https://github.com/segemart/statsmed/blob/main/examples/example10/Poisson_NegBin_Rate_Change.ipynb) - Poisson / Negative Binomial Rate Change


For some special use cases we also implemented a functional t-test, where you can compare two groups of functions.

- [Special Example 1](https://github.com/segemart/statsmed/blob/main/examples/special_example1/Functional_t_test.ipynb) - Functional T-Test


### Installation

Statsmed works on Ubuntu, Mac, and Windows and on CPU and GPU.

Please make sure you have a running version of Python (>= 3.10), [uv](https://docs.astral.sh/uv/) (recommended) or pip, and git.

Install Statsmed with uv:
```
uv add git+https://github.com/segemart/statsmed.git
```

Or with pip:
```
pip install git+https://github.com/segemart/statsmed.git
```

### Goal

The idea was that you can perform quickly basic medical data analysis and create some figures. We will add more functions and create more examples. If you have ideas for improvement please contact us (martin.segeroth@usb.ch).

### Usage

Statsmed also allows you to generate figures quickly. See for example [Example 3](https://github.com/segemart/statsmed/blob/main/examples/example3/Correlations.ipynb), [Example 5](https://github.com/segemart/statsmed/blob/main/examples/example5/Bland-Altman-Plots.ipynb), [Example 6](https://github.com/segemart/statsmed/blob/main/examples/example6/Boxplots.ipynb), and [Example 7](https://github.com/segemart/statsmed/blob/main/examples/example7/ROC-Curves.ipynb), where we generated plots to show correlations, Bland-Altman plots, boxplots, and ROC curves.

![Correlations](examples/example3/Corr_subplots.png)

![Bland-Altman plots](examples/example5/Bland_Altman_subplots.png)

![Boxplots](examples/example6/Boxplots_subplots.png)

![ROC curves](examples/example7/ROCurve.png)

### Web Application

Statsmed includes a browser-based interface that lets you upload a CSV or Excel file, select statistical tests, and view results directly in the browser. Results can be downloaded as a PDF report.

To run the web application locally:

```
git clone https://github.com/segemart/statsmed.git
cd statsmed
uv sync --extra web
./run-web-app.sh
```

This starts the Flask development server at `http://localhost:5000`.

### Cite

If you use Statsmed in your research, please cite:

Segeroth, M., Indrakanti A. (2025). Statsmed: Statistics with Figures for medical data analysis (v1.0.1). GitHub. Available at [GitHub repository](https://github.com/segemart/statsmed).

```bibtex
@software{Segeroth_Statsmed_2025,
  author    = {Martin Segeroth, Ashraya Kumar Indrakanti},
  title     = {Statsmed: Statistics with Figures for medical data analysis},
  year      = {2025},
  url       = {https://github.com/segemart/statsmed},
  publisher = {GitHub}
}
```

### License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.