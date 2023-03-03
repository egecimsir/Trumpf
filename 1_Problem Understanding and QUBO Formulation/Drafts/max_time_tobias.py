# -*- coding: utf-8 -*-
"""
Created on Sat May 29 19:11:29 2021

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
#orderDF = orderDF.iloc[0:3][:]

##############################################################################

def max_time_new(jobs):
    a = 0 
    b = 0 
    c = 0
    for i in jobs.index:
        actualTime = jobs.iloc[i]['BendingLines']
        if a < b and a < c:
            a += actualTime
        elif b < a and b < c:
            b += actualTime
        else:
            c += actualTime
    maximumBending = max(a, b, c) * 2
    
    a = 0
    b = 0
    for i in jobs.index:
        actualTime = jobs.iloc[i]['WeldingPoints']
        if a < b:
            a += actualTime
        else:
            b += actualTime
    maximumWelding = max(a, b) * 3
    
    maximumPainting = sum(jobs.PaintTime) * 6
    
    return maximumBending + maximumWelding + maximumPainting


##############################################################################
    
bend_dauer = 2
weld_dauer = 3
paint_dauer = 6    
def max_time(jobs):
    t = 0
    for x in jobs.index:
        t += jobs.iloc[x]['BendingLines'] * bend_dauer + jobs.iloc[x]['WeldingPoints'] * weld_dauer + jobs.iloc[x]['PaintTime'] * paint_dauer
    return t




