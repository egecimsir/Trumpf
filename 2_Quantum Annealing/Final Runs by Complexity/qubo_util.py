import matplotlib.pylab as plt
import numpy as np
import pandas as pd
import networkx as nx
import plotly.express as px
import seaborn as sns
import random

from dwave_qbsolv import QBSolv

import dimod
import neal
from dwave.system.samplers import DWaveSampler
from dwave.system.composites import EmbeddingComposite
from dwave.system import LeapHybridSampler
import dwave.inspector

from uqoclient.client.connection import Connection
from uqoclient import Problem
from uqoclient.client.config import Config

import plotly.express as px
import plotly.graph_objects as go
from prettytable import PrettyTable


#Data Generator provided by TRUMPF
def data_generator_trumpf():
    # Data Generator for the Job Shop Scheduling Problem
    # open file streams
    file = open("OrdersGenerated.txt", "w")
    file.write("OrderNo, PartNo, BendingLines, WeldingPoints, PaintTime, DueDate \n")

    # Number of Orders
    for i in range(0, 15):

        noOfParts = 1 + int(random.random() * 3)  # number of parts
        totalWelding = 0
        totalBending = 0
        totalPainting = 0
        resultArray = []

        for j in range(0, noOfParts):

            # BendingLines, every part has bending lines, unifrom distribution
            bendLines = 1 + int(random.random() * 8)

            # WeldingPoints, unifrom distribution
            weldPointsRnd = random.random()
            if weldPointsRnd < 0.15:
                weldPoints = 0
            else:
                weldPoints = 1 + int(random.random() * 14)

            # PaintTime
            weldPointsRnd = random.random()
            if weldPointsRnd < 0.25:
                PaintTime = 0
            else:
                PaintTime = 3 + int(random.random() * 6)

            # Statistics
            totalBending = totalBending + bendLines
            totalWelding = totalWelding + weldPoints
            totalPainting = totalPainting + PaintTime

            # Save to file
            partResultArray = [
                str(i) + ", " + str(j) + ", " + str(bendLines) + ", " + str(weldPoints) + ", " + str(PaintTime)]
            resultArray.append(partResultArray)

        # DueDate in mins from start
        bendingTime = totalBending / 9  # 3 bending machines, 20 seconds per bend
        weldingTime = totalWelding / 4  # 2 welding machines, 30 seconds per weld
        totalOrderTime = bendingTime + weldingTime + totalPainting
        jamFactor = 350
        dueDate = int(totalOrderTime) + int(
            random.random() * jamFactor) + 15  # 15 minutes buffer, choose jamFactor according to number of parts and average processing time

        for x in resultArray:
            file.write(x[0] + ", " + str(dueDate) + "\n")
    file.close()
    print("Fertig!")


#Import Method to use Data Generated Files
def import_from_txt():
    jobs = []
    path = r"OrdersGenerated.txt"
    orders = open(path, "r")
    orders = orders.readlines()
    orders = orders[1:]
    for i in range(len(orders)):
        orders[i] = orders[i].split(', ')
        actual_order = orders[i]
        new_job = tuple((int(actual_order[0]), int(actual_order[1]), int(actual_order[2]), int(actual_order[3]),
                         int(actual_order[4]), int(actual_order[5])))
        jobs.append(new_job)
    return jobs


#Method to calculate the maximum time needed
def max_time(jobs, bend_length, weld_length, paint_length):
    a = 0
    b = 0
    c = 0
    for i in jobs:
        actual_time = i[2]
        if a < b and a < c:
            a += actual_time
        elif b < a and b < c:
            b += actual_time
        else:
            c += actual_time
    max_bend = max(a, b, c) * bend_length

    a = 0
    b = 0
    for i in jobs:
        actual_time = i[3]
        if a < b:
            a += actual_time
        else:
            b += actual_time
    max_weld = max(a, b) * weld_length

    c = 0
    for i in jobs:
        c += i[4]
    max_paint = c * paint_length

    return max_bend + max_weld + max_paint


