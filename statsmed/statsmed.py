import numpy as np
import scipy
import math
import sys
from collections import Counter
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import casadi as ca
import itertools
import random

from scipy.stats import chi2_contingency
from statsmodels.stats.contingency_tables import mcnemar

# Shapiro-Wilk-Test returning Test-statistic and p-value
def shapiro_wilk_test(x):
    [t,z] = scipy.stats.shapiro(x)
    return ([t,z])

# Kolmogorow-Smirnow-Test returning Test-statistic and p-value
def kolmogorow_smirnow_test(x):
    [t,z] = scipy.stats.kstest((x - np.mean(x))/np.std(x,ddof = 1),scipy.stats.norm.cdf)
    return ([t,z])

'''test of normality using the: 1. Shapiro-Wilk-Test and 2. Kolmogorow-Smirnow-Test
Kolmogorow-Smirnow-Test requires normalization but not Shapiro-Wilk-Test
Input: array of test-data - please exclude NaN or None Values.
Output: 0 if both tests do not indicate a significant difference from a normal distribution and 1 if at least ones does,
        0 if Shapiro-Wilk-Test does not indicate a significant difference from a normal distribution and 1 if does,
        0 if Kolmogorow-Smirnow-Test does not indicate a significant difference from a normal distribution and 1 if does,
        Test-statistic of Shapiro-Wilk-Test,
        p-value of Shapiro-Wilk-Test,
        test-statistic of Kolmogorow-Smirnow-Test,
        p-value of Kolmogorow-Smirnow-Test
'''
def stdnorm_test(x,Np_of_decimals = 3, quiet = False):
    SWn = 0
    [t1,z1] = shapiro_wilk_test(x)
    if z1 < 0.05:
        SWn = 1
        if not quiet: print("Shapiro-Wilk: No normal dsitribution (p-value = " + report_p_value(z1,Np_of_decimals) + ")")
    else:
        SWn = 0
        if not quiet: print("Shapiro-Wilk: Normal dsitribution (p-value = " + report_p_value(z1,Np_of_decimals) + " \n \t - p-value >= 0.05 indicates no significant difference from normal distribution)")
    KSn = 0
    [t2,z2] = kolmogorow_smirnow_test(x)
    if z2 < 0.05:
        KSn = 1
        if not quiet: print("Kolmogorow-Smirnow: No normal dsitribution (p-value = " + report_p_value(z2,Np_of_decimals) + ")")
    else:
        KSn = 0
        if not quiet: print("Kolmogorow-Smirnow: Normal dsitribution (p-value = " + report_p_value(z2,Np_of_decimals) + " \n \t - p-value >= 0.05 indicates no significant difference from normal distribution)")
    Fn = 0
    if (z1 < 0.05) or (z2 < 0.05):
        Fn = 1
        if not quiet: print("At least one test indicates no normal distribution")
    else:
        Fn = 0
        if not quiet: print("Both tests do not indicate a significant difference from a normal distribution")
    return [Fn,SWn,KSn,t1,z1,t2,z2]

''' Descriptive statistic of data depending on their dirstribution:
Input: array of test-data - please exclude NaN or None Values; Number of decimals; mode (what to return)
Output: depends on mode if mode = all the function prints mean with standard deviation and confidence interval
                                  as well as median with inter-quartile range and pseudomedian with confidence interval of the signed-rank distribution
                        if mode = normal distribution - only the mean with standard deviation and confidence interval is given
                        if mode = no normal distribution - median with inter-quartile range and pseudomedian with confidence interval of the signed-rank distribution is returned
                        if something else is given the respective output depends on whether the data is normal distributed due to stdnorm_test
        the output is rounded to the number of given decimals
        it also returns a numpy array containing all values depending on mode
'''
def get_desc(x,N_of_decimals = 2,mode = 'choose', quiet = False):
    distr = stdnorm_test(x,quiet = True)
    mean_std = np.array([np.mean(x),np.std(x), np.nan])
    normald = get_CI_normd(x)
    IQRd = np.append(np.array([np.percentile(x,50)]),np.percentile(x, (25,75)))
    SignRd = get_CI_signrankdist_CC(x)
    if mode == 'all':
        if not quiet: print(f'The mean with standard deviation is: {mean_std[0]:.{N_of_decimals}f} \u00B1 {mean_std[1]:.{N_of_decimals}f}')
        if not quiet: print(f'The mean with 95%-confidence interval is: {normald[0]:.{N_of_decimals}f} (CI: {normald[1]:.{N_of_decimals}f} - {normald[2]:.{N_of_decimals}f})')
        if not quiet: print(f'The median with interquartile range (IQR) from the 25th to 75th percentile is: {IQRd[0]:.{N_of_decimals}f} (IQR: {IQRd[1]:.{N_of_decimals}f} - {IQRd[2]:.{N_of_decimals}f})')
        if not quiet: print(f'The pseudomedian with 95%-confidence interval from the signed-rank distribution is: {SignRd[0]:.{N_of_decimals}f} (CI: {SignRd[1]:.{N_of_decimals}f} - {SignRd[2]:.{N_of_decimals}f})')
        res = np.stack((mean_std,normald, IQRd, SignRd), axis=0)
        res = np.round(res,N_of_decimals)
        return res
    elif mode == 'normal distribution':
        if not quiet: print(f'The mean with standard deviation is: {mean_std[0]:.{N_of_decimals}f} \u00B1 {mean_std[1]:.{N_of_decimals}f}')
        if not quiet: print(f'The mean with 95%-confidence interval is: {normald[0]:.{N_of_decimals}f} (CI: {normald[1]:.{N_of_decimals}f} - {normald[2]:.{N_of_decimals}f})')
        res = np.stack((mean_std,normald), axis=0)
        res = np.round(res,N_of_decimals)
        return res
    elif mode == 'no normal distribution':
        if not quiet: print(f'The median with interquartile range (IQR) from the 25th to 75th percentile is: {IQRd[0]:.{N_of_decimals}f} (IQR: {IQRd[1]:.{N_of_decimals}f} - {IQRd[2]:.{N_of_decimals}f})')
        if not quiet: print(f'The pseudomedian with 95%-confidence interval from the signed-rank distribution is: {SignRd[0]:.{N_of_decimals}f} (CI: {SignRd[1]:.{N_of_decimals}f} - {SignRd[2]:.{N_of_decimals}f})')
        res = np.stack((IQRd, SignRd), axis=0)
        res = np.round(res,N_of_decimals)
        return res
    else:
        if distr[0] == 0:
            if not quiet: print(f'The mean with standard deviation is: {mean_std[0]:.{N_of_decimals}f} \u00B1 {mean_std[1]:.{N_of_decimals}f}')
            if not quiet: print(f'The mean with 95%-confidence interval is: {normald[0]:.{N_of_decimals}f} (CI: {normald[1]:.{N_of_decimals}f} - {normald[2]:.{N_of_decimals}f})')
            res = np.stack((mean_std,normald), axis=0)
            res = np.round(res,N_of_decimals)
            return res
        else:
            if not quiet: print(f'The median with interquartile range (IQR) from the 25th to 75th percentile is: {IQRd[0]:.{N_of_decimals}f} (IQR: {IQRd[1]:.{N_of_decimals}f} - {IQRd[2]:.{N_of_decimals}f})')
            if not quiet: print(f'The pseudomedian with 95%-confidence interval from the signed-rank distribution is: {SignRd[0]:.{N_of_decimals}f} (CI: {SignRd[1]:.{N_of_decimals}f} - {SignRd[2]:.{N_of_decimals}f})')
            res = np.stack((IQRd, SignRd), axis=0)
            res = np.round(res,N_of_decimals)
            return res

def report_p_value(p,Np_of_decimals = 3):
    if p >= 0.06:
        return "p = " + str(np.round(p,2))
    elif (p < 0.06) and (p > 0.05):
        return "p = " + str(np.round(p,3))
    elif (p <= 0.05) and p >= np.power(1/10,Np_of_decimals):
        return "p = " + str(np.round(p,Np_of_decimals))
    else:
        return f"p < {np.round(np.power(1/10,Np_of_decimals),Np_of_decimals)}"


