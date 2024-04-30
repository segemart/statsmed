import numpy as np
import scipy
import math
import sys
from collections import Counter
import matplotlib.pyplot as plt

'''test of normality using the: 1. Shapiro-Wilk-Test and 2. Kolmogorow-Smirnow-Test
Kolmogorow-Smirnow-Test requires normalization but not Shapiro-Wilk-Test
Input: array of test-data - please exclude NaN oder None Values.
Output: 0 if both tests do not indicate a significant difference from a normal distribution and 1 if at least ones does,
        0 if Shapiro-Wilk-Test does not indicate a significant difference from a normal distribution and 1 if does,
        0 if Kolmogorow-Smirnow-Test does not indicate a significant difference from a normal distribution and 1 if does,
        Test-statistic of Shapiro-Wilk-Test,
        p-value of Shapiro-Wilk-Test,
        test-statistic of Kolmogorow-Smirnow-Test,
        p-value of Kolmogorow-Smirnow-Test
'''
def stdnorm_test(x):
    SWn = 0
    [t1,z1] = scipy.stats.shapiro(x)
    if z1 < 0.05:
        SWn = 1
        print(f"Shapiro-Wilk: No normal dsitribution (p-value = {z1:.4f})")
    else:
        SWn = 0
        print(f"Shapiro-Wilk: Normal dsitribution (p-value = {z1:.2f} \n \t - p-value >= 0.05 indicates no significant difference from normal distribution)")
    KSn = 0
    [t2,z2] = scipy.stats.kstest((x - np.mean(x))/np.std(x,ddof = 1),scipy.stats.norm.cdf)
    if z2 < 0.05:
        KSn = 1
        print(f"Kolmogorow-Smirnow: No normal dsitribution (p-value = {z2:.4f})")
    else:
        KSn = 0
        print(f"Kolmogorow-Smirnow: Normal dsitribution (p-value = {z2:.2f} \n \t - p-value >= 0.05 indicates no significant difference from normal distribution)")
    Fn = 0
    if (z1 < 0.05) or (z2 < 0.05):
        Fn = 1
        print("At least one test indicates no normal distribution")
    else:
        Fn = 0
        print("Both tests do not indicate a significant difference from a normal distribution")
    return [Fn,SWn,KSn,t1,z1,t2,z2]

def get_CI_normv(x):
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

def get_desc(u,mode = 'choose'):
    print("u" + str(np.sum(np.isnan(u))))
    u = u.dropna()
    [t1,z1] = scipy.stats.kstest((u - np.mean(u))/np.std(u,ddof = 1),scipy.stats.norm.cdf)
    if mode == 'both':
        return [['normalverteilt', np.mean(u), scipy.stats.t.interval(alpha=0.95, df=len(u)-1, loc=np.mean(u), scale=scipy.stats.sem(u))],['nicht normalverteilt', np.percentile(u,50), np.percentile(u, (25,75))]]
    if mode == 'np':
        return ['nicht normalverteilt', np.percentile(u,50), np.percentile(u, (25,75))]
    if mode == 'p':
        return ['normalverteilt', np.mean(u), scipy.stats.t.interval(alpha=0.95, df=len(u)-1, loc=np.mean(u), scale=scipy.stats.sem(u))]
    if z1 <= 0.05:
        return ['nicht normalverteilt', np.percentile(u,50), np.percentile(u, (25,75))]
    else:
        return ['normalverteilt', np.mean(u), scipy.stats.t.interval(alpha=0.95, df=len(u)-1, loc=np.mean(u), scale=scipy.stats.sem(u))]