#Method to get the number of Combinations (Complexity)
def ops(jobs, bend, weld, paint, bend_length, weld_length, paint_length, t_step):
    m_t_steps = max_time(jobs, bend_length, weld_length, paint_length)
    operations = []
    for x in jobs:
        if x[2] > 0:
            punish = x[2] * bend_length
            if x[3] > 0:
                punish += x[3] * weld_length
            if x[4] > 0:
                punish += x[4] * paint_length
            for m in bend:
                t = 0
                while t <= m_t_steps - punish:
                    operations.append(tuple((x[0], x[1], x[2], m, t)))
                    t += t_step

        if x[3] > 0:
            punish = x[3] * weld_length
            if x[4] > 0:
                punish += x[4] * paint_length
            for m in weld:
                t = 0
                if x[2] > 0:
                    t += x[2] * bend_length
                while t <= m_t_steps - punish:
                    operations.append(tuple((x[0], x[1], x[3], m, t)))
                    t += t_step

        if x[4] > 0:
            punish = x[4] * paint_length
            for m in paint:
                t = 0
                if x[2] > 0:
                    t += x[2] * bend_length
                if x[3] > 0:
                    t += x[3] * weld_length
                while t <= m_t_steps - punish:
                    operations.append(tuple((x[0], x[1], x[4], m, t)))
                    t += t_step
    return operations


#Method to convert tuples
def convert(operations, ord1, part1, op1, mach1, t1):
    return operations.index(tuple((ord1, part1, op1, mach1, t1)))

#Method to fill the QUBO with indexes
def fill_qubo_with_indexes(qubo, operations, ord1, part1, op1, mach1, t1, ord2, part2, op2, mach2, t2, value):
    index_a = convert(operations, ord1, part1, op1, mach1, t1)
    index_b = convert(operations, ord2, part2, op2, mach2, t2)
    if index_a > index_b:
        index_a, index_b = index_b, index_a
    qubo[index_a][index_b] += value


#First Constraint: Operation has to start once and only once
def h00_constraint(QUBO, operations, bend, weld, paint, alpha):
    for tuple1 in operations:
        for tuple2 in operations:
            if tuple1[0] == tuple2[0] and tuple1[1] == tuple2[1]:

                if tuple1[3] <= max(bend) and tuple2[3] <= max(bend):
                    if tuple1[3] == tuple2[3] and tuple1[4] == tuple2[4]:
                        fill_qubo_with_indexes(QUBO, operations, *tuple1, *tuple2, -alpha)
                    else:
                        fill_qubo_with_indexes(QUBO, operations, *tuple1, *tuple2, 2 * alpha)
                elif tuple1[3] >= min(weld) and tuple1[3] <= max(weld) and tuple2[3] >= min(weld) and tuple2[3] <= max(
                        weld):

                    if tuple1[3] == tuple2[3] and tuple1[4] == tuple2[4]:
                        fill_qubo_with_indexes(QUBO, operations,  *tuple1, *tuple2, -alpha)
                    else:
                        fill_qubo_with_indexes(QUBO, operations,  *tuple1, *tuple2, 2 * alpha)

                elif tuple1[3] >= min(paint) and tuple2[3] >= min(paint):
                    if tuple1[3] == tuple2[3] and tuple1[4] == tuple2[4]:
                        fill_qubo_with_indexes(QUBO, operations,  *tuple1, *tuple2, -alpha)
                    else:
                        fill_qubo_with_indexes(QUBO, operations,  *tuple1, *tuple2, 2 * alpha)
    return QUBO



# H0: Mehrmaliges Abarbeiten der selben Operation eines Bauteils eines Jobs bestrafen
def h0_constraint(QUBO, operations, bend, weld, paint, alpha):
    for tupel1 in operations:
        for tupel2 in operations:
            if (tupel1[0] == tupel2[0]) and (tupel1[1] == tupel2[1]): #gleiches Bauteil
                if tupel1[3] < min(weld) and tupel2[3] < min(weld): #gleiche op-Art check
                    if tupel1[3] != tupel2[3] or tupel1[4] != tupel2[4]:
                        fill_qubo_with_indexes(QUBO, operations, *tupel1, *tupel2, 2*alpha)
                    else:
                        fill_qubo_with_indexes(QUBO, operations, *tupel1, *tupel2, -alpha)
                elif tupel1[3] > max(bend) and tupel2[3] > max(bend) and tupel1[3] < min(paint) and tupel2[3] < min(paint):
                    if tupel1[3] != tupel2[3] or tupel1[4] != tupel2[4]: #gleiche op-Art check
                        fill_qubo_with_indexes(QUBO, operations, *tupel1, *tupel2, 2*alpha)
                    else:
                        fill_qubo_with_indexes(QUBO, operations, *tupel1, *tupel2, -alpha)
                elif tupel1[3] > max(weld) and tupel2[3] > max(weld) and tupel1[3] <= max(paint) and tupel2[3] <= max(paint): #gleiche op-Art check
                    if tupel1[3] != tupel2[3] or tupel1[4] != tupel2[4]:
                        fill_qubo_with_indexes(QUBO, operations, *tupel1, *tupel2, 2*alpha)
                    else:
                        fill_qubo_with_indexes(QUBO, operations, *tupel1, *tupel2, -alpha)
    return QUBO