''' Correlation of two groups:
Input: two arrays of test-data (x and y) - please exclude NaN or None Values; Number of decimals; mode (what to return); Number of decimals for significant p values
Output: depends on mode if mode = all the function prints Spearman correlation and Pearson correlation
                        if mode = normal distribution - only the Pearson correlation is given
                        if mode = no normal distribution - Spearman correlation is returned
                        if something else is given the respective output depends on whether the data is normal distributed (Pearson correlation) or not normal distributed (Spearman correlation) due to stdnorm_test
        the output for each line of the output: 0 (Pearson) or 1 (Spearman); r-value rounded to number of given decimals; p-value rounded to number of decimals for significant p values;
                        95%-confidence interval of r-value rounded to number of given decimals
        the given lines depend on the mode
'''
def corr_two_gr(x,y,N_of_decimals = 2,mode = 'choose',Np_of_decimals = 3, quiet = False):
    if not quiet: print('Testing normal distribution of first variable:')
    x_distr = stdnorm_test(x,quiet)
    if not quiet: print('Testing normal distribution of second variable:')
    y_distr = stdnorm_test(y,quiet)
    [r,p] = scipy.stats.spearmanr(x, y)
    s2 = (1 + np.power(r,2)/2)/(len(x)-3)
    confrs = [np.tanh(np.arctanh(r) - np.sqrt(s2) * scipy.stats.norm.ppf(0.975)) , np.tanh(np.arctanh(r) + np.sqrt(s2) * scipy.stats.norm.ppf(0.975))]
    a = np.array([1,r,p,confrs[0],confrs[1]])
    a = np.expand_dims(a, axis=0)
    [r,p] = scipy.stats.pearsonr(x, y)
    zr = np.arctanh(r)
    se = 1/np.sqrt(len(x)-3)
    z = scipy.stats.norm.ppf(1-0.05/2)
    lo_z, hi_z = zr-z*se, zr+z*se
    confrr = np.tanh((lo_z, hi_z))
    a = np.append(a,np.expand_dims(np.array([0,r,p,confrr[0],confrr[1]]), axis=0),axis = 0)
    if mode == 'all':
        if not quiet: print(f'The Spearman correlation yields a r-value of: r = {a[0,1]:.{N_of_decimals}f} (' + report_p_value(a[0,2],Np_of_decimals) + ')')
        if not quiet: print(f'The Spearman correlation with 95%-confidence interval is: r = {a[0,1]:.{N_of_decimals}f} (CI: {a[0,3]:.{N_of_decimals}f} - {a[0,4]:.{N_of_decimals}f}; ' + report_p_value(a[0,2],Np_of_decimals) + ')')
        if not quiet: print(f'The Pearson correlation yields a r-value of: r = {a[1,1]:.{N_of_decimals}f} (' + report_p_value(a[1,2],Np_of_decimals) + ')')
        if not quiet: print(f'The Pearson correlation with 95%-confidence interval is: r = {a[1,1]:.{N_of_decimals}f} (CI: {a[1,3]:.{N_of_decimals}f} - {a[1,4]:.{N_of_decimals}f}; ' + report_p_value(a[1,2],Np_of_decimals) + ')')
        return np.stack([a[:,0],np.round(a[:,1],N_of_decimals),np.round(a[:,2],Np_of_decimals),np.round(a[:,3],N_of_decimals),np.round(a[:,4],N_of_decimals)],axis = 1)
    elif mode == 'normal distribution':
        if not quiet: print(f'The Pearson correlation yields a r-value of: r = {a[1,1]:.{N_of_decimals}f} (' + report_p_value(a[1,2],Np_of_decimals) + ')')
        if not quiet: print(f'The Pearson correlation with 95%-confidence interval is: r = {a[1,1]:.{N_of_decimals}f} (CI: {a[1,3]:.{N_of_decimals}f} - {a[1,4]:.{N_of_decimals}f}; ' + report_p_value(a[1,2],Np_of_decimals) + ')')
        return np.stack([a[1,0],np.round(a[1,1],N_of_decimals),np.round(a[1,2],Np_of_decimals),np.round(a[1,3],N_of_decimals),np.round(a[1,4],N_of_decimals)],axis = 0)
    elif mode == 'no normal distribution':
        if not quiet: print(f'The Spearman correlation yields a r-value of: r = {a[0,1]:.{N_of_decimals}f} (' + report_p_value(a[0,2],Np_of_decimals) + ')')
        if not quiet: print(f'The Spearman correlation with 95%-confidence interval is: r = {a[0,1]:.{N_of_decimals}f} (CI: {a[0,3]:.{N_of_decimals}f} - {a[0,4]:.{N_of_decimals}f}; ' + report_p_value(a[0,2],Np_of_decimals) + ')')
        return np.stack([a[0,0],np.round(a[0,1],N_of_decimals),np.round(a[0,2],Np_of_decimals),np.round(a[0,3],N_of_decimals),np.round(a[0,4],N_of_decimals)],axis = 0)
    else:
        if (x_distr[0] == 0) and (y_distr[0] == 0):
            if not quiet: print('The distribution of both variables show no significant difference from a normal distribution. Thus Pearson correlation is performed.')
            if not quiet: print(f'The Pearson correlation yields a r-value of: r = {a[1,1]:.{N_of_decimals}f} (' + report_p_value(a[1,2],Np_of_decimals) + ')')
            if not quiet: print(f'The Pearson correlation with 95%-confidence interval is: r = {a[1,1]:.{N_of_decimals}f} (CI: {a[1,3]:.{N_of_decimals}f} - {a[1,4]:.{N_of_decimals}f}; ' + report_p_value(a[1,2],Np_of_decimals) + ')')
            return np.stack([a[1,0],np.round(a[1,1],N_of_decimals),np.round(a[1,2],Np_of_decimals),np.round(a[1,3],N_of_decimals),np.round(a[1,4],N_of_decimals)],axis = 0)
        else:
            if not quiet: print('The distribution of at least one of both variables shows a significant difference from a normal distribution. Thus Spearman correlation is performed.')
            if not quiet: print(f'The Spearman correlation yields a r-value of: r = {a[0,1]:.{N_of_decimals}f} (' + report_p_value(a[0,2],Np_of_decimals) + ')')
            if not quiet: print(f'The Spearman correlation with 95%-confidence interval is: r = {a[0,1]:.{N_of_decimals}f} (CI: {a[0,3]:.{N_of_decimals}f} - {a[0,4]:.{N_of_decimals}f}; ' + report_p_value(a[0,2],Np_of_decimals) + ')')
            return np.stack([a[0,0],np.round(a[0,1],N_of_decimals),np.round(a[0,2],Np_of_decimals),np.round(a[0,3],N_of_decimals),np.round(a[0,4],N_of_decimals)],axis = 0)

def func_fit(x,a,b):
    return a*x+b

''' Makes a scatter plot of the x and y data with a linear regression for visualization and gives the correlations (Spearman and Pearson):
Input: two arrays of test-data (x and y) - please exclude NaN or None Values; Figure; Title; Label of x-axis; Label of y-axis; color; Number of decimals; mode (what to return); Number of decimals for significant p values
'''
def corr_scatter_figure(x,y,fig_x,title='',x_label='',y_label='', color = 'green',N_of_decimals = 2,mode = 'choose',Np_of_decimals = 3,quiet = False):
    plt.scatter(x,y, color = color,s=10, alpha=0.2)
    popt, pcov = scipy.optimize.curve_fit(func_fit, x, y)
    plt.plot(x,func_fit(x,*popt), color = color,linewidth=3)
    sigma = np.sqrt(np.diagonal(pcov))
    bound_upper = func_fit(np.linspace(np.min(x), np.max(x), 1000), *(popt + sigma))
    bound_lower = func_fit(np.linspace(np.min(x), np.max(x), 1000), *(popt - sigma))
    plt.fill_between(np.linspace(np.min(x), np.max(x), 1000), bound_lower, bound_upper,color = 'green', alpha = 0.15)
    [normaly_low, normaly_high] = fig_x.get_ybound()
    ysize = normaly_high - normaly_low
    xsize = fig_x.get_xbound()[1] - fig_x.get_xbound()[0]
    if (mode != 'all') and (mode != 'normal distribution') and (mode != 'no normal distribution'):
        x_distr = stdnorm_test(x,quiet)
        y_distr = stdnorm_test(y,quiet)
        if (x_distr[0] == 0) and (y_distr[0] == 0):
            mode = 'normal distribution'
        else:
            mode = 'no normal distribution'
    if mode == 'all':
        fig_x.set_ylim([normaly_low , normaly_high + 0.2 * ysize])
        [r,p] = scipy.stats.pearsonr(x, y)
        plt.text(fig_x.get_xbound()[0] + 0.1*xsize, normaly_high + 0.0*ysize, f'$r_r$ = {r:.{N_of_decimals}f} (' + report_p_value(p,Np_of_decimals) + ')',fontsize=18)
        [r,p] = scipy.stats.spearmanr(x, y)
        plt.text(fig_x.get_xbound()[0] + 0.1*xsize, normaly_high + 0.1*ysize, f'$r_s$ = {r:.{N_of_decimals}f} (' + report_p_value(p,Np_of_decimals) + ')',fontsize=18)
    elif mode == 'normal distribution':
        fig_x.set_ylim([normaly_low , normaly_high + 0.1 * ysize])
        [r,p] = scipy.stats.pearsonr(x, y)
        plt.text(fig_x.get_xbound()[0] + 0.1*xsize, normaly_high + 0.0*ysize, f'$r_r$ = {r:.{N_of_decimals}f} (' + report_p_value(p,Np_of_decimals) + ')',fontsize=18)
    elif mode == 'no normal distribution':
        fig_x.set_ylim([normaly_low , normaly_high + 0.1 * ysize])
        [r,p] = scipy.stats.spearmanr(x, y)
        plt.text(fig_x.get_xbound()[0] + 0.1*xsize, normaly_high + 0.0*ysize, f'$r_s$ = {r:.{N_of_decimals}f} (' + report_p_value(p,Np_of_decimals) + ')',fontsize=18)
    fig_x.set_title(title,fontsize=22)
    fig_x.set_xlabel(x_label,fontsize=20)
    fig_x.set_ylabel(y_label,fontsize=20)
    fig_x.tick_params(labelsize=18)

