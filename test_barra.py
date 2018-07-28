import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import style
import sklearn
import time
import scipy.stats as sps
import pandas as pd
import datetime
import pickle
import csv
import cvxpy as cp

from scipy import linalg
from risk_adj import Covariance_NW, NW_adjusted, Eigen_adjusted



def v_fitting(gamma_k,amp=2,n_start_fitting = 16):

    y = gamma_k[n_start_fitting:]
    x = np.array(range(n_start_fitting,40))
    z = np.polyfit(x, y, 2)
    p = np.poly1d(z)
    gamma_k_new = [p(xi) for xi in range(n_start_fitting)]+list(y)
    
    gamma_k_new = amp*(np.array(gamma_k_new)-1)+1
    
    return gamma_k_new

def v_fitting_modified(gamma_k,amp=1.6,n_start_fitting = 15):

    y = gamma_k[n_start_fitting:]
    x = np.array(range(n_start_fitting,40))
    z = np.polyfit(x, y, 2)
    p = np.poly1d(z)
    gamma_k_new = [p(xi) for xi in range(n_start_fitting)]+list(y)
    gamma_k_new=np.array(gamma_k_new)+0.05
    
    gamma_k_new[:33] = amp*(np.array(gamma_k_new[:33])-1.05)+1.05
    
    return np.array(gamma_k_new)

def EWMA(n=252,tau=42,norm=1):
    
    lambd = 0.5**(1./tau)
    
    w = np.array([lambd**n for n in range(252)][::-1])
    
    if norm:
        return w/w.sum()
    else:
        return w


def Get_data_spr():
    
    data_spr = pd.read_csv('factors_000905_2010_2018_spr.csv')
    data_spr = data_spr.sort_values(['TRADEDATE'])
    dates = data_spr['TRADEDATE'].drop_duplicates().tolist()
    data_spr_ = data_spr[['STOCKCODE','TRADEDATE','specific_r']]
    
    stocks_all = list(set(data_spr_['STOCKCODE'].tolist()))
    spr_data = pd.DataFrame(np.arange(len(stocks_all)))
    spr_data.index = stocks_all
    
    for i in range(len(dates)):
        
        data_frame = data_spr_[data_spr_['TRADEDATE']==dates[i]][['STOCKCODE','specific_r']]
        data_frame.index = data_frame.STOCKCODE
       
        del data_frame['STOCKCODE']
        
        spr_data = pd.concat([spr_data,data_frame],axis=1)
    
    spr_data = spr_data.sort_index()
    del spr_data[0]
    
    dates = [str(x)[:4]+'-'+str(x)[4:6]+'-'+str(x)[6:] for x in dates]
    #dates = [datetime.strptime(x, "%Y-%m-%d") for x in dates]
    spr_data.columns = dates
    
    return spr_data

def Get_data_r():
    data_spr = pd.read_csv('factors_000905_2010_2018_spr.csv')
    data_spr = data_spr.sort_values(['TRADEDATE'])
    dates = data_spr['TRADEDATE'].drop_duplicates().tolist()
    data_spr_ = data_spr[['STOCKCODE','TRADEDATE','RET']]
    
    stocks_all = list(set(data_spr_['STOCKCODE'].tolist()))
    spr_data = pd.DataFrame(np.arange(len(stocks_all)))
    spr_data.index = stocks_all
    
    for i in range(len(dates)):
        
        data_frame = data_spr_[data_spr_['TRADEDATE']==dates[i]][['STOCKCODE','RET']]
        data_frame.index = data_frame.STOCKCODE
       
        del data_frame['STOCKCODE']
        
        spr_data = pd.concat([spr_data,data_frame],axis=1)
    
    spr_data = spr_data.sort_index()
    del spr_data[0]
    
    dates = [str(x)[:4]+'-'+str(x)[4:6]+'-'+str(x)[6:] for x in dates]
    #dates = [datetime.strptime(x, "%Y-%m-%d") for x in dates]
    spr_data.columns = dates
    
    return spr_data









data_factor = pd.read_csv('factor_r_sqrt_000905.csv')
data_factor = data_factor.iloc[:,2:]
data_factor = data_factor.dropna()

length = 252
n_forward = 21
tau = 90

Bias=[]
stat_all=[]