def h0_alt_constraint(QUBO, operations, jobs, bend, weld, paint, bend_length, weld_length, paint_length,
                  m_t_steps, t_step, alpha):
    for x in jobs:
        if x[2] > 0:
            punish = x[2] * bend_length
            if x[3] > 0:
                punish += x[3] * weld_length
            if x[4] > 0:
                punish += x[4] * paint_length
            for m in bend:
                t = 0
                while t <= m_t_steps - punish:
                    u = t
                    while u <= m_t_steps - punish:
                        if t != u:
                            fill_qubo_with_indexes(QUBO, operations, x[0], x[1], x[2], m, t, x[0], x[1], x[2], m, u, 2 * alpha)
                        else:
                            fill_qubo_with_indexes(QUBO, operations, x[0], x[1], x[2], m, t, x[0], x[1], x[2], m, u, -alpha)
                        u += t_step
                    t += t_step

        if x[3] > 0:
            punish = x[3] * weld_length
            if x[4] > 0:
                punish += x[4] * paint_length
            for m in weld:
                t = 0
                if x[2] > 0:
                    t += x[2] * bend_length
                while t <= m_t_steps - punish:
                    u = t
                    while u <= m_t_steps - punish:
                        if t != u:
                            fill_qubo_with_indexes(QUBO, operations,  x[0], x[1], x[3], m, t, x[0], x[1], x[3], m, u, 2 * alpha)
                        else:
                            fill_qubo_with_indexes(QUBO, operations,  x[0], x[1], x[3], m, t, x[0], x[1], x[3], m, u, -alpha)
                        u += t_step
                    t += t_step

        if x[4] > 0:
            punish = x[4] * paint_length
            for m in paint:
                t = 0
                if x[2] > 0:
                    t += x[2] * bend_length
                if x[3] > 0:
                    t += x[3] * weld_length
                while t <= m_t_steps - punish:
                    u = t
                    while u <= m_t_steps - punish:
                        if t != u:
                            fill_qubo_with_indexes(QUBO, operations,  x[0], x[1], x[4], m, t, x[0], x[1], x[4], m, u, 2 * alpha)
                        else:
                            fill_qubo_with_indexes(QUBO, operations,  x[0], x[1], x[4], m, t, x[0], x[1], x[4], m, u, -alpha)
                        u += t_step
                    t += t_step
    return QUBO

#Second constraint: Precendence of operations
def h1_constraint(QUBO, operations, bend, weld, paint, bend_length, weld_length, beta):
    for tupel1 in operations:
        if tupel1[3] < min(paint):
            if tupel1[3] < min(weld):
                dom = bend_length * tupel1[2]
            else:
                dom = weld_length * tupel1[2]
            for tupel2 in operations:
                if (tupel1[0] == tupel2[0]) and (tupel1[1] == tupel2[1]):
                    if (tupel1[3] <= max(bend) and tupel2[3] > max(bend) and (tupel1[4] + dom) > tupel2[4] or
                            tupel1[3] > max(bend) and tupel1[3] < min(paint) and tupel2[3] >= min(paint)
                            and (tupel1[4] + dom) >
                            tupel2[4]):
                        fill_qubo_with_indexes(QUBO, operations,  *tupel1, *tupel2, beta)
    return QUBO


#Third constraint: each machine can at every Timestep only conduct one operation
def h2_constraint(QUBO, operations, weld, paint, bend_length, weld_length, paint_length, gamma):
    for tupel1 in operations:
        if tupel1[3] < min(weld):
            dom = bend_length * tupel1[2]
        elif tupel1[3] < min(paint):
            dom = weld_length * tupel1[2]
        else:
            dom = paint_length * tupel1[2]
        for tupel2 in operations:
            if ((tupel1[0] != tupel2[0] or tupel1[1] != tupel2[1]) and tupel1[3] == tupel2[3] and tupel2[4] >= tupel1[
                4] and tupel2[4] < tupel1[4] + dom):
                fill_qubo_with_indexes(QUBO, operations,  *tupel1, *tupel2, gamma)
    return QUBO