def ttest_ind(x,y,alternative='two-sided'):
    [t,p] = scipy.stats.ttest_ind(x,y,alternative=alternative)
    return [t,p]

def ttest_dep(x,y,alternative='two-sided'):
    [t,p] = scipy.stats.ttest_rel(x,y,alternative=alternative)
    return [t,p]

def mann_whitney_ind(x,y,alternative='two-sided'):
    [t,p] = scipy.stats.mannwhitneyu(x, y,alternative=alternative)
    return [t,p]

def wilcoxon_dep(x,y,alternative='two-sided'):
    [t,p] = scipy.stats.wilcoxon(x, y,alternative=alternative)
    return [t,p]

''' Comparison of two groups with continuous variables:
Input: two arrays of test-data (x and y) - please exclude NaN or None Values; independet = True or False is x and y are independent (True) or dependent/related (False); alternative: {two-sided, less, greater}; Number of decimals; mode (what to return); Number of decimals for significant p values
Output: depends on mode if mode = all; the function prints results of T-test for the means of two independent and dependent/related samples, Mann-Whitney U-Test of two independent samples and Wilcoxon signed-rank test of two dependent/related samples
                        if mode = normal distribution - dependent on independent value the function prints results of T-test for the means of two independent or dependent/related samples
                        if mode = no normal distribution - dependent on independent value the function prints results of Mann-Whitney U-Test of two independent samples or Wilcoxon signed-rank test of two dependent/related samples
                        if something else is given the respective output depends on whether the data is normal distributed or not normal distributed due to stdnorm_test
        the output for each line of the output: t-value rounded to number of given decimals; p-value rounded to number of decimals for significant p values;
        the given lines depend on the mode
'''
def comp_two_gr_continuous(x,y,independent,alternative='two-sided', N_of_decimals = 2,mode = 'choose',Np_of_decimals = 3, quiet = False):
    if not quiet: print('Testing normal distribution of x-data:')
    x_distr = stdnorm_test(x,Np_of_decimals,quiet = quiet)
    if not quiet:
        print('Descriptive Statistic of the x-data with all returns:')
    x_res = get_desc(x,N_of_decimals,mode = 'all',quiet = quiet)
    if not quiet: print('\n')
    if not quiet: print('Testing normal distribution of y-data:')
    y_distr = stdnorm_test(y,Np_of_decimals,quiet = quiet)
    if not quiet:
        print('Descriptive Statistic of the y-data with all returns:')
    y_res = get_desc(y,N_of_decimals,mode = 'all',quiet = quiet)
    if not quiet: print('\n')
    if independent == True:
        [t_ttest_ind,p_ttest_ind] = ttest_ind(x,y,alternative=alternative)
        [t_mann_whitney_ind,p_mann_whitney_ind] = mann_whitney_ind(x,y,alternative=alternative)
    else:
        [t_ttest_dep,p_ttest_dep] = ttest_dep(x,y,alternative=alternative)
        [t_wilcoxon_dep,p_wilcoxon_dep] = wilcoxon_dep(x,y,alternative=alternative)
    if mode == 'all':
        if independent == True:
            if not quiet: print('T-test for the means of two independent samples yields a p-value of: ' + report_p_value(p_ttest_ind,Np_of_decimals) + f' (t-value: {t_ttest_ind:.{N_of_decimals}f})')
            if not quiet: print('Mann-Whitney U-Test of two independent samples yields a p-value of: ' + report_p_value(p_mann_whitney_ind,Np_of_decimals) + f' (t-value: {t_mann_whitney_ind:.{N_of_decimals}f})')
            res = np.array([[np.round(t_ttest_ind,N_of_decimals),np.round(p_ttest_ind,Np_of_decimals)],[np.round(t_mann_whitney_ind,N_of_decimals),np.round(p_mann_whitney_ind,Np_of_decimals)]])
            return res
        else:
            if not quiet: print('T-test for the means of two dependent/related samples yields a p-value of: ' + report_p_value(p_ttest_dep,Np_of_decimals) + f' (t-value: {t_ttest_dep:.{N_of_decimals}f})')
            if not quiet: print('Wilcoxon signed-rank test of two dependent/related samples yields a p-value: ' + report_p_value(p_wilcoxon_dep,Np_of_decimals) + f' (t-value: {t_wilcoxon_dep:.{N_of_decimals}f})')
            res = np.array([[np.round(t_ttest_dep,N_of_decimals),np.round(p_ttest_dep,Np_of_decimals)],[np.round(t_wilcoxon_dep,N_of_decimals),np.round(p_wilcoxon_dep,Np_of_decimals)]])
            return res
    elif mode == 'normal distribution':
        if independent == True:
            if not quiet: print('T-test for the means of two independent samples yields a p-value of: ' + report_p_value(p_ttest_ind,Np_of_decimals) + f' (t-value: {t_ttest_ind:.{N_of_decimals}f})')
            res = np.array([np.round(t_ttest_ind,N_of_decimals),np.round(p_ttest_ind,Np_of_decimals)])
            return res
        else:
            if not quiet: print('T-test for the means of two dependent/related samples yields a p-value of: ' + report_p_value(p_ttest_dep,Np_of_decimals) + f' (t-value: {t_ttest_dep:.{N_of_decimals}f})')
            res = np.array([np.round(t_ttest_dep,N_of_decimals),np.round(p_ttest_dep,Np_of_decimals)])
            return res
    elif mode == 'no normal distribution':
        if independent == True:
            if not quiet: print('Mann-Whitney U-Test of two independent samples yields a p-value of: ' + report_p_value(p_mann_whitney_ind,Np_of_decimals) + f' (t-value: {t_mann_whitney_ind:.{N_of_decimals}f})')
            res = np.array([np.round(t_mann_whitney_ind,N_of_decimals),np.round(p_mann_whitney_ind,Np_of_decimals)])
            return res
        else:
            if not quiet: print('Wilcoxon signed-rank test of two dependent/related samples yields a p-value: ' + report_p_value(p_wilcoxon_dep,Np_of_decimals) + f' (t-value: {t_wilcoxon_dep:.{N_of_decimals}f})')
            res = np.array([np.round(t_wilcoxon_dep,N_of_decimals),np.round(p_wilcoxon_dep,Np_of_decimals)])
            return res
    else:
        if (x_distr[0] == 0) and (y_distr[0] == 0):
            if independent == True:
                if not quiet: print('T-test for the means of two independent samples yields a p-value of: ' + report_p_value(p_ttest_ind,Np_of_decimals) + f' (t-value: {t_ttest_ind:.{N_of_decimals}f})')
                res = np.array([np.round(t_ttest_ind,N_of_decimals),np.round(p_ttest_ind,Np_of_decimals)])
                return res
            else:
                if not quiet: print('T-test for the means of two dependent/related samples yields a p-value of: ' + report_p_value(p_ttest_dep,Np_of_decimals) + f' (t-value: {t_ttest_dep:.{N_of_decimals}f})')
                res = np.array([np.round(t_ttest_dep,N_of_decimals),np.round(p_ttest_dep,Np_of_decimals)])
                return res
        else:
            if independent == True:
                if not quiet: print('Mann-Whitney U-Test of two independent samples yields a p-value of: ' + report_p_value(p_mann_whitney_ind,Np_of_decimals) + f' (t-value: {t_mann_whitney_ind:.{N_of_decimals}f})')
                res = np.array([np.round(t_mann_whitney_ind,N_of_decimals),np.round(p_mann_whitney_ind,Np_of_decimals)])
                return res
            else:
                if not quiet: print('Wilcoxon signed-rank test of two dependent/related samples yields a p-value: ' + report_p_value(p_wilcoxon_dep,Np_of_decimals) + f' (t-value: {t_wilcoxon_dep:.{N_of_decimals}f})')
                res = np.array([np.round(t_wilcoxon_dep,N_of_decimals),np.round(p_wilcoxon_dep,Np_of_decimals)])
                return res