def comp_two_gr(u1,u2, mode = 'choose'):
    # 1 nicht normalverteilt = nicht parametrisch (np)
    # 0 normalverteilt = parametrisch (p)
    print("u1" + str(np.sum(np.isnan(u1))))
    print("u2" + str(np.sum(np.isnan(u2))))
    # u1 = u1.dropna()
    # u2 = u2.dropna()
    [t1,z1] = scipy.stats.kstest((u1 - np.mean(u1))/np.std(u1,ddof = 1),scipy.stats.norm.cdf)
    [t2,z2] = scipy.stats.kstest((u2 - np.mean(u2))/np.std(u2,ddof = 1),scipy.stats.norm.cdf)
    [tnp,pnp] = scipy.stats.ranksums(u1,u2)
    [tp,pp] = scipy.stats.ttest_ind(u1, u2, equal_var=False)
    if mode == 'both':
        return [[1,tnp,pnp],[0,tp,pp]]
    if mode == 'np':
        return [1,tnp,pnp]
    if mode == 'p':
        return [0,tp,pp]
    if z1 <= 0.05 or z2 <= 0.05:
        return [1,tnp,pnp]
    else:
        return [0,tp,pp]

def corr_two_gr(u1,u2,mode = 'choose'):
    #spearman = 1
    #pearson = 0
    print("u1" + str(np.sum(np.isnan(u1))))
    print("u2" + str(np.sum(np.isnan(u1))))
    # u1 = u1.dropna()
    # u2 = u2.dropna()
    [t1,z1] = scipy.stats.kstest((u1 - np.mean(u1))/np.std(u1,ddof = 1),scipy.stats.norm.cdf)
    [t2,z2] = scipy.stats.kstest((u2 - np.mean(u2))/np.std(u2,ddof = 1),scipy.stats.norm.cdf)
    [r,p] = scipy.stats.spearmanr(u1, u2)
    s2 = (1 + np.power(r,2)/2)/(len(u1)-3)
    confrs = [np.tanh(np.arctanh(r) - np.sqrt(s2) * scipy.stats.norm.ppf(0.975)) , np.tanh(np.arctanh(r) + np.sqrt(s2) * scipy.stats.norm.ppf(0.975))]
    a = np.array([1,p,r,confrs[0],confrs[1]])
    a = np.expand_dims(a, axis=0)
    [r,p] = scipy.stats.pearsonr(u1, u2)
    zr = np.arctanh(r)
    se = 1/np.sqrt(len(u1)-3)
    z = scipy.stats.norm.ppf(1-0.05/2)
    lo_z, hi_z = zr-z*se, zr+z*se
    confrr = np.tanh((lo_z, hi_z))
    a = np.append(a,np.expand_dims(np.array([0,p,r,confrr[0],confrr[1]]), axis=0),axis = 0)
    if mode == 'both':
        return a
    if mode == 's':
        return a[0,:]
    if mode == 'p':
        return a[1,:]
    if z1 <= 0.05 or z2 <= 0.05:
        return a[0,:]
    else:
        return a[1,:]

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

def bland_altman_plot(data1, data2, x,title='',x_label='Mean of raters',y_label='Difference in seconds between raters'):
    data1     = np.asarray(data1)
    data2     = np.asarray(data2)
    mean      = np.mean([data1, data2], axis=0)
    # diff      = (data1 - data2)/data2 * 100                   # Difference between data1 and data2
    diff      = (data1 - data2)                   # Difference between data1 and data2
    md        = np.mean(diff)                   # Mean of the difference
    sd        = np.std(diff,ddof = 1, axis=0)            # Standard deviation of the difference
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
    
    x.set_title(title,fontsize=22)
    x.set_xlabel(x_label,fontsize=20)
    x.set_ylabel(y_label,fontsize=20)
    x.tick_params(labelsize=18)



def bland_altman_bias_and_limits(data1, data2):
    data1     = np.asarray(data1)
    data2     = np.asarray(data2)
    diff      = (data1 - data2)                   # Difference between data1 and data2
    md        = np.mean(diff)                   # Mean of the difference
    sd        = np.std(diff,ddof = 1, axis=0)            # Standard deviation of the difference
    return np.array([md, 1.96*sd])







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
