#Cost Function: for each additional timestep over the deadline, the cost gets higher
def h3_constraint(QUBO, jobs, operations, weld, paint, bend_length, weld_length, paint_length, delta):
    c = 0
    while c < len(jobs):
        t1 = 0
        while t1 < len(operations):
            if jobs[c][0] == operations[t1][0]:
                tail = 0
                if operations[t1][3] < min(weld):  # op is bend
                    dom = bend_length * operations[t1][2]
                    if jobs[c][3] > 0:  # has weld op
                        tail += jobs[c][3] * weld_length
                    if jobs[c][4] > 0:  # has paint op
                        tail += jobs[c][4] * paint_length
                elif operations[t1][3] < min(paint):  # op is weld
                    dom = weld_length * operations[t1][2]
                    if jobs[c][4] > 0:  # has paint op
                        tail += jobs[c][4] * paint_length
                else:
                    dom = paint_length * operations[t1][2]
                if operations[t1][4] + dom + tail > jobs[c][5] * paint_length:
                    factor = operations[t1][4] + dom + tail - jobs[c][5] * paint_length
                    fill_qubo_with_indexes(QUBO, operations,  *operations[t1], *operations[t1], delta*factor)
                # else:
                # fill_qubo_with_indexes(QUBO, operations,  *operations[t1], *operations[t1], -delta)
            t1 += 1
        c += 1
    return QUBO


#transform the QUBO from numpy to dictionairy
def qubo_to_dictionary(qubo, operations):
    qubo_dictionary = {}
    x1 = 0
    while x1 < len(operations):
        x2 = x1
        while x2 < len(operations):
            qubo_dictionary[(x1, x2)] = qubo[x1][x2]
            x2 += 1
        x1 += 1

    return qubo_dictionary


#make heatmap of QUBO
def get_qubo_heatmap(qubo, operations, output):
    line_width_qubo = 1/len(operations)
    df = pd.DataFrame(qubo, columns=operations, index=operations)
    sns.set_style("white")
    mask = np.tril(np.zeros_like(df)).astype(np.bool)
    mask[np.tril_indices_from(mask)] = True

    # Keep diagonal elements
    mask[np.diag_indices_from(mask)] = False

    # Set up the matplotlib figure
    f, ax = plt.subplots(figsize=(14, 12))

    # Generate a custom diverging colormap in Trumpf Color 0033BA
    color_map = sns.diverging_palette(255, 200, sep=10, as_cmap=True)

    # Draw the heatmap with the mask and correct aspect ratio

    sns_plot = sns.heatmap(df, mask=mask, cmap=color_map, center=0,
                           square=True,
                            linewidths=line_width_qubo,
                           # cbar_kws={"shrink": .5}
                           )
    # save to file
    fig = sns_plot.get_figure()
    output += ".png"
    fig.savefig(output)

    

#Method to get results from QBsolv
def get_results(result, operations, number):
    result_n = [result.samples()[number][x] for x in result.samples()[number]]
    schedule = []
    for i in range(len(result_n)):
        if result_n[i] == 1:
            schedule.append(operations[i])
    return schedule
##Number as Input to iterate through the results if wanted


#Method to help following method
def create_time(row, bend_length, weld_length, paint_length):
    if row['Machine'] == 0 or row['Machine'] == 1 or row['Machine'] == 2:
        return row['OperationSteps'] * bend_length
    elif row['Machine'] == 3 or row['Machine'] == 4:
        return row['OperationSteps'] * weld_length
    elif row['Machine'] == 5:
        return row['OperationSteps'] * paint_length
    else:
        return row['OperationSteps']


#Method to make a DataFrame from our results
def make_result_df(schedule, jobs, bend_length, weld_length, paint_length):
    df = pd.DataFrame(jobs, columns=["OrderNo", "PartNo", "BendLines", "WeldLines", "PaintMins", "DueDate"])
    df.reset_index(inplace=True)
    df = df.rename(columns={'index': 'Job'})
    df['DueDate'] = df['DueDate']*6 #DueDate ist in Minuten, der Rest in 10sec Steps
    df_schedule = pd.DataFrame(schedule)
    df_schedule.columns = ["OrderNo", "PartNo", "OperationSteps", "Machine", "StartTime"]
    df_schedule['TotalTime'] = df_schedule.apply(lambda row: create_time(row, bend_length, weld_length, paint_length), axis=1)
    df_schedule['FinishTime'] = df_schedule['TotalTime'] + df_schedule['StartTime']
    df_final = pd.merge(df_schedule, df, on=['OrderNo', 'PartNo'])
    df_final = df_final.drop(columns=['BendLines', 'WeldLines', 'PaintMins'])
    return df_final


#Visualize the results as Gantt Chart
def get_qubo_ganttchart(df_schedule):
    fig = px.timeline(df_schedule, x_start="StartTime", x_end="FinishTime", y="Machine",
                      color="Job",
                      text="DueDate",
                      title="Job Shop Schedule [Timeline in 10sec Steps]", color_continuous_scale=px.colors.sequential.Teal)
    fig.update_yaxes(autorange="reversed")
    fig.update_layout({
        'plot_bgcolor': 'rgba(0, 0, 0, 0)',
        'paper_bgcolor': 'rgba(0, 0, 0, 0)',
        })
    fig.layout.xaxis.type = 'linear'
    fig.data[0].x = df_schedule.TotalTime.tolist()
    return fig