''' Makes a Bland-Altman plot of the x and y data:
Input: two arrays of test-data (x and y) - please exclude NaN or None Values; Figure; Title; Label of x-axis; Label of y-axis
'''
def bland_altman_plot(x, y, fig_x,title='',x_label='Mean of raters',y_label='Difference in seconds between raters'):
    data1     = np.asarray(x)
    data2     = np.asarray(y)
    mean      = np.mean([x, y], axis=0)
    # diff      = (x - y)/y * 100               # Difference between data1 and data2
    diff      = (x - y)                         # Difference between data1 and data2
    md        = np.mean(diff)                   # Mean of the difference
    sd        = np.std(diff,ddof = 1, axis=0)   # Standard deviation of the difference
    median    = np.percentile(diff,50)
    quartile  = np.percentile(diff,[10, 90])
    plt.scatter(mean, diff,color="green")
    plt.axhline(md,           color='blue', linestyle='--')
    plt.axhline(md + 1.96*sd, color='red', linestyle='--')
    plt.axhline(md - 1.96*sd, color='red', linestyle='--')
    # plt.axhline(quartile[0] , color='black', linestyle=':')
    # plt.axhline(quartile[1] , color='black', linestyle=':')
    n = diff.shape[0]
    sd = np.std(diff,ddof = 1)
    # Variance
    var = sd**2
    # Standard error of the bias
    se_bias = np.sqrt(var / n)
    # Standard error of the limits of agreement
    se_loas = np.sqrt(3 * var / n)
    # Endpoints of the range that contains 95% of the Student’s t distribution
    t_interval = scipy.stats.t.interval(alpha=0.95, df=n - 1)
    # Confidence intervals
    ci_bias = md + np.array(t_interval) * se_bias
    ci_upperloa = md + 1.96*sd + np.array(t_interval) * se_loas
    ci_lowerloa = md - 1.96*sd + np.array(t_interval) * se_loas
    left, right = plt.xlim()    
    plt.fill_between([left-100, right+100], [ci_upperloa[0], ci_upperloa[0]], [ci_upperloa[1], ci_upperloa[1]],color = 'lightcoral', alpha = 0.15)
    plt.fill_between([left-100, right+100], [ci_bias[0], ci_bias[0]], [ci_bias[1], ci_bias[1]],color = 'cornflowerblue', alpha = 0.15)
    plt.fill_between([left-100, right+100], [ci_lowerloa[0], ci_lowerloa[0]], [ci_lowerloa[1], ci_lowerloa[1]],color = 'lightcoral', alpha = 0.15)
    plt.xlim(left,right)
    # plt.plot([left] * 2, list(ci_upperloa), c='grey', ls='--', alpha=0.5)
    # plt.plot([left] * 2, list(ci_bias), c='grey', ls='--', alpha=0.5)
    # plt.plot([left] * 2, list(ci_lowerloa), c='grey', ls='--', alpha=0.5)
    fig_x.set_title(title,fontsize=22)
    fig_x.set_xlabel(x_label,fontsize=20)
    fig_x.set_ylabel(y_label,fontsize=20)
    fig_x.tick_params(labelsize=18)

def halloa():
    print('halloeawd')

#x,y,independent,alternative='two-sided', N_of_decimals = 2,mode = 'choose',Np_of_decimals = 3, quiet = False
'''
Return:
0: Size of total population
1: Number of positives
2: Number of negatives
3: Number of predicted positives
4: Number of predicted negatives
5: Number of true positives
6: Number of true negatives
7: Number of false positives
8: Number of false negatives
9: Prevalence
10: Accuaracy
11: Positive Predictive Value / Precision (PPV)
12: Negative Predictive Value (NPV)
13: False Omission Rate (FOR)
14: False Discovery Rate (FDR)
15: True Positive Rate / Sensitivity / Recall (TPR)
16: True Negative Rate / Spezificity (TNR)
17: False Positive Rate (FPR)
18: False Negative Rate (FNR)
19: Informedness / Youden's J statistic
20: Prevalence threshold
21: Balanced accuracy
22: F1 score
23: Positive likelihood ratio
24: Negative likelihood ratio
25: Diagnostics Odds Ratio (DOR)
26: Jaccard Index
'''
def acc_sens(gt,x,N_of_decimals = 2,quiet = False):
    if np.sum(((gt != 1).astype(int) + (gt != 0).astype(int)) != 1) > 0:
        print('Ground truth is not indicated by ones and zeros')
    if np.sum(((x != 1).astype(int) + (x != 0).astype(int)) != 1) > 0:
        print('Evaluation parameter is not indicated by ones and zeros')
    if len(gt) != len(x):
        print('Length of ground truth and evaluation parameter are not equal')
    total_population = len(gt)
    if not quiet: print(f'Size of total population: {total_population:.{0}f}')
    p = np.sum(gt == 1)
    if not quiet: print(f'Number of positives: {p:.{0}f}')
    n = np.sum(gt == 0)
    if not quiet: print(f'Number of negatives: {n:.{0}f}')
    pp = np.sum(x == 1)
    if not quiet: print(f'Number of predicted positives: {pp:.{0}f}')
    pn = np.sum(x == 0)
    if not quiet: print(f'Number of predicted negatives: {pn:.{0}f}')
    tp = np.sum((gt == 1) & (x == 1))
    if not quiet: print(f'Number of true positives: {tp:.{0}f}')
    tn = np.sum((gt == 0) & (x == 0))
    if not quiet: print(f'Number of true negatives: {tn:.{0}f}')
    fp = np.sum((gt == 0) & (x == 1))
    if not quiet: print(f'Number of false positives: {fp:.{0}f}')
    fn = np.sum((gt == 1) & (x == 0))
    if not quiet: print(f'Number of false negatives: {fn:.{0}f}')
    prevalence = np.nan
    if total_population != 0:
        prevalence = p/total_population
    else:
        print('Prevalence cannot be calculated as the size of total population is zero')
    if not quiet: print(f'Prevalence: {prevalence:.{N_of_decimals}f}')
    accuracy = np.nan
    if total_population != 0:
        accuracy = (tp + tn)/total_population
    else:
        print('Accuaracy cannot be calculated as the size of total population is zero')
    if not quiet: print(f'Accuaracy: {accuracy:.{N_of_decimals}f}')
    ppv = np.nan
    if pp != 0:
        ppv = tp/pp
    else:
        print('Positive Predictive Value / Precision (PPV) cannot be calculated as the number of predicted positives is zero')
    if not quiet: print(f'Positive Predictive Value / Precision (PPV): {ppv:.{N_of_decimals}f}')
    npv = np.nan
    if pn != 0:
        npv = tn/pn
    else:
        print('Negative Predictive Value (NPV) cannot be calculated as the number of predicted negatives is zero')
    if not quiet: print(f'Negative Predictive Value (NPV): {npv:.{N_of_decimals}f}')
    false_omission_rate = np.nan
    if pn != 0:
        false_omission_rate = fn/pn
    else:
        print('False Omission Rate (FOR) cannot be calculated as the number of predicted negatives is zero')
    false_discovery_rate = np.nan
    if pp != 0:
        false_discovery_rate = fp/pp
    else:
        print('False Discovery Rate (FDR) cannot be calculated as the number of predicted positives is zero')
    if np.round(false_omission_rate,N_of_decimals) != np.round((1-npv),N_of_decimals):
        print('Problem with False Omission Rate (FOR)')
    if np.round(false_discovery_rate,N_of_decimals) != np.round((1-ppv),N_of_decimals):
        print('Problem with False Discovery Rate (FDR)')
    if not quiet: print(f'False Omission Rate (FOR): {false_omission_rate:.{N_of_decimals}f}')
    if not quiet: print(f'False Discovery Rate (FDR): {false_discovery_rate:.{N_of_decimals}f}')
    tpr = np.nan
    if p != 0:
        tpr = tp/p
    else:
        print('True Positive Rate / Sensitivity / Recall (TPR) cannot be calculated as the number of positives is zero')
    tnr = np.nan
    if n != 0:
        tnr = tn/n
    else:
        print('True Negative Rate / Spezificity (TNR) cannot be calculated as the number of negatives is zero')
    fpr = np.nan
    if n != 0:
        fpr = fp/n
    else:
        print('False Positive Rate (FPR) cannot be calculated as the number of negatives is zero')
    fnr = np.nan
    if p != 0:
        fnr = fn/p
    else:
        print('False Negative Rate (FNR) cannot be calculated as the number of positives is zero')
    if np.round(tpr,N_of_decimals) != np.round((1-fnr),N_of_decimals):
        print('Problem with True Positive Rate')
    if np.round(tnr,N_of_decimals) != np.round((1-fpr),N_of_decimals):
        print('Problem with True Negative Rate')
    if np.round(fpr,N_of_decimals) != np.round((1-tnr),N_of_decimals):
        print('Problem with False Positive Rate')
    if np.round(fnr,N_of_decimals) != np.round((1-tpr),N_of_decimals):
        print('Problem with False Negative Rate')
    if not quiet: print(f'True Positive Rate / Sensitivity / Recall (TPR): {tpr:.{N_of_decimals}f}')
    if not quiet: print(f'True Negative Rate / Spezificity (TNR): {tnr:.{N_of_decimals}f}')
    if not quiet: print(f'False Positive Rate (FPR): {fpr:.{N_of_decimals}f}')
    if not quiet: print(f'False Negative Rate (FNR): {fnr:.{N_of_decimals}f}')
    informedness_youdenJ = np.nan
    if (np.isnan(tpr) or np.isnan(tnr)) == False:
        informedness_youdenJ = tpr + tnr -1
    else:
        print('Informedness / Youden\'s J statistic cannot be calculated as the True Positive Rate / Sensitivity / Recall (TPR) or the True Negative Rate / Spezificity (TNR) cannot be calculated')
    if not quiet: print(f'Informedness / Youden\'s J statistic: {informedness_youdenJ:.{N_of_decimals}f}')
    prevalence_threshold = np.nan
    if ((np.isnan(tpr) or np.isnan(fpr)) == False) and ((tpr - fpr) != 0):
        prevalence_threshold = (np.sqrt(tpr*fpr) - fpr)/(tpr - fpr)
    else:
        print('Prevalence threshold cannot be calculated as the True Positive Rate / Sensitivity / Recall (TPR) or the False Positive Rate (FPR) cannot be calculated')
    if not quiet: print(f'Prevalence threshold: {prevalence_threshold:.{N_of_decimals}f}')
    balanced_accuracy = np.nan
    if (np.isnan(tpr) or np.isnan(tnr)) == False:
        balanced_accuracy = (tpr + tnr)/2
    else:
        print('Balanced accuracy cannot be calculated as the True Positive Rate / Sensitivity / Recall (TPR) or the True Negative Rate / Spezificity (TNR) cannot be calculated')
    if not quiet: print(f'Balanced accuracy: {balanced_accuracy:.{N_of_decimals}f}')
    f1_score = np.nan
    if ((np.isnan(ppv) or np.isnan(tpr)) == False) and ((ppv + tpr) != 0):
        f1_score = (2 * ppv * tpr)/(ppv + tpr)
    else:
        print('F1 score cannot be calculated as the True Positive Rate / Sensitivity / Recall (TPR) or the Positive Predictive Value / Precision (PPV) cannot be calculated')
    if np.round(f1_score,N_of_decimals) != np.round(((2*tp)/(2*tp + fp + fn)),N_of_decimals):
        print('Problem with F1 score')
    if not quiet: print(f'F1 score: {f1_score:.{N_of_decimals}f}')
    LRpos = np.nan
    if ((np.isnan(fpr) or np.isnan(tpr)) == False) and (fpr != 0):
        LRpos = tpr/fpr
    else:
        print('Positive likelihood ratio score cannot be calculated as the True Positive Rate / Sensitivity / Recall (TPR) or the False Positive Rate (FPR) cannot be calculated')
    if not quiet: print(f'Positive likelihood ratio: {LRpos:.{N_of_decimals}f}')
    LRneg = np.nan
    if ((np.isnan(fnr) or np.isnan(tnr)) == False) and (tnr != 0):
        LRneg = fnr/tnr
    else:
        print('Negative likelihood ratio score cannot be calculated as the True Negative Rate / Spezificity (TNR) or the False Negative Rate (FNR) cannot be calculated')
    if not quiet: print(f'Negative likelihood ratio: {LRneg:.{N_of_decimals}f}')
    DiagOddsRatio = np.nan
    if ((np.isnan(LRpos) or np.isnan(LRneg)) == False) and (LRneg != 0):
        DiagOddsRatio = LRpos / LRneg
    else:
        print('Diagnostics Odds Ratio (DOR) cannot be calculated as the positive or negative likelihood ratio cannot be calculated')
    if not quiet: print(f'Diagnostics Odds Ratio (DOR): {DiagOddsRatio:.{N_of_decimals}f}')
    JaccardIndex = np.nan
    if (tp + fn + fp) != 0:
        JaccardIndex = tp/(tp + fn + fp)
    else:
        print('Jaccard Index cannot be calculated')
    if not quiet: print(f'Jaccard Index: {JaccardIndex:.{N_of_decimals}f}')
    res = np.array([total_population,p,n,pp,pn,tp,tn,fp,fn,prevalence,accuracy,ppv,npv,false_omission_rate,false_discovery_rate,tpr,tnr,fpr,fnr,informedness_youdenJ,prevalence_threshold,balanced_accuracy,f1_score,LRpos,LRneg,DiagOddsRatio,JaccardIndex])
    return np.round(res,N_of_decimals)