for i in range(length,data_factor.shape[0]-n_forward,10):
    
    if i%20==0: print("i: ",i)
    
    data_cov, U, F_NW, R_i, Std_i = NW_adjusted(data_factor,tau=tau,length=length,n_start=i,NW=0)
    
    Bias.append(R_i/Std_i)
    
    stat = Eigen_adjusted(F_NW,U,Std_i,length=length,N_mc=1000)
    stat_all.append(stat)

    


Bias = np.array(Bias)
Bias_eigen = [np.std(Bias[:,x]) for x in range(Bias.shape[1])]
gamma_k = np.array(stat_all).mean(axis=0)

gamma_k_new = Gamma_fitting(gamma_k,amp=2.,n_start_fitting=15)






spr_data = Get_data_spr()



weights = EWMA(n=252,tau=42,norm=1)

length = 252
n_forward = 21
tau = 90
n_dates = data_factor.shape[0]

BF_t_all=[]
CSV = []
lambda_F=[]
lambda_F_all=[]
BF_t_vra_all=[]

portfolio={}

for i in range(length,n_dates-n_forward,1):
    
    
    date_i = dates[i]
    
    data_cov, U, F_NW, R_i, Std_i = NW_adjusted(data_factor,tau=tau,n_start=i,NW=1)
    
    s, U = linalg.eigh(F_NW)
    
    # eigen adjusted
    F_eigen = U@(np.diag(np.power(gamma_k_new,2))@np.diag(s))@U.T
    
    f_kt = data_factor.iloc[i,:].values
    b_ = f_kt / np.sqrt(np.diag(F_eigen))
    BF_t = np.sqrt(np.mean(b_@b_))
    BF_t_all.append(BF_t)
        
    
    if i>length+252 and (i-length-252)%10==0:
        lambda_F = np.sqrt( np.power(BF_t_all[i-length-252:i-length],2) @ weights )
        lambda_F_all.append( lambda_F )
    
        F_VRA = np.diag([lambda_F**2]*F_eigen.shape[0])@F_eigen 
        b_vra = f_kt / np.sqrt(np.diag(F_VRA))
        BF_t = np.sqrt(np.mean(b_vra@b_vra))
        BF_t_vra_all.append(BF_t)
    
        X = data_spr[data_spr['TRADEDATE']==date_i]
        X = X.sort_values(by=['STOCKCODE'])
        stocks_i =  X['STOCKCODE'].tolist()
        X = X.iloc[:,4:-2]
        X = np.concatenate([np.ones((X.shape[0],1)), X ],axis=1)
        
        
        Risk_1 = X @ F_VRA @ X.T
        
        data_temp = spr_data.iloc[:,i-length:i]
        data_temp = data_temp.loc[stocks_i]
        data_temp = data_temp.fillna(0)
        specific_risk = np.diag(data_temp.var(axis=1).values)
        
        Risk = Risk_1 + specific_risk

        P = cp.Variable(Risk.shape[0])
        objective = cp.Minimize(cp.quad_form(P, Risk))
        '''
        constraints = [
            0 <= P, P <= 0.05,
            cp.sum_entries(P) == 1
        ]
        '''
        constraints = [
            0 <= P, P <= 0.1,
            cp.sum_entries(P) == 1
        ]
        
        prob = cp.Problem(objective, constraints)
        result = prob.solve()
        
        port_i = pd.DataFrame(P.value,index=stocks_i)
        port_i = port_i[port_i[0]>0.001]
        
        portfolio[str(date_i)] = port_i
        
        print(date_i,port_i.shape[0])


def cal_bais_stat(data_factor,length=252,n_forward=21,tau=90,N_mc=1000,NW=0):

    Bias=[]
    stat_all=[]
    
    for i in range(length,data_factor.shape[0]-n_forward,50):
        
        print("# %1d/%1d" %(i,data_factor.shape[0]-n_forward))
        
        data_cov, U, F_NW, R_i, Std_i = NW_adjusted(data_factor,tau=tau,length=length,n_start=i,NW=0)
        
        Bias.append(R_i/Std_i)
        
        stat = Eigen_adjusted(F_NW,U,Std_i,length=length,N_mc=N_mc)
        stat_all.append(stat)
    
    Bias = np.array(Bias)
    bias_eigen = [np.std(Bias[:,x]) for x in range(Bias.shape[1])]
    
    return bias_eigen,stat_all