# Get number of tasks
def number_of_tasks(jobs):
    count = 0
    for x in jobs:
        if x[2] > 0:
            count = count + 1
        if x[3] > 0:
            count = count + 1
        if x[4] > 0:
            count = count + 1
    return count


# Get Time of the machine
def time_of_machine(machine, paint_length, bend_length, weld_length):
    time = paint_length;
    if (machine == 0):
        time = bend_length
    if (machine == 1):
        time = bend_length
    if (machine == 2):
        time = bend_length
    if (machine == 3):
        time = weld_length
    if (machine == 4):
        time = weld_length
    return time


#Verification for h0
def h0_constraint_is_fulfilled(operation_results, jobs):
    nbr_jobs = number_of_tasks(jobs)
    N = len(operation_results)
    if nbr_jobs != N:
        return False
    return True

#Verification for h1
def h1_constraint_is_fulfilled(operation_results, paint_length, bend_length, weld_length):
    for j in operation_results:
        for i in operation_results:
            if (j[0]==i[0] and j[1] == i[1]):
                #print('Compare j = ' + str(j) + ' und i = ' + str(i))
                if (j[3] < i[3]):
                    if (j[4] + j[2]*time_of_machine(j[3], paint_length, bend_length, weld_length) > i[4]):
                        return False
    return True

#Verification for h2
def h2_constraint_is_fulfilled(operation_results, paint_length, bend_length, weld_length):
    for j in operation_results:
        for i in operation_results:
            if (j != i):
                if (j[3] == i[3]):
                    if (j[4] <= i[4]):
                        #print('Compare j = ' + str(j) + ' und i = ' + str(i))
                        if (j[4] + j[2]*time_of_machine(j[3], paint_length, bend_length, weld_length) > i[4]):
                            return False
    return True

#Verification for h3
def h3_constraint_is_fulfilled(operation_results, jobs, paint_length, bend_length, weld_length):
    for j in operation_results:
        for job in jobs:
            #print('Compare j = ' + str(j) + ' und job = ' + str(job))
            if (j[0]==job[0] and j[1]==job[1]):
                if(j[4]+j[2]*time_of_machine(j[3], paint_length, bend_length, weld_length) > job[5]*6):
                    return False;
    return True

#Transform QUBO from numpy to Dictionary without Zeros
def qubo_to_dictionary_ohne_null(qubo, operations):
    qubo_dictionary = {}
    x1 = 0
    while x1 < len(operations):
        x2 = x1
        while x2 < len(operations):
            if (qubo[x1][x2] != 0):
                qubo_dictionary[(x1, x2)] = qubo[x1][x2]
            x2 += 1
        x1 += 1

    return qubo_dictionary


#Find the Chain Strength following D Waves Problem Solving Handbook
def find_chstr(QUBO):
    chstr = QUBO.max() # Implementation parameter on the DWave QPU
    return chstr;

#Return Infos for the JobSet
def job_info(jobs, bend_length, weld_length, paint_length, t_step_in_sec, bend, weld, paint, t_step):
    # OrderNo, PartNo, BendingLines, WeldingPoints, PaintTime, DueDate

    m_t_steps = max_time(jobs, bend_length, weld_length, paint_length)

    m_time = m_t_steps * t_step_in_sec

    print('The maximal maketime for the given operations is: ' + str(m_time) + ' second(s).\nWhich is equal to: ' + str(
        m_t_steps) + ' time steps.\n\n')

    operations = ops(jobs, bend, weld, paint, bend_length, weld_length, paint_length, t_step)

    print('Anzahl an Kombinationen: ' + str(len(operations)) + '\n')

    df = pd.DataFrame(jobs, columns=['order', 'part', 'bend', 'weld', 'paint', 'deadline'])
    df["bend"] = df["bend"] * 2
    df["weld"] = df["weld"] * 3
    df["paint"] = df["paint"] * 6
    df["deadline"] = df["deadline"] * 6
    print(df)
    return operations

#Simple approach to get QUBO
def get_QUBO(jobs, operations, alpha, beta, gamma, delta, bend_length, weld_length, paint_length, bend, weld, paint):
    QUBO = np.zeros((len(operations), len(operations)))
    QUBO = h0_constraint(QUBO, operations, bend, weld, paint, alpha)
    QUBO = h1_constraint(QUBO, operations, bend, weld, paint, bend_length, weld_length, beta)
    QUBO = h2_constraint(QUBO, operations, weld, paint, bend_length, weld_length, paint_length, gamma)
    QUBO = h3_constraint(QUBO, jobs, operations, weld, paint, bend_length, weld_length, paint_length, delta)
    return QUBO