'''
    acc = np.sum(((gt == 1) & (i == 1) & (modal == 1)) + ((gt == 0) & (i == 0) & (modal == 1))) / np.sum(modal == 1)
    sen = np.sum((gt == 1) & (i == 1) & (modal == 1))/ np.sum((gt == 1) & (modal == 1))
    spez = np.sum((gt == 0) & (i == 0) & (modal == 1))/ np.sum((gt == 0) & (modal == 1))
    ppv = np.sum((gt == 1) & (i == 1) & (modal == 1))/ np.sum((i == 1) & (modal == 1))
    npv = np.sum((gt == 0) & (i == 0) & (modal == 1))/ np.sum((i == 0) & (modal == 1))
    print('acc %.1f'%(a*100))
    print('sens %.1f'%(sen*100))
    print('spez %.1f'%(spez*100))
    print('ppv %.1f'%(ppv*100))
    print('npv %.1f'%(npv*100))
'''

def mc_nemar_test(test1,test2,gt):
    data = [[np.sum((test1 == gt) & (test2 == gt)), np.sum((test1 == gt) & (test2 != gt))],
         [np.sum((test1 != gt) & (test2 == gt)), np.sum((test1 != gt) & (test2 != gt))]]
    print(mcnemar(data, exact=True))

def get_table_desc(var):
    print(np.sum(np.isnan(var)))
    print(get_desc(var[np.where(tzu.mri_mi == 1)[0]].dropna()))
    print(get_desc(var[np.where(tzu.mri_mi == 0)[0]].dropna()))
    x1 = var[np.where(tzu.mri_mi == 1)[0]].dropna()
    x2 = var[np.where(tzu.mri_mi == 0)[0]].dropna()
    print(scipy.stats.kruskal(x1, x2))
    print([np.sum(x1),np.sum(x2)])
    print([np.sum(x1)/len(np.where((tzu.mri_mi == 1))[0]),np.sum(x2)/len(np.where((tzu.mri_mi == 0))[0])])
    print([np.sum(x1),np.sum(x2)]/np.sum(var == 1))
    print(scipy.stats.chisquare([np.sum(x1),np.sum(x2)]))



# obs = np.array([[10, 72], [20, 69]])
# chi2, p, dof, ex = chi2_contingency(obs)
# print(chi2, dof, p)

def get_table_desc_m(var,var2):
    print(scipy.stats.kruskal(x1, x2))
    print([np.sum(x1),np.sum(x2)])
    print([np.sum(x1)/len(np.where((tzu.mri_mi == 1) & (var2 == 1))[0]),np.sum(x2)/len(np.where((tzu.mri_mi == 0) & (var2 == 1))[0])])
    print([np.sum(x1),np.sum(x2)]/np.sum(var == 1))
    print(scipy.stats.chisquare([np.sum(x1),np.sum(x2)]))
    obs = np.array([[np.sum(x1), len(np.where((tzu.mri_mi == 1) & (var2 == 1) & (var == 0))[0])], [np.sum(x2), len(np.where((tzu.mri_mi == 0) & (var2 == 1) & (var == 0))[0])]])
    chi2, p, dof, ex = chi2_contingency(obs)
    print(chi2, dof, p)



def get_CI_normd(x):
    n = len(x)
    t1 = scipy.stats.t.ppf(1-0.025, n-1)
    return np.append(np.mean(x),np.mean(x) + np.array([-t1,t1])*np.std(x,ddof = 1)/np.sqrt(n))

def get_CI_signrankdist(x):
    u1 = x
    diffs = np.add.outer(np.array(u1),np.array(u1))
    diffs = diffs[np.triu(np.ones(diffs.shape)).astype('bool')]
    diffs = np.sort(diffs.reshape([-1]))/2
    
    n = len(x)
    qu = qsignrank(0.025, n)
    if qu == 0:
        qu = 1
    ql = n*(n+1)/2 - qu
    med = np.median(diffs)
    return np.array([med, diffs[int(qu)-2], diffs[int(ql)+1]])

def get_p_signrank_glNull(x): #zweiseitig bei nur einer seite p nicht mit 2 multiplizieren
    abs_x = np.abs(np.array(x))
    ranks = np.argsort(np.argsort(abs_x)) + 1
    s = np.sum(ranks[x > 0])
    n = len(x)
    if s > (n*(n+1)/4):
        p = psignrank(s-1,n,lower_tail=False)
    else:
        p = psignrank(s,n)
    return np.min([2*p,1])

def get_CI_signrankdist_CC(x):
    mumin = np.min(x)
    mumax = np.max(x)
    alpha = 0.05
    zq = scipy.stats.norm.ppf(1 - alpha/2)
    sol = scipy.optimize.root_scalar(signrank_wdiff,args=(zq,x), bracket=[mumin, mumax], xtol=1e-4, method='brentq')
    l = sol.root
    zq = scipy.stats.norm.ppf(alpha/2)
    sol = scipy.optimize.root_scalar(signrank_wdiff,args=(zq,x), bracket=[mumin, mumax], xtol=1e-4, method='brentq')
    u = sol.root
    sol = scipy.optimize.root_scalar(signrank_wdiff,args=(0,x), bracket=[mumin, mumax], xtol=1e-4, method='brentq')
    ps = sol.root
    return np.array([ps,l,u])