data_factor = pd.read_csv('factor_r_sqrt_000905.csv')
data_factor = data_factor.iloc[:,2:]
data_factor = data_factor.dropna()

length = 252
n_forward = 21
tau = 90


bias_eigen,stat_all = cal_bais_stat(data_factor,length=252,n_forward=21,tau=90,N_mc=1000,NW=0)

v_k = np.array(stat_all).mean(axis=0)
v_k_new = v_fitting_modified(v_k,amp=2.,n_start_fitting=16)


'''
# Bias statistics of eigenfactors using the unadjusted covariance matrix 
# Figure 4.1 of UNE4
plt.plot(bias_eigen,'-*')

# Simulated volatility bias 
# Figure 4.3 of UNE4, plot every simulation result
for i in range(len(stat_all)):
    plt.plot(stat_all[i])

# Mean simulated volatility bias 
# Figure 4.3 of UNE4
plt.plot(v_k)

# Mean simulated volatility bias 
# Figure 4.3 of UNE4
plt.plot(v_k_new)
'''


# get specific return data
spr_ret = Get_data_spr()
data_spr = pd.read_csv('factors_000905_2010_2018_spr.csv')
data_spr['TRADEDATE'] = [str(x)[:4]+'-'+str(x)[4:6]+'-'+str(x)[6:] for x in data_spr['TRADEDATE'].tolist()]

dates = spr_ret.columns.tolist()

weights = EWMA(n=252,tau=42,norm=1)

length = 252
n_forward = 21
tau = 90
n_dates = data_factor.shape[0]

BF_t_all=[]
CSV = []
lambda_F=[]
lambda_F_all=[]
BF_t_vra_all=[]

portfolio={}

for i in range(length,n_dates-n_forward,1):
    
    date_i = dates[i]
    
    data_cov, U, F_NW, R_i, Std_i = NW_adjusted(data_factor,tau=tau,n_start=i,NW=1)
    
    s, U = linalg.eigh(F_NW)
    
    # eigen adjusted
    F_eigen = U@(np.diag(np.power(gamma_k_new,2))@np.diag(s))@U.T
    
    f_kt = data_factor.iloc[i,:].values
    b_ = f_kt / np.sqrt(np.diag(F_eigen))
    BF_t = np.sqrt(np.mean(b_@b_))
    BF_t_all.append(BF_t)
        
    
    if i>length+252 and (i-length-252)%20==0:
        lambda_F = np.sqrt( np.power(BF_t_all[i-length-252:i-length],2) @ weights )
        lambda_F_all.append( lambda_F )
    
        F_VRA = np.diag([lambda_F**2]*F_eigen.shape[0])@F_eigen 
        b_vra = f_kt / np.sqrt(np.diag(F_VRA))
        BF_t = np.sqrt(np.mean(b_vra@b_vra))
        BF_t_vra_all.append(BF_t)
    
        X = data_spr[data_spr['TRADEDATE']==date_i]
        X = X.sort_values(by=['STOCKCODE'])
        stocks_i =  X['STOCKCODE'].tolist()
        X = X.iloc[:,4:-2]
        X = np.concatenate([np.ones((X.shape[0],1)), X ],axis=1)
        
        
        Risk_1 = X @ F_VRA @ X.T
        
        data_temp = spr_ret.iloc[:,i-length:i]
        data_temp = data_temp.loc[stocks_i]
        data_temp = data_temp.fillna(0)
        specific_risk = np.diag(data_temp.var(axis=1).values)
        
        Risk = Risk_1 + specific_risk

        P = cp.Variable(Risk.shape[0])
        objective = cp.Minimize(cp.quad_form(P, Risk))
        '''
        constraints = [
            0 <= P, P <= 0.05,
            cp.sum_entries(P) == 1
        ]
        '''
        constraints = [
            0 <= P, P <= 0.02,
            cp.sum_entries(P) == 1
        ]
        
        prob = cp.Problem(objective, constraints)
        result = prob.solve()
        
        port_i = pd.DataFrame(P.value,index=stocks_i)
        port_i = port_i[port_i[0]>0.001]
        
        portfolio[str(date_i)] = port_i
        
        print(date_i,port_i.shape[0])

