#QBSolve
def on_QBsolve(qubo_dictionary):
    result = QBSolv().sample_qubo(qubo_dictionary)
    return result

#Run on UQO Fujitsu
def on_Fujitsu(config, qubo_dictionary, solver):
    #solver = "DAU"  # CPU or DAU
    number_runs = 1
    parameters = {
    # default parameters:
        "number_iterations": 500,           # total number of iterations per run
        "temperature_start": 1000.0,        # start temperature as float value
        "temperature_end": 1.0,             # end temperature as float value or None
        "temperature_mode": 0,              # 0, 1, or 2 to define the cooling curve
                                            # 0: reduce temperature by factor (1-temperature_decay) every temperature_interval steps
                                            # 1: reduce temperature by factor (1-temperature_decay*temperature) every temperature_interval steps
                                            # 2: reduce temperature by factor (1-temperature_decay*temperature^2) every temperature_interval steps
        "temperature_decay": 0.001,         # decay per step if temperature_end is None
        "temperature_interval": 100,        # number of iterations keeping temperature constant
        "offset_increase_rate": 0.0,        # increase of dynamic offset when no bit selected, set to 0.0 to switch off dynamic energy feature
        "solution_mode": "COMPLETE",        # COMPLETE returns all runs best configuration, QUICK returns overall best configuration only
        "optimization_method": "annealing",  # annealing or parallel tempering are supported methods
        "number_replicas": 26,              # number of replicas for parallel tempering mode
        "annealer_version": 2,              # Digital Annealer version
        "guidance_config": {},              # list of variable values that to be set for DA as a starting values of variables for annealing process for each run
        "auto_tuning": 0,                    # EXPERIMENTAL! options of automatic tuning the QUBO
        "bit_precision": 16,                 # bit precision (DAU version 2)
        "connection_mode": "CMODE_ASYNC"    # Mode can be CMODE_ASYNC (default) or CMODE_SYNC
    }
        
    answer = Problem.Qubo(config, qubo_dictionary).with_platform("fujitsu").with_solver(solver).with_params(**parameters).solve(number_runs)
    return answer

#Dwave Simulator
def on_DWave_simulator(QUBO, numr):
    bqm = dimod.BinaryQuadraticModel.from_numpy_matrix(QUBO)
    sampler = neal.SimulatedAnnealingSampler()
    # reding num_reads responses from the sampler
    sampleset = sampler.sample(bqm, chain_strength=find_chstr(QUBO), num_reads=numr)
    return sampleset


#Dwave Hybrid
def on_DWave_Hybrid(QUBO):
    bqm = dimod.BinaryQuadraticModel.from_numpy_matrix(QUBO)
    sampler = LeapHybridSampler()
    # reding num_reads responses from the sampler
    sampleset = sampler.sample(bqm)
    return sampleset

#echtes HW
def on_DWave(QUBO, numr): 
    bqm = dimod.BinaryQuadraticModel.from_numpy_matrix(QUBO)
    sampler = EmbeddingComposite(DWaveSampler())
       
    # reding num_reads responses from the sampler
    sampleset = sampler.sample(bqm, chain_strength=find_chstr(QUBO),num_reads=numr)
    return sampleset

#to make a schedule from sample munr from sampleset
def make_schedule_from_sample(jobs, operations, sampleset, numr, bend_length, weld_length, paint_length):
    schedule = get_results(sampleset, operations, numr)
    df_schedule = make_result_df(schedule, jobs, bend_length, weld_length, paint_length)
    return df_schedule

# Get schedule from fujitsu
def get_fujitsu_schedule_from_sample(answer, jobs, operations, sampleset, numr, bend_length, weld_length, paint_length):
    result = list(answer.solutions)[numr]
    print(result)
    schedule = []
    for i in range(len(result)):
        if result[i] == 1:
            schedule.append(operations[i])
    df_schedule = make_schedule_from_sample(jobs, operations, sampleset, numr, bend_length, weld_length, paint_length)
    return df_schedule

#Check the Constraints
def check_constraints(schedule, jobs, paint_length, bend_length, weld_length):
    print('H_0 erfüllt: ' + str(h0_constraint_is_fulfilled(schedule, jobs)))
    print('H_1 erfüllt: ' + str(h1_constraint_is_fulfilled(schedule, paint_length, bend_length, weld_length)))
    print('H_2 erfüllt: ' + str(h2_constraint_is_fulfilled(schedule, paint_length, bend_length, weld_length)))
    print('H_3 erfüllt: ' + str(h3_constraint_is_fulfilled(schedule, jobs, paint_length, bend_length, weld_length)))