def get_CI_wilcox(x,y):
    diffs = np.sort(np.subtract.outer(np.array(x),np.array(y)).reshape([-1]))
    n_x = len(x)
    n_y = len(y)
    qu = qwilcox(0.025, n_x,n_y)
    if qu == 0:
        qu = 1
    ql = n_x * n_y - qu
    med = np.median(diffs)
    return np.array([med, diffs[int(qu)-2], diffs[int(ql)+1]])

def get_p_wilcox_glNull(x,y): #zweiseitig bei nur einer seite p nicht mit 2 multiplizieren
    c = np.concatenate([np.array(x), np.array(y)])
    ranks = np.argsort(np.argsort(c)) + 1
    s = np.sum(ranks[np.arange(len(x))])
    n_x = len(x)
    n_y = len(y)
    s = s - n_x *(n_x+1)/2
    if s > (n_x*n_y/2):
        p = pwilcox(s-1,n_x,n_y,lower_tail=False)
    else:
        p = pwilcox(s,n_x,n_y)
    return np.min([2*p,1])

def relation_CI_normv(x,y):
    # x sind 100 prozent
    r = (x-y)/x
    return get_CI_normv(r)

def relation_CI_normv_abs(x,y):
    # x sind 100 prozent
    r = np.abs((x-y))/x
    if stdnormvert_test(r)[1]:
        print("r not normally distributed")
    return get_CI_normv(r)

def relation_CI_signrank(x,y):
    # x sind 100 prozent
    r = (x-y)/x
    return get_CI_signrankdist(r)

def relation_CI_signrank_abs(x,y):
    # x sind 100 prozent
    r = np.abs((x-y))/(x)
    return get_CI_signrankdist(r)

def relation_CI_signrank_mse(x,y):
    # x sind 100 prozent
    r = np.power((x-y),2)/(x*x)
    return get_CI_signrankdist(r)

def relation_CI_signrankdist_CC(x,y):
    r = (x-y)/x
    return get_CI_signrankdist_CC(r)

def relation_CI_signrankdist_CC_abs(x,y):
    r = np.abs((x-y))/x
    return get_CI_signrankdist_CC(r)

# auch nutzbar bei Bland altman plots
def within_subject_coefficient_of_variation(x,y):
    s2 = np.power((x-y),2)/2
    m = (x+y)/2
    s2m2 = s2/np.power(m,2)
    return np.sqrt(np.sum(s2m2))

# non- inferiorty und non-superiority testing
def sampleN0_noninf(lmargin, d0, se,alpha=0.025, targetpower=0.8, steps=2, bk=2):
    n0 = bk*np.power(se,2)*np.power(scipy.stats.norm.ppf(targetpower)+ scipy.stats.norm.ppf(1-alpha),2) / np.power((d0 - lmargin),2)
    n0 = steps*round(n0/steps,0)
    return n0

def power_noninf(alpha, lmargin, diffm, sem, df):
    tval = scipy.stats.t.ppf(1-alpha, df)
    tau  = (diffm-lmargin)/sem
    if lmargin>0:
        tau = -tau
    return 1 - scipy.stats.t.cdf(tval, df, loc = tau)

def size_noninf(cv,theta0,margin,alpha,targetpower,steps = 2, bk = 2):
    lmargin = margin
    diffm = theta0
    se = cv
    n = sampleN0_noninf(lmargin,diffm, se,alpha, targetpower, steps, bk)
    power = power_noninf(alpha, lmargin, diffm,sem=se*np.sqrt(bk/n), df=n-1)   # df = n-1 gilt für einen verbundenen t-test ggf. anpassen
    while power < targetpower:
        n += steps
        power = power_noninf(alpha, lmargin, diffm,sem=se*np.sqrt(bk/n), df=n-1)
    return n

# mögliche parameter
'''alpha=0.025
targetpower=0.8
margin = 0.2
theta0 = 0.05
cv = within_subject_coefficient_of_variation(u1,u2)'''




#im prinzip non inferiority oder non superiority von y
def non_inferiority_ttest(x,y, relad, alpha):
    # x sind die daten auf denen relative abweichungen erlaubt sind
    #relad -> vormals relative_difference
    '''
    H0 : y < x - delta; H1 y >= x - delta
    '''
    delta = x * relad
    threshold = x - delta
    tstat, pval = scipy.stats.ttest_rel(threshold,y,alternative='less')
    sig = 0
    if pval <= alpha:
        sig = 1
    return tstat, sig, pval
    
def non_superiority_ttest(x,y, relad, alpha):
    # x sind die daten auf denen relative abweichungen erlaubt sind
    '''
    H0 : y > x + delta; H1 y <= y + delta
    '''
    delta = x * relad
    threshold = x + delta
    tstat, pval = scipy.stats.ttest_rel(threshold,y,alternative='greater')
    sig = 0
    if pval <= alpha:
        sig = 1
    return tstat, sig, pval

def non_inferiority_wilcoxon(x,y, relad, alpha):
    # x sind die daten auf denen relative abweichungen erlaubt sind
    #relad -> vormals relative_difference
    '''
    H0 : y < x - delta; H1 y >= x - delta
    '''
    delta = x * relad
    threshold = x - delta
    tstat, pval = scipy.stats.wilcoxon(threshold,y,alternative='less')
    sig = 0
    if pval <= alpha:
        sig = 1
    return tstat, sig, pval

def non_superiority_wilcoxon(x,y, relad, alpha):
    # x sind die daten auf denen relative abweichungen erlaubt sind
    '''
    H0 : y > x + delta; H1 y <= y + delta
    '''
    delta = x * relad
    threshold = x + delta
    tstat, pval = scipy.stats.wilcoxon(threshold,y,alternative='greater')
    sig = 0
    if pval <= alpha:
        sig = 1
    return tstat, sig, pval

def non_superiority_wilcoxon_abs(x,y, relad, alpha):
    # x sind die daten auf denen relative abweichungen erlaubt sind
    '''
    H0 : y > x + delta; H1 y <= y + delta
    d.h. y-x > delta
    '''
    delta = x * relad
    tstat, pval = scipy.stats.wilcoxon(np.abs(delta),np.abs(y-x),alternative='greater')
    sig = 0
    if pval <= alpha:
        sig = 1
    return tstat, sig, pval

# plots
def rconf_int_plot(data,labels, x,title='',x_label='',y_label=''):
    maxy = data.shape[0]
    counter = 0
    for i in data:
        yline = maxy-counter
        plt.plot(i[0], yline, 'o', color='red')
        plt.fill_between([i[1], i[2]], [yline-0.2, yline-0.2], [yline+0.2, yline+0.2],color = 'cornflowerblue', alpha = 0.15)
        counter += 1
    lab = labels.copy()
    lab.reverse()
    x.set_yticks(np.arange(maxy)+1,lab)
    x.set_xlim([-1 , +1])
    x.spines['top'].set_visible(False)
    x.spines['right'].set_visible(False)
    x.spines['left'].set_visible(False)
    x.set_title(title,fontsize=22)
    x.set_xlabel(x_label,fontsize=20)
    x.set_ylabel(y_label,fontsize=20)
    x.tick_params(labelsize=18)

def CI_plot(data,labels,bound, x,title='',x_label='',y_label=''):
    maxy = data.shape[0]
    counter = 0
    for i in data:
        yline = maxy-counter
        plt.plot(i[0], yline, 'o', color='red')
        plt.fill_between([i[1], i[2]], [yline-0.2, yline-0.2], [yline+0.2, yline+0.2],color = 'cornflowerblue', alpha = 0.5)
        counter += 1
    lab = labels.copy()
    lab.reverse()
    x.set_yticks(np.arange(maxy)+1,lab)
    x.set_xlim([bound[0] , bound[1]])
    x.spines['top'].set_visible(False)
    x.spines['right'].set_visible(False)
    x.spines['left'].set_visible(False)
    x.set_title(title,fontsize=22)
    x.set_xlabel(x_label,fontsize=20)
    x.set_ylabel(y_label,fontsize=20)
    x.tick_params(labelsize=18)


def CI_plot_multi(datas,legend_labels,labels,bound, x,title='',x_label='',y_label=''):
    num = datas.shape[0]
    # colors = [plt.cm.get_cmap("Spectral")(i) for i in np.linspace(0, 1, num)]
    colors = [plt.cm.get_cmap("brg")(i) for i in np.linspace(0, 1, num)]
    counter_col = 0
    for data in datas:
        maxy = data.shape[0]
        color_data = colors.pop()
        if counter_col == 0:
            legend_handles = [
                plt.Line2D([], [], color=color_data, marker='s', linestyle='None')]
            counter_col += 1
        else:
            legend_handles.append(plt.Line2D([], [], color=color_data, marker='s', linestyle='None'))
        counter = 0
        for i in data:
            yline = maxy-counter
            plt.plot(i[0], yline, 'o', color=color_data)
            plt.fill_between([i[1], i[2]], [yline-0.2, yline-0.2], [yline+0.2, yline+0.2],color = color_data, alpha = 0.5)
            counter += 1
        lab = labels.copy()
        lab.reverse()
    plt.legend(handles=legend_handles, labels=legend_labels, loc='best',fontsize=20)
    x.set_yticks(np.arange(maxy)+1,lab)
    x.set_xlim([bound[0] , bound[1]])
    x.spines['top'].set_visible(False)
    x.spines['right'].set_visible(False)
    x.spines['left'].set_visible(False)
    x.set_title(title,fontsize=22)
    x.set_xlabel(x_label,fontsize=20)
    x.set_ylabel(y_label,fontsize=20)
    x.tick_params(labelsize=18)

