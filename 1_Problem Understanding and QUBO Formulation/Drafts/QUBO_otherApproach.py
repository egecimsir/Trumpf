# -*- coding: utf-8 -*-
"""
Created on Tue May 25 15:22:04 2021

@author: trohe
"""
import pandas as pd
import numpy as np
import sys

d = {'OrderNo' : [], 'PartNo' : [], 'BendingLines' : [], 'WeldingPoints' : [], 'PaintTime' : [], 'DueDate' : []}
orderDF = pd.DataFrame(data=d)

path = r"C:\Users\trohe\Desktop\Studium Informatik\4. Sem info\Quantencomputing\QUBO\OrdersGenerated.txt"
orders = open(path, "r")
orders = orders.readlines()
orders = orders[1:]
for i in range(len(orders)):
    orders[i] = orders[i].split(', ')
    actualOrder = orders[i]
    newRow = {'OrderNo' : actualOrder[0], 
              'PartNo' : actualOrder[1], 
              'BendingLines' : actualOrder[2], 
              'WeldingPoints' : actualOrder[3], 
              'PaintTime' : actualOrder[4], 
              'DueDate' : actualOrder[5]}
    orderDF = orderDF.append(newRow, ignore_index = True)    

orderDF = orderDF.astype('int64')

#for simplicity the following lines:
orderDF = orderDF.iloc[0:3][:]

#about jobs
jobs_data = []
for i in orderDF.index:
    if not orderDF.iloc[i]['BendingLines'] == 0:
        {}
    if not orderDF.iloc[i]['WeldingPoints'] == 0:
        {}
    if not orderDF.iloc[i]['PaintTime'] == 0:
        {}

M = 6 #number of machines
bend = ['m0', 'm1', 'm2']
solder = ['m3', 'm4']
paint = ['m5']

#O is the number of operations to perform
O = orderDF['BendingLines'].sum() + orderDF['WeldingPoints'].sum() + orderDF['PaintTime'].sum() 

#represents the maximum of timesteps needed
T = orderDF['BendingLines'].sum() * 2 + orderDF['WeldingPoints'].sum() * 3 + orderDF['PaintTime'].sum() * 6  

quboLength = T * M * O
QUBO = np.zeros((quboLength, quboLength))

#index conversions
def convert_into_index(o, m, t):
    return M*T*o + T*m + t

def convert_from_index(idx):
    o = idx // (M*T)
    m = (idx - o*M*T)//T
    t = (idx - o*M*T - m*T)
    return o, m, t

def fill_QUBO_with_indexes(QUBO, o1, m1, t1, o2, m2, t2, value):
    index_a = convert_into_index(o1, m1, t1)
    index_b = convert_into_index(o2, m2, t2)
    if index_a > index_b:
        index_a, index_b = index_b, index_a
    QUBO[index_a][index_b] += value

def get_operation_indexes_for_job_j(j, jobs):
    op_idx = 0
    for i in range(j):
        for o in jobs[i]:
            op_idx += 1
    return list(range(op_idx, op_idx + len(jobs[j])))

def get_operation_x(x, jobs):
    op_idx = 0
    for j in jobs:
        for o in j:
            if op_idx == x:
                return o
            op_idx += 1

def get_operation_indexes_for_machine_m(m, jobs):
    indexes = []
    op_idx = 0
    for j in jobs:
        for o in j:
            if o[0] == m:
                indexes.append(op_idx)
            op_idx += 1
    return indexes

#filling the QUBO
#h0
alpha = 1
def __add_h0_constraint(QUBO):
    for i in range(O):
        for j in range(M):
            for u in range(T):
                for t in range(u):
                    fill_QUBO_with_indexes(QUBO, i, j, t, i, j, u, alpha * 2)
                for t in range(T):
                    fill_QUBO_with_indexes(QUBO, i, j, t, i, j, t, -alpha)

__add_h0_constraint(QUBO)

#h1
beta = 1
def __add_h1_constraint(QUBO):
    nbr_jobs = len(jobs_data)
    for j in range(nbr_jobs):
        for o in get_operation_indexes_for_job_j(j, jobs_data)[:-1]:
            for m in range(M):
                for t in range(T):
                    for t_prime in range(T):
                        if (t + get_operation_x(o, jobs_data)[1]) > t_prime:
                            fill_QUBO_with_indexes(QUBO, o, m, t, o + 1, m, t_prime, beta)

__add_h1_constraint(QUBO)

#h2
gamma = 1
def __add_h2_constraint(QUBO):
    def Rm_condition_fulfilled(o, m, t, o2, m2, t_prime, T, jobs):
        return o != o2 and 0 <= t and t_prime <= T and 0 <= t_prime - t < get_operation_x(o, jobs)[1]

        nbr_machines = M #fraglich ob das M hier das richtige beschreibt
        for m in range(nbr_machines):
            operation_indexes_m = get_operation_indexes_for_machine_m(m, jobs_data)
            for o in operation_indexes_m:
                for o2 in operation_indexes_m:
                    for t in range(T):
                        for t_prime in range(T):
                            if Rm_condition_fulfilled(o, m, t, o2, t_prime, T, jobs_data):
                                fill_QUBO_with_indexes(QUBO, o, m, t, o2, m, t_prime, gamma)
__add_h2_constraint(QUBO)

'''
orderDF : all Job information


J : the set of all jobs to do
|J| : number of rows in orderDF
(b, w, p)j : operations to perform for job j, where b represents bending, w for
             welding, and p for painting




'''