# Analyze the D Wave results and append to List
def analyze(sampleset, label, data):
    print("Good solutions are {}% of samples.".format(len(sampleset.lowest(atol=0.5).record.energy)/5))
    print("Best Known solutions are {}% of samples.".format(len(sampleset.lowest(atol=0).record.energy)/5))
    print("Lowest energy found: {}".format(list(dict.fromkeys(sampleset.lowest(atol=0).record.energy))))
    print("Average energy is {:.2f} with standard deviation {:.2f}".format(sampleset.record.energy.mean(), sampleset.record.energy.std()))
    Label = label
    GKS = len(sampleset.lowest(atol=0.5).record.energy)/5
    BKS = len(sampleset.lowest(atol=0).record.energy)/5
    LE = list(dict.fromkeys(sampleset.lowest(atol=0).record.energy))[0]
    AVG = sampleset.record.energy.mean()
    STD = sampleset.record.energy.std()
    newlist = [Label, BKS, GKS, LE, AVG, STD]
    data.append(newlist)

## Make plot for Anneal Schedule
def make_anneal_plot(reverse_schedule):
    plt.figure(1, figsize=(3, 3))
    plt.plot(*np.array(reverse_schedule).T)
    plt.title("Reverse Anneal Schedule")
    plt.xlabel("Time [us]")
    plt.ylabel("Annealing Parameter s")
    plt.ylim([0.0,1.0])
    plt.show()

## Construct Reverse anneal Schedule
def make_reverse_anneal_schedule(s_target=0.0, hold_time=10.0, ramp_back_slope=0.2, ramp_up_time=0.0201,
                                 ramp_up_slope=None):
    """Build annealing waveform pattern for reverse anneal feature.
    Waveform starts and ends at s=1.0, descending to a constant value
    s_target in between, following a linear ramp.
      s_target:   s-parameter to descend to (between 0 and 1)
      hold_time:  amount of time (in us) to spend at s_target (must be >= 2.0us)
      ramp_slope: slope of transition region, in units 1/us
    """
    # validate parameters
    if s_target < 0.0 or s_target > 1.0:
        raise ValueError("s_target must be between 0 and 1")
    if hold_time < 0.0:
        raise ValueError("hold_time must be >= 0")
    if ramp_back_slope > 0.2:
        raise ValueError("ramp_back_slope must be <= 0.2")
    if ramp_back_slope <= 0.0:
        raise ValueError("ramp_back_slope must be > 0")

    ramp_time = (1.0 - s_target) / ramp_back_slope

    initial_s = 1.0
    pattern = [[0.0, initial_s]]

    # don't add new points if s_target == 1.0
    if s_target < 1.0:
        pattern.append([round(ramp_time, 4), round(s_target, 4)])
        if hold_time != 0:
            pattern.append([round(ramp_time+hold_time, 4), round(s_target, 4)])

    # add last point
    if ramp_up_slope is not None:
        ramp_up_time = (1.0-s_target)/ramp_up_slope
        pattern.append([round(ramp_time + hold_time + ramp_up_time, 4), round(1.0, 4)])
    else:
        pattern.append([round(ramp_time + hold_time + ramp_up_time, 4), round(1.0, 4)])

    return pattern

def qubo_to_nx_graph(qubo):
    graph = nx.Graph()
    
    for coupler, energy in qubo.items():
        if coupler[0] != coupler[1]:
            graph.add_edge(coupler[0], coupler[1], weight=energy)
    
    return graph

def on_QBsolv_Hybrid(isQuantum, QUBO, subqubo_size, problem_label ):
    if isQuantum:
                     sampler = EmbeddingComposite(DWaveSampler())
    else:
                     sampler = neal.SimulatedAnnealingSampler()
    #print(sampler)
    response = QBSolv().sample_qubo(QUBO, solver=sampler, solver_limit=subqubo_size, label=problem_label)
    return response