def CI_plot_multi_sing(datas,legend_labels,labels,bound, x,title='',x_label='',y_label=''):
    num = datas.shape[0]
    # colors = [plt.cm.get_cmap("Spectral")(i) for i in np.linspace(0, 1, num)]
    colors = [plt.cm.get_cmap("brg")(i) for i in np.linspace(0, 1, num)]
    counter_col = 0
    counter_data = 0
    for data in datas:
        maxy = data.shape[0]
        color_data = colors.pop()
        if counter_col == 0:
            legend_handles = [
                plt.Line2D([], [], color=color_data, marker='s', linestyle='None')]
            counter_col += 1
        else:
            legend_handles.append(plt.Line2D([], [], color=color_data, marker='s', linestyle='None'))
        counter = 0
        for i in data:
            yline = maxy-counter
            plt.plot(i[0], yline - 0.5 + 1/(num+2) * (counter_data + 1.5), 'o', color='black')
            plt.fill_between([i[1], i[2]], [yline- 0.5 + 1/(num+2) * (counter_data + 1), yline- 0.5 + 1/(num+2) * (counter_data + 1)], [yline-0.5 + 1/(num+2) * (counter_data + 2), yline-0.5 + 1/(num+2) * (counter_data + 2)],color = color_data, alpha = 0.5)
            counter += 1
        lab = labels.copy()
        lab.reverse()
        counter_data += 1
    plt.legend(handles=legend_handles, labels=legend_labels, loc='best',fontsize=20)
    x.set_yticks(np.arange(maxy)+1,lab)
    x.set_xlim([bound[0] , bound[1]])
    x.spines['top'].set_visible(False)
    x.spines['right'].set_visible(False)
    x.spines['left'].set_visible(False)
    x.set_title(title,fontsize=22)
    x.set_xlabel(x_label,fontsize=20)
    x.set_ylabel(y_label,fontsize=20)
    x.tick_params(labelsize=18)



def bland_altman_bias_and_limits(data1, data2,N_of_decimals = 2, quiet = False):
    data1     = np.asarray(data1)
    data2     = np.asarray(data2)
    mean      = np.mean([data1, data2], axis=0)
    diff      = (data1 - data2)                   # Difference between data1 and data2
    md        = np.mean(diff)                   # Mean of the difference
    sd        = np.std(diff,ddof = 1, axis=0)            # Standard deviation of the difference
    popt, pcov = scipy.optimize.curve_fit(func_fit, mean, diff)
    if not quiet: print(f'The mean and upper and lower limit of error is: {md:.{N_of_decimals}f} \u00B1 {1.96*sd:.{N_of_decimals}f}')
    if not quiet: print(f'The constant bias is: {popt[1]:.{N_of_decimals}f}')
    if not quiet: print(f'The proportional bias is: {popt[0]:.{N_of_decimals}f}')
    return np.array([md, 1.96*sd,popt[0],popt[1]])







# signed rank distribution from R

#origninal braucht zu lange wegen speicher allokation
'''def csignrank(k, n):
    u = n * (n + 1) / 2
    c = (u / 2)
    if (k < 0) or (k > u):
        return 0
    
    if k > c:
        k = u - k
    
    if n == 1:
        return 1
    
    w = np.zeros(int(c+1))
    w[0] = 1
    w[1] = 1
    j = 2
    while j < n+1:
        end = np.min([j*(j+1)/2, c])
        i = int(end)
        while i >= j:
            w[i] += w[i-j]
            i -= 1
        j += 1
    return w[k]'''

def R_DT0(lower_tail):
    if lower_tail == True:
        return 0
    else:
        return 1
    
def R_DT1(lower_tail):
    if lower_tail == True:
        return 1
    else:
        return 0

def csignrank_defw(n):
    u = n * (n + 1) / 2
    c = (u / 2)
    if n == 1:
        return 1
    
    w = np.zeros(int(c)+1)
    w[0] = 1
    w[1] = 1
    j = 2
    while j < n+1:
        end = np.min([j*(j+1)/2, c])
        i = int(end)
        while i >= j:
            w[i] += w[i-j]
            i -= 1
        j += 1
    return w

def csignrank(k, n, w):
    u = n * (n + 1) / 2
    c = (u / 2)
    if (k < 0) or (k > u):
        return 0
    
    if k > c:
        k = u - k
    
    if n == 1:
        return 1
    
    if int(c)+1 != len(w):
        return "length error"
    
    return w[k]

def psignrank(x, n, lower_tail = True):
    if np.isnan(x) or np.isnan(n):
        return x+n
    if math.isinf(n):
        return "Infinity error"
    n = int(n)
    if n <= 0:
        return "Zero error"
    
    x = int(x + 1e-7)
    if x < 0:
        return R_DT0(lower_tail)
    if x > (n * (n + 1) / 2):
        return R_DT1(lower_tail)
    
    w = csignrank_defw(n)
    f = np.exp(-n * np.log(2))
    p = 0
    if x <= (n * (n + 1) / 4):
        i = 0
        while i <= x:
            p += csignrank(i, n,w) * f
            i += 1
    else:
        x = n * (n + 1) / 2 - x
        i = 0
        while i < x:
            p += csignrank(i, n,w) * f
            i += 1
        lower_tail = not lower_tail
    if lower_tail == True:
        return p
    else:
        return 1-p

def qsignrank(x, n, lower_tail = True):
    if np.isnan(x) or np.isnan(n):
        return x+n
    if math.isinf(n) | math.isinf(x):
        return "Infinity error"
    if (x < 0) | (x > 1):
        return "error p check"
    
    n = int(n)
    if n <= 0:
        return "Zero error"
    if x == R_DT0(lower_tail):
        return 0
    if x == R_DT1(lower_tail):
        return (n * (n + 1) / 2)
    
    if not lower_tail:
        x = 1-x
    
    w = csignrank_defw(n)
    f = np.exp(-n * np.log(2))
    p = 0
    q = 0
    if x <= 0.5:
        x = x - 10 * sys.float_info.epsilon
        while p < x:
            p += csignrank(q, n,w) * f
            q += 1
    else:
        x = 1 - x + 10 * sys.float_info.epsilon
        while p < x:
            p += csignrank(q, n,w) * f
            q += 1
        q = int((n * (n + 1) / 2 - q))
    return q

#benötigt bei der continuity correction -form
def signrank_wdiff(d,zq,x):
    xd = x - d
    xd = xd[xd != 0]
    nx = len(xd)
    abs_xd = np.abs(np.array(xd))
    dranks = np.argsort(np.argsort(abs_xd)) + 1
    zd = np.sum(dranks[xd > 0]) - nx * (nx + 1)/4
    nties_CI = Counter(dranks)
    i_1 = sum([val ** 3 - val for val in nties_CI.values()]) / 48
    sigma = np.sqrt(nx * (nx + 1) * (2 * nx + 1) / 24 - i_1)
    return (zd - np.sign(zd)*0.5) / sigma - zq

# wilcoxon distribution from R
def cwilcox_defw( m, n):
    u = m * n
    c = int(u / 2)
    if m < n:
        i = m
        j = n
    else:
        i = n
        j = m
    
    w = np.ones([i+1,j+1,c+1]) * (-1)
    return w

def cwilcox(k, m, n,w):
    w = w
    u = m * n
    if (k < 0) or (k > u):
        return 0
    c = int(u / 2)
    if k > c:
        k = u - k
    if m < n:
        i = m
        j = n
    else:
        i = n
        j = m
    
    if j == 0:
        return (k == 0)
    
    if (j > 0) and (k < j):
        return cwilcox(k, i, k,w)
    
    if w[i,j,k] < 0:
        if j == 0:
            w[i,j,k] = (k == 0)
        else:
            w[i,j,k] = cwilcox(k - j, i - 1, j,w) + cwilcox(k, i, j - 1,w)
    
    return w[i,j,k]