# Analyze the D Wave results and append to List
def analyze_Hybrid(sampleset, label, data):
    samples_count = 0
    for datum in sampleset.data():
        samples_count = samples_count + datum.num_occurrences
        
    GS_count = 0
    for GS in sampleset.lowest(atol=0.5).record:
        GS_count = GS_count + GS.num_occurrences
    
    
    BKS_count = 0
    for BKS in sampleset.lowest(atol=0).record:
        BKS_count = BKS_count + BKS.num_occurrences
    print("{} Samples done.".format(GS_count*100/samples_count))   
    print("Good solutions are {}% of samples.".format(GS_count*100/samples_count))
    print("Best Known solutions are {}% of samples.".format(BKS_count*100/samples_count))
    print("Lowest energy found: {}".format(list(dict.fromkeys(sampleset.lowest(atol=0).record.energy))))
    print("Average energy is {:.2f} with standard deviation {:.2f}".format(sampleset.record.energy.mean(), sampleset.record.energy.std()))
    Label = label
    GKS = GS_count*100/samples_count
    BKS = BKS_count*100/samples_count
    LE = list(dict.fromkeys(sampleset.lowest(atol=0).record.energy))[0]
    AVG = sampleset.record.energy.mean()
    STD = sampleset.record.energy.std()
    newlist = [Label, BKS, GKS, LE, AVG, STD]
    data.append(newlist)
    return data
    

    
def analyse_HS(run_nmr, sampleset, datei):
    t = PrettyTable(["Run", "Min_Energy", "GS %", "BKS %"])
    samples_count = 0
    for datum in sampleset.data():
        samples_count = samples_count + datum.num_occurrences
        
    GS_count = 0
    for GS in sampleset.lowest(atol=0.5).record:
        GS_count = GS_count + GS.num_occurrences
    
    
    BKS_count = 0
    for BKS in sampleset.lowest(atol=0).record:
        BKS_count = BKS_count + BKS.num_occurrences
        
    min_energy = list(dict.fromkeys(sampleset.lowest(atol=0).record.energy))
    run = run_nmr
    t.add_row([run, min_energy, GS_count*100/samples_count, BKS_count*100/samples_count])
    with open(datei, 'a') as w:
        w.write(str(t))
    print(t)
    return t    
    
def countGS(sampleset):
    samples_count = 0
    for datum in sampleset.data():
        samples_count = samples_count + datum.num_occurrences
    GS_count = 0
    for GS in sampleset.lowest(atol=0.5).record:
        GS_count = GS_count + GS.num_occurrences
    return GS_count*100/samples_count
    
    
def countBKS(sampleset):
    samples_count = 0
    for datum in sampleset.data():
        samples_count = samples_count + datum.num_occurrences    
    BKS_count = 0
    for BKS in sampleset.lowest(atol=0).record:
        BKS_count = BKS_count + BKS.num_occurrences
    return BKS_count*100/samples_count   


def print_solutions(sampleset):
    t = PrettyTable(["Answer-Sample", "Energy", "Num-Occurrences"])

    for datum in sampleset.data():
        t.add_row([datum.sample, datum.energy, datum.num_occurrences])
    print(t)
    return t


def countBKS_DAU(sampleset):
    samples = countSamples_DAU(sampleset)
    min_energy = sampleset.energies[0]
    count_BKS = 0
    for index, solution in enumerate(sampleset.solutions):
        if (sampleset.energies[index] == min_energy):
            count_BKS = count_BKS + sampleset.num_occurrences[index]
    return count_BKS


def countSamples_DAU(sampleset):
    samples_count = 0
    for index, solution in enumerate(sampleset.solutions):
        samples_count = samples_count + sampleset.num_occurrences[index]
    return samples_count


def analyse_DAU(run_nmr, sampleset, datei, atol, mult):
    t = PrettyTable(["Run", "Min_Energy", "GS %", "BKS %"])
    min_energy = sampleset.energies[0]
    run = run_nmr
    bks = countBKS_DAU(sampleset)
    gs = countGS_DAU(sampleset, atol, mult)
    t.add_row([run, min_energy, gs, bks])
    with open(datei, 'a') as w:
        w.write(str(t))
    print(t)
    return t

def countGS_DAU(sampleset, atol, mult):
    samples = countSamples_DAU(sampleset)
    min_energy = sampleset.energies[0]
    count_GS = 0
    for index, solution in enumerate(sampleset.solutions):
        if abs(sampleset.energies[index] - min_energy) <= atol*mult :
            count_GS = count_GS + sampleset.num_occurrences[index]
    return count_GS
    
    

def energy_distribution(sampleset):
    all_energies = []
    for index, solution in enumerate(sampleset.solutions):
        for i in range(sampleset.num_occurrences[index]):
            all_energies.append(sampleset.energies[index])
    energies_withoutDub = list(dict.fromkeys(all_energies))
    
    x = energies_withoutDub
    y = []
    
    for energy in energies_withoutDub:
        y.append(all_energies.count(energy))
    fig1 = px.scatter(x=x, y=y)
    fig1.add_trace(go.Bar(x=x, y=y, name="Energy Distribution"))
    return fig1