def pwilcox(q, m, n, lower_tail = True):
    if np.isnan(q) or np.isnan(m) or np.isnan(n):
        return q+m+n
    if math.isinf(m) or math.isinf(n):
        return "Infinity error"
    m = int(m)
    n = int(n)
    if (m <= 0) or (n <= 0):
        return "Zero error"
    
    q = int(q + 1e-7)
    if q < 0:
        return R_DT0(lower_tail)
    if q > (m*n):
        return R_DT1(lower_tail)
    
    c = math.comb(m+n,n) # wie viele möglichkeiten n aus m+n zu wählen also m+n über n
    p = 0
    w = cwilcox_defw( m, n)
    if q <= (m*n/2):
        i = 0
        while i <= q:
            p += cwilcox(i, m, n,w) / c
            i += 1
    else:
        q = m * n - q
        i = 0
        while i < q:
            p += cwilcox(i, m, n,w) / c
            i += 1
        lower_tail = not lower_tail
    
    if lower_tail == True:
        return p
    else:
        return 1-p

def qwilcox(x, m, n, lower_tail = True):
    if np.isnan(x) or np.isnan(m) or np.isnan(n):
        return x+m+n
    if math.isinf(x) or math.isinf(m) or math.isinf(n):
        return "Infinity error"
    if (x < 0) | (x > 1):
        return "error p check"
    
    m = int(m)
    n = int(n)
    if (m <= 0) or (n <= 0):
        return "Zero error"
    if x == R_DT0(lower_tail):
        return 0
    if x == R_DT1(lower_tail):
        return (m*n)
    
    if not lower_tail:
        x = 1-x
    
    c = math.comb(m+n,n)
    p = 0
    q = 0
    w = cwilcox_defw( m, n)
    if x <= 0.5:
        x = x - 10 * sys.float_info.epsilon
        while p < x:
            p += cwilcox(q,m, n,w) /c
            q += 1
    else:
        x = 1 - x + 10 * sys.float_info.epsilon
        while p < x:
            p += cwilcox(q, m,n,w) /c
            q += 1
        q = int((m*n) - q)
    return q

# input: x is casadi variable, xd is x - data and yd is y - data of measures
# ouput: linearized function that connects the datapoints of x - data and y - data
def punkt_def_function(x,xd, yd):
    if len(xd) == len(yd):
        f = ((yd[1] - yd[0])/(xd[1]- xd[0])*x + (yd[0]-((yd[1] - yd[0])/(xd[1]-xd[0]))*xd[0])) * ((x>=xd[0])*(x<xd[1]))
        if len(xd) > 2:
            i=2
            while i < len(xd):
                f = f+ ((yd[i] - yd[i-1])/(xd[i]- xd[i-1])*x + (yd[i-1]-((yd[i] - yd[i-1])/(xd[i]-xd[i-1]))*xd[i-1])) * ((x>=xd[i-1])*(x<xd[i]))
                i += 1
        return f
    else:
        print('Error: x - data and y - data do not have the same size')
        return None

# calculates mean function of list of functions - may be defined by statsmed.punkt_def_function
def mean_function(f_list):
    mfunc = f_list[0]
    if len(f_list) > 1:
        i = 0
        while i < len(f_list):
            mfunc += f_list[i]
            i += 1
    mfunc = mfunc / len(f_list)
    return mfunc

# calculates variance function of list of functions - may be defined by statsmed.punkt_def_function
def var_function(f_list):
    mfunc = mean_function(f_list)
    vfunc = (f_list[0]-mfunc)**2
    if len(f_list) > 1:
        i = 0
        while i < len(f_list):
            vfunc += (f_list[i]-mfunc)**2
            i += 1
    vfunc = vfunc / (len(f_list)-1)
    return vfunc

# returns max of a and b, whereas a and b may also be functions
def max(a,b):
    max = a * (a >= b) + b*(a < b)
    return max

# returns absolute valua of a, whereas a may also be a function
def abs(a):
    abs = max(a,-a)
    return abs

def Tfun(lf1,lf2):
    Tfun = abs(mean_function(lf1) - mean_function(lf2))/np.sqrt( (1/len(lf1))*var_function(lf1) + (1/len(lf2))*var_function(lf2))
    return Tfun

def functional_t_test_stat(x,lf1,lf2,sampler):
    Tfun_fR = Tfun(lf1,lf2)
    TfR_eval = ca.Function('f_eval', [x], [Tfun_fR])
    R = TfR_eval(sampler)
    R[np.where(np.isnan(R))[0]] = -np.inf
    TfR_max = np.max(R)
    return TfR_max

def functional_t_test_all_perm(x,lf1,lf2,sampler,Np_of_decimals = 3):
    T_org_max = functional_t_test_stat(x,lf1,lf2,sampler)
    f_all = lf1 + lf2
    count = 0
    T_coll = np.array([])
    for i in itertools.combinations(np.arange(len(f_all)),len(lf1)):
        if count != 0:
            inf_lst1 = []
            for ooi in i:
                inf_lst1 += [f_all[ooi]]
            inf_lst2 = []
            for ooi in np.setdiff1d(np.arange(len(f_all)),i):
                inf_lst2 += [f_all[ooi]]
            T_coll = np.append(T_coll,functional_t_test_stat(x,inf_lst1,inf_lst2,sampler))
        count += 1
    return [T_org_max, report_p_value(np.sum(T_coll > T_org_max)/count,Np_of_decimals)]

def functional_t_test(x,lf1,lf2,sampler,nnum,Np_of_decimals = 3):
    T_org_max = functional_t_test_stat(x,lf1,lf2,sampler)
    f_all = lf1 + lf2
    count = 0
    T_coll = np.array([])
    for i_cc in range(nnum):
        i = random.sample(np.arange(len(f_all)).tolist(),len(lf1))
        if count != 0:
            inf_lst1 = []
            for ooi in i:
                inf_lst1 += [f_all[ooi]]
            inf_lst2 = []
            for ooi in np.setdiff1d(np.arange(len(f_all)),i):
                inf_lst2 += [f_all[ooi]]
            T_coll = np.append(T_coll,functional_t_test_stat(x,inf_lst1,inf_lst2,sampler))
        count += 1
    return [T_org_max, report_p_value(np.sum(T_coll > T_org_max)/count,Np_of_decimals)]

def functional_corr_vec(x,lf,sampler):
    len_lf = len(lf)
    corr_vec = np.array([])
    for i1 in range(len_lf):
        for i2 in range(len_lf):
            if i1 < i2:
                f1 = ca.Function('f_eval', [x], [lf[i1]])
                f2 = ca.Function('f_eval', [x], [lf[i2]])
                corr_vec = np.append(corr_vec,scipy.stats.spearmanr(f1(sampler), f2(sampler))[0])
    return corr_vec

def functional_corr_test_stat(x,lf1,lf2,sampler,Np_of_decimals = 3):
    corrv_f1 = functional_corr_vec(x,lf1,sampler)
    corrv_f2 = functional_corr_vec(x,lf2,sampler)
    m1 = np.mean(corrv_f1)
    m2 = np.mean(corrv_f2)
    v1 = np.var(corrv_f1)
    v2 = np.var(corrv_f2)
    lcorrv_f1 = len(corrv_f1)
    lcorrv_f2 = len(corrv_f1)
    sq2 = np.sqrt(((lcorrv_f1-1)*v1 + (lcorrv_f2-1)*v2)/(lcorrv_f1 + lcorrv_f2 - 2))
    t = np.sqrt((lcorrv_f1*lcorrv_f2)/(lcorrv_f1 + lcorrv_f2)) * ((m1 - m2)/sq2)
    return [t,report_p_value(scipy.stats.ttest_ind(corrv_f1, corrv_f2)[1],Np_of_decimals)]

def functional_corr_test_all_perm(x,lf1,lf2,sampler,Np_of_decimals = 3):
    T_org = functional_corr_test_stat(x,lf1,lf2,sampler)[0]
    f_all = lf1 + lf2
    count = 0
    T_coll = np.array([])
    for i in itertools.combinations(np.arange(len(f_all)),len(lf1)):
        if count != 0:
            inf_lst1 = []
            for ooi in i:
                inf_lst1 += [f_all[ooi]]
            inf_lst2 = []
            for ooi in np.setdiff1d(np.arange(len(f_all)),i):
                inf_lst2 += [f_all[ooi]]
            T_coll = np.append(T_coll,functional_corr_test_stat(x,inf_lst1,inf_lst2,sampler)[0])
        count += 1
    return [T_org, report_p_value(np.sum(T_coll > T_org)/count,Np_of_decimals)]

def functional_corr_test(x,lf1,lf2,sampler,nnum,Np_of_decimals = 3):
    T_org = functional_corr_test_stat(x,lf1,lf2,sampler)[0]
    f_all = lf1 + lf2
    count = 0
    T_coll = np.array([])
    for i_cc in range(nnum):
        i = random.sample(np.arange(len(f_all)).tolist(),len(lf1))
        if count != 0:
            inf_lst1 = []
            for ooi in i:
                inf_lst1 += [f_all[ooi]]
            inf_lst2 = []
            for ooi in np.setdiff1d(np.arange(len(f_all)),i):
                inf_lst2 += [f_all[ooi]]
            T_coll = np.append(T_coll,functional_corr_test_stat(x,inf_lst1,inf_lst2,sampler)[0])
        count += 1
    return [T_org, report_p_value(np.sum(T_coll > T_org)/count,Np_of_decimals)]



