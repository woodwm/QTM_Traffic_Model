#! /usr/bin/python
from __future__ import division
from gurobipy import *
import pprint
import json as json
import sys
import argparse
import time as clock_time
import os, platform, subprocess, re
import copy
import random
import zipfile
import zlib
import numpy
import scipy.interpolate as interp
import math
#import plot_model as pl
#import matplotlib.pyplot as plt


DEBUG = False

def debug(msg=""):
    """
    Display debug messege
    :param msg: The message to display
    :return:
    """
    if DEBUG:
        print 'DEBUG: ',msg

def get_processor_name():
    if platform.system() == "Windows":
        family = platform.processor()
        name = subprocess.check_output(["wmic","cpu","get", "name"]).strip().split("\n")[1]
        return ' '.join([name, family])
    elif platform.system() == "Darwin":
        os.environ['PATH'] = os.environ['PATH'] + os.pathsep + '/usr/sbin'
        command ="sysctl -n machdep.cpu.brand_string"
        return subprocess.check_output(command, shell=True).strip()
    elif platform.system() == "Linux":
        command = "cat /proc/cpuinfo"
        all_info = subprocess.check_output(command, shell=True).strip()
        for line in all_info.split("\n"):
            if "model name" in line:
                return re.sub( ".*model name.*:", "", line,1)
    return ""

def t_in_index(t_prop,t,t_prev):
    index = interp.interp1d(t_prev + t, range(-len(t_prev),len(t)))
    t_in = [x - t_prop for x in t]
    return [int(i) if i >= 0 else -int(math.ceil(-i)) for i in index(t_in)]

# def min2_constr(m,g,a,b,z1):
#     # add min contraints to model m such that g == min(a,b)
#     #z1 = m.addVar(vtype=GRB.BINARY,name='z1_%d @ %d' % (i,n))
#     #m.update()
#     constr = []
#     L = -1e9
#     U = 1e9
#     constr.append(m.addConstr(0 <= b - g))
#     constr.append(m.addConstr(b - g <= U * (1 - z1)))
#     constr.append(m.addConstr(0 <= a - g))
#     constr.append(m.addConstr(a - g <= U * z1))
#     constr.append(m.addConstr(L * (1 - z1) <= a - b))
#     constr.append(m.addConstr(a - b <= U * z1))
#     return constr

def min2_constr(m,g,a,b,z1):
    # add min contraints to model m such that g == min(a,b)
    #z1 = m.addVar(vtype=GRB.BINARY,name='z1_%d @ %d' % (i,n))
    #m.update()
    #L = -1e9
    M = 1e9
    constr = []
    constr.append(m.addConstr(a - M * z1 <= g))
    constr.append(m.addConstr(g <= a))
    constr.append(m.addConstr(b - M * (1 - z1) <= g))
    constr.append(m.addConstr(g <= b))
    return constr

def min2_test(a,b):
    m = Model("min2_test")
    m.reset()
    g = m.addVar(lb=-GRB.INFINITY)
    z1 = m.addVar(vtype=GRB.BINARY)
    m.update()
    #a = 3
    #b = 1
    min2_constr(m, g, a, b, z1)
    m.setParam(GRB.Param.LogToConsole, 0)
    m.optimize()
    # assert g.x == min(a,b), 'g != min(a,b), g=%f, a=%f, b=%f' % (g.x,a,b)
    numpy.testing.assert_almost_equal([g.x], [min(a,b)],
                                      decimal=9)
    # print '=================='
    # print 'MIN2_TEST:'
    # print 'a:',a
    # print 'b:',b
    # print 'min(a,b):',min(a,b)
    # print 'g=',g.x

    # m.reset()
    # g = m.addVar()
    # z1 = m.addVar(vtype=GRB.BINARY)
    # m.update()
    # a = 2
    # b = 3
    # min2_constr(m, g, a, b, z1)
    # m.setParam(GRB.Param.LogToConsole, 0)
    # m.optimize()
    # print '=================='
    # print 'MIN2_TEST 2:'
    # print 'a:', a
    # print 'b:', b
    # print 'min(a,b):', min(a, b)
    # print 'g=', g.x
    # print '=================='


# def min3_constr(m,g,a,b,c,z1,z2,phi):
#     # add min contraints to model m such that g == min(a,b,c)
#     #z1 = m.addVar(vtype=GRB.BINARY,name='z1_%d @ %d' % (i,n))
#     #z2 = m.addVar(vtype=GRB.BINARY,name='z2_%d @ %d' % (i,n))
#     #phi = m.addVar(name='phi_%d @ %d' % (i,n))
#     #m.update()
#     L = -1e6
#     U = 1e6
#     constr = []
#     constr.append(m.addConstr(0 <= b - phi))
#     constr.append(m.addConstr(b - phi <= U * (1 - z1)))
#     constr.append(m.addConstr(0 <= a - phi))
#     constr.append(m.addConstr(a - phi <= U * z1))
#     constr.append(m.addConstr(L * (1 - z1) <= a - b))
#     constr.append(m.addConstr(a - b <= U * z1))
#
#     constr.append(m.addConstr(0 <= c - g))
#     constr.append(m.addConstr(c - g <= U * (1 - z2)))
#     constr.append(m.addConstr(0 <= phi - g))
#     constr.append(m.addConstr(phi - g <= U * z2))
#     constr.append(m.addConstr(L * (1 - z2) <= phi - c))
#     constr.append(m.addConstr(phi - c <= U * z2))
#     return constr

def min3_constr(m,g,a,b,c,z1,z2,phi):
    # add min contraints to model m such that g == min(a,b,c)
    #z1 = m.addVar(vtype=GRB.BINARY,name='z1_%d @ %d' % (i,n))
    #z2 = m.addVar(vtype=GRB.BINARY,name='z2_%d @ %d' % (i,n))
    #phi = m.addVar(name='phi_%d @ %d' % (i,n))
    #m.update()

    M = 1e6
    constr = []
    constr.append(m.addConstr(b - M * z1 <= phi))
    constr.append(m.addConstr(phi <= b))
    constr.append(m.addConstr(c - M * (1 - z1) <= phi))
    constr.append(m.addConstr(phi <= c))
    constr.append(m.addConstr(a - M * z2 <= g))
    constr.append(m.addConstr(g <= a))
    constr.append(m.addConstr(phi - M * (1 - z2) <= g))
    constr.append(m.addConstr(g <= phi))
    return constr


def read_flows(flow_data):
    flow = {}
    out_fmax = {}

    for f_ij in flow_data.keys():
        i = int(f_ij.split('_')[0])
        j = int(f_ij.split('_')[1])
        if i not in flow:
            flow[i] = {}
        if j not in flow[i]:
            flow[i][j] = flow_data[f_ij]

    for i in flow.keys():
        max_out = 0
        for j in flow[i].keys():
            max_out = max(max_out,flow[i][j]['F_MAX'])
        out_fmax[i] = max_out
        out_fmax[j] = max_out

    return flow,out_fmax

def convert_model_to_ctm(data,dt):
    print 'old Nodes',data['Nodes']
    new_queues = []
    new_flows = {}
    new_nodes = data['Nodes']
    new_q_in = {}
    new_q_out = {}
    flows, out_fmax = read_flows(data['Flows'])
    for i,q in enumerate(data['Queues']):
        n = int(q['Q_DELAY'] / float(dt))
        if n < 1: n = 1
        n0 = q['edge'][0]
        n1 = q['edge'][1]
        rx0 = data['Nodes'][n0]['p'][0]
        ry0 = data['Nodes'][n0]['p'][1]
        rx1 = data['Nodes'][n1]['p'][0]
        ry1 = data['Nodes'][n1]['p'][1]
        rx_f = interp.interp1d([0,1],[rx0,rx1])
        ry_f = interp.interp1d([0,1],[ry0,ry1])
        #n_in = len(new_nodes)
        print 'n',n
        #print rx_f(0)
        q_nodes = [n0]
        if n > 1:
            for k in range(1, n):
                t = k / (n)
                #print t,type(float(rx_f(t)))
                q_nodes.append(len(new_nodes))
                new_nodes.append({"p": [float(rx_f(t)), float(ry_f(t))]})
        q_nodes.append(n1)
        if n > 1:

            n_out = len(new_nodes) - 1
            f_max = out_fmax[i]
            q_in = len(new_queues)

            new_queues.append({ "Q_DELAY": dt, "edge": [n0, q_nodes[1]], "Q_IN": q["Q_IN"],
                                "Q_OUT": 0,  "Q_P": None, "Q_MAX": q["Q_MAX"] / n,
                                "q0": q["q0"] / n, "q0_in": q["q0_in"], "q0_out": 0 })

            if "weights" in q:
                new_queues[-1]["weights"] = q["weights"]

            if n > 2:
                for k in range(1,n-1):

                    new_queues.append({ "Q_DELAY": dt, "Q_IN": 0, "edge": [q_nodes[k], q_nodes[k + 1]],
                                    "Q_OUT": 0,  "Q_P": None, "Q_MAX": q["Q_MAX"] / n,
                                    "q0": q["q0"] / n, "q0_in": 0, "q0_out": 0 })

            q_out = len(new_queues)
            new_queues.append({ "Q_DELAY": dt, "Q_IN": 0, "edge": [q_nodes[-2], n1],
                                "Q_OUT": q["Q_OUT"],  "Q_P": q["Q_P"], "Q_MAX": q["Q_MAX"] / n,
                                "q0": q["q0"] / n, "q0_in": q["q0_in"], "q0_out": q["q0_out"] })

            for k in range(q_in, q_out):
                new_flows["%d_%d" % (k, k + 1)] = { "F_MAX": float(f_max), "f0": 0 }

            new_q_in[i] = q_in
            new_q_out[i] = q_out
            print i,new_q_in[i],new_q_out[i]

        else:
            new_q_in[i] = len(new_queues)
            new_q_out[i] = len(new_queues)
            new_queues.append(q)
            #q['edge'] = [n_in, n_in + 1]


    for f_ij in data['Flows'].keys():
        i = int(f_ij.split('_')[0])
        j = int(f_ij.split('_')[1])
        new_f_i_j = "%d_%d" % (new_q_out[i], new_q_in[j])
        new_flows[new_f_i_j] = data['Flows'][f_ij]
        if "F_y" in new_flows[new_f_i_j]:
            F_ij = new_flows[new_f_i_j]['F_Y'].split('_')
            new_flows[new_f_i_j]['F_Y'] = ['%d_%d' % (F_ij[0],F_ij[1])]

    if 'Base_Network' not in data:
        data['Base_Network'] = {}
        data['Base_Network']['Nodes'] = data['Nodes']
        data['Base_Network']['Queues'] = data['Queues']
        data['Base_Network']['Flows'] = data['Flows']
    data['Nodes'] = new_nodes
    data['Queues'] = new_queues
    data['Flows'] = new_flows
    #print 'Nodes',data['Nodes']
    #print 'Queues',data['Queues']
    #print 'Flows',data['Flows']

def milp_solver(data,t0,t1,n_samples,dt0=None,dt1=None,DT_file=False,DT_vari=None,minor_frame=0,major_frame=0,blend_frame=None,nthreads=0,fixed_plan=None,
           timelimit=0,accuracy=0,verbose=False,label=None,step=None,run=None,obj='NEW',alpha_obj=1.0,beta_obj=0.001,gamma_obj=0.0001,
           DT_offset=0,seed=0,tune=False,tune_file='',param=None, in_weight=1.0,mip_start=None,refine=False,no_assertion_fail=False, lost_time=0,
                solver_model='QTM',no_warning=False,buffer_input=False,exact=False):
    start_time = clock_time.time()
    try:

        t_period = (t1-t0)
        print 't0=',t0,'t1=',t1,'t_period=',t_period
        t=t0
        DT=[]
        DT_factor=1
        if 'DT_factor' in data:
            DT_factor=data['DT_factor']
        print 'DT_vari',DT_vari
        print 'DT_factor',DT_factor
        if DT_vari != None:
            if DT_offset>0:
                DT.append(DT_offset)
            if 'len' in DT_vari[0]:
                for DT_step in DT_vari:
                    DT_len = DT_step['len']
                    n=0
                    while n< DT_len  and t<=t1:
                        DT.append(DT_step['DT'])
                        t+=DT[-1]
                        n+=1
            elif len(DT_vari)==1:
                DT = DT_vari[0]['DT_vec']
            elif len(DT_vari)==2:
                while t<t0+minor_frame:
                    DT.append(DT_vari[0]['DT']*DT_factor)
                    t+=DT[-1]
                blend_start_i = len(DT)
                if blend_frame != None:
                    while t <= t0+minor_frame+blend_frame:
                        alpha = (t-minor_frame-t0)/(blend_frame)
                        DT.append(DT_vari[0]['DT']*DT_factor*(1-alpha) + DT_vari[1]['DT']*DT_factor*alpha)
                        t+=DT[-1]
                else:
                    DT += DT_vari[0]['DT_vec']
                    t = t0 + sum(DT)
                blend_stop_i = len(DT)
                print 'blend_rate=',blend_frame / (blend_stop_i - blend_start_i),'len',blend_frame,'start',blend_start_i,'stop',blend_stop_i
                while t <= t0+major_frame:
                    DT.append(DT_vari[1]['DT']*DT_factor)
                    t+=DT[-1]

            else:
                for DT_step in DT_vari:
                    DT_start = t0 + DT_step['start']*t_period
                    DT_stop = t0 + DT_step['stop']*t_period

                    while t>= DT_start and t<DT_stop and t<=t1:

                        DT.append(DT_step['DT']*DT_factor)
                        t+=DT[-1]
            #DT.append(DT[-1])
            #DT.append(DT[-1])
            N=len(DT)
            n_samples = N #-2
            print DT

        elif "DT" in data and DT_file == True:
            DT = data["DT"]
            N = len(DT)
            n_samples = len(DT)

        else:
            N=n_samples+2
            if DT_offset>0:
                if DT_offset < (t_period)/n_samples:
                    DT = [DT_offset] + [(t_period)/n_samples for n in range(N-2)] + [(t_period)/n_samples - DT_offset]
                else:
                    n_offset = int(DT_offset / ((t_period)/n_samples))
                    residual = DT_offset - (n_offset)*( (t_period)/n_samples )
                    if residual > 0:
                        DT = [DT_offset] + [(t_period)/n_samples for n in range(N-1-n_offset)] + [(t_period)/n_samples - residual]
                    else:
                        DT = [DT_offset] + [(t_period)/n_samples for n in range(N-n_offset)]
                        N = 1 + N-n_offset
            elif dt0 != None and dt1 != None:
                DT = [dt0]
                t = t0 + dt0
                while t<=t1:
                    alpha = (t-t0)/(t1 - t0)
                    DT.append(dt0*(1-alpha) + dt1*alpha)
                    t += DT[-1]
                DT.append(dt1)
                DT.append(dt1)
                N = len(DT)
                n_samples = N-2
            else:
                DT = [(t_period)/n_samples for n in range(N)]
        print 'DT_offset=',DT_offset
        if len(DT) < 10:
            print 'DT=',DT
        else:
            print 'DT=',DT[0:10],'...'
        DT_s={}
        for dt in DT:
            if str(dt) not in DT_s:
                DT_s[str(dt)]=1
            else:
                DT_s[str(dt)]+=1
        if len(DT_s) > 1:
            print 'DT = ',DT_s
        else:
            print 'DT = ',DT[0]
        print 'N  = ',N
        t=t0
        time = []
        for _dt in DT:
            time.append(t)
            t+=_dt
        time_full = time + [t]

        if refine is not False:
            out=data['Out']
            if run != None:
                out = out['Run'][run]
            if step != None and step > 0:
                out = out['Step'][step-1]
            prev_mp_dt = out['DT']
            prev_mp_t = out['t']
            prev_mp_t += [prev_mp_t[-1] + prev_mp_dt[-1]]
            print prev_mp_t
            print time
            new_t_sample = [0 for n in time]
            for i in range(len(data['Lights'])):
                for j in range(len(data['Lights'][i]['P_MAX'])):
                    prev_p = out['p_{%d,%d}' % (i,j)]
                    for k in range(1,len(prev_p)):
                        p_state = prev_p[k]

                        if prev_p[k] != prev_p[k-1]:
                            k_t = int(time[k] / DT[0])
                            new_t_sample[(k_t * 2) - 2] = 1
                            new_t_sample[(k_t * 2) - 1] = 1
                            new_t_sample[(k_t * 2)    ] = 1



                    #plt.figure(figsize=(20,5))

                    #plt.plot(prev_mp_t[0:-1],prev_p,'-x')

                    #plt.plot(time,new_p,'-',marker='.')
                    #plt.plot(time,new_t,'-',marker='o')
                    #plt.ylim(-0.1,1.1)
                    #plt.show();

            dt_step = DT[0]
            dt = dt_step
            new_DT=[]
            for state in new_t_sample:
                if state == 1:
                    new_DT.append(dt)
                    dt = dt_step
                else:
                    dt += dt_step
            if sum(new_DT) < time[-1]:
                new_DT.append(time[-1] - sum(new_DT))
            print new_DT
            print sum(new_DT), '(',time[-1],')'
            #plt.plot(time,new_t_sample,'-',marker='o')
            #plt.ylim(-0.1,1.1)
            #plt.show();
            DT = new_DT
            t=t0
            time = []
            for _dt in DT:
                time.append(t)
                t+=_dt
            time_full = time + [t]
            N = len(DT)
            n_samples = N


            print prev_mp_t
            print time

        if solver_model == 'CTM' and ('Solver_model' not in data or mip_start is not None):
            convert_model_to_ctm(data,DT[0])
            data['Solver_model'] = 'CTM'

        #print 'time     =',time
        #print 'time_full=',time_full
        if 'Flow_Weights' in data:
            flow_weights = data['Flow_Weights']
            for n,t in enumerate(time):
                for f in flow_weights:

                    if n==0:
                        flow_weights[f]['wt']=[0]*N
                    if t >= flow_weights[f]['start'] and t < flow_weights[f]['end']:
                        flow_weights[f]['wt'][n]=flow_weights[f]['weight']
                    else:
                        flow_weights[f]['wt'][n]=0
                    if n>1:
                        if t >= flow_weights[f]['start'] and time[n-1] < flow_weights[f]['start']:
                            flow_alpha = (flow_weights[f]['start'] - time[n-1]) / (t - time[n-1])
                            flow_weights[f]['wt'][n] *= flow_alpha
                        if t >= flow_weights[f]['end'] and time[n-1] < flow_weights[f]['end']:
                            flow_alpha = (flow_weights[f]['end'] - time[n-1]) / (t - time[n-1])
                            flow_weights[f]['wt'][n-1] *= flow_alpha


        else:
            flow_weights=None

        # Define Constants
        T_MAX = time[N-1] # T_MAX = time[N-1]+1

        if lost_time > 0:
            for i,light in enumerate(data['Lights']):
                P_MIN = []
                P_MAX = []
                p0 = []
                c0 = []
                d0 = []
                c_min_extra = 0
                c_max_extra = 0

                for j,p in enumerate(light['P_MAX']):
                    P_MIN.append(light['P_MIN'][j]) #  - lost_time)
                    P_MIN.append(lost_time)
                    P_MAX.append(light['P_MAX'][j]) #  - lost_time)
                    P_MAX.append(lost_time)
                    p0.append(light['p0'][j])
                    p0.append(0)
                    c0.append(light['c0'][j])
                    c0.append(0)
                    d0.append(light['d0'][j])
                    d0.append(lost_time)
                    c_min_extra += lost_time
                    c_max_extra += lost_time
                    # light['P_MIN'].insert(j+1,lost_time)
                    # light['p0'].insert(j+1,0)
                    # light['c0'].insert(j+1,0)
                    # light['d0'].insert(j+1,0)
                light['P_MIN'] = P_MIN
                light['P_MAX'] = P_MAX
                light['p0'] = p0
                light['c0'] = c0
                light['d0'] = d0
                #light['C_MIN'] += c_min_extra
                #light['C_MAX'] += c_max_extra
                print light
            for i,q in enumerate(data['Queues']):
                if q['Q_P'] is not None:
                    print i,'from:',q['Q_P'],'to:',
                    for j in range(1,len(q['Q_P'])):
                        q['Q_P'][j] = q['Q_P'][j] * 2
                    print q['Q_P']
        epsilon = 0.1

        Q = len(data['Queues'])
        L = len(data['Lights'])

        Q_IN  = [ q['Q_IN']   for q in data['Queues'] ]
        Q_in  = [ []   for q in data['Queues'] ]
        Q_OUT = [ q['Q_OUT']  for q in data['Queues'] ]
        if flow_weights != None:
            Q_IN_weight = [ [0]*N for q in data['Queues'] ]
            for i,q in enumerate(data['Queues']):
                if 'weights' in q:
                    for w in q['weights']:
                        for n in range(N):
                            Q_IN_weight[i][n]+=flow_weights[w]['wt'][n]*in_weight
                            if (args.Q_IN_limit or data.get('Flow_Weight_Q_IN_limit',False)) and Q_IN_weight[i][n] > 1.0:
                                Q_IN_weight[i][n] = 1.0
                else:
                    Q_IN_weight[i]=[1]*N

        Q_p   = [ q['Q_P']    for q in data['Queues'] ]
        if buffer_input:
            Q_MAX = [ 1e9 if Q_IN[i] > 0 else q['Q_MAX'] for i,q in enumerate(data['Queues']) ]
        else:
            Q_MAX = [ q['Q_MAX']  for q in data['Queues'] ]
        Q_DELAY = [ q['Q_DELAY']  for q in data['Queues'] ]

        P_MAX = [ [ p for p in light['P_MAX']] for light in data['Lights'] ]

        P_MIN = [ [ p for p in light['P_MIN']] for light in data['Lights'] ]
        C_MAX = [ light['C_MAX'] for light in data['Lights'] ]
        C_MIN = [ light['C_MIN'] if 'C_MIN' in light.keys() else 0 for light in data['Lights'] ]
        l = [ [ p for p in light['P_MAX']] for light in data['Lights'] ]
        # "transits" : [{"id": "West-East" ,"phase": 1, "P_MAX_ext": [2,0],"offset": 10, "duration": 5, "period": 20}]
        p_transit = [ [ [False for n in range(N)] for p in light['P_MAX']] for light in data['Lights'] ]
        P_MAX_ext = [ [ [0 for n in range(N)] for p in light['P_MAX']] for light in data['Lights'] ]
        C_MAX_ext = [ [0 for n in range(N)] for light in data['Lights'] ]
        TRANSIT = False
        for i,light in enumerate(data['Lights']):
            if 'transits' in light:
                TRANSIT = True
                for transit in light['transits']:
                    if args.no_transit is None or (len(args.no_transit) > 0 and transit['id'] not in args.no_transit):
                        print 'adding transit: %s at light %d ' % (transit['id'],i)
                        j = transit['phase']
                        for n in range(N):

                            # for j in range(len(transit['P_MAX_ext'])):
                            #     if P_MAX[i][j] < transit['duration'] \
                            #             and time[n] >= transit['offset']\
                            #             and (time[n] - transit['offset'] ) % transit['period'] < transit['duration']:
                            #         P_MAX_ext[i][j][n] = transit['P_MAX_ext'][j]


                            #if P_MAX[i][j] < transit['duration'] \
                            #            and time[n] >= transit['offset']\
                            #            and (time[n] - transit['offset'] ) % transit['period'] < transit['duration']:
                            #        p_transit[i][j][n] = True
                            if time[n] >= transit['offset'] and (time[n] - transit['offset'] ) % transit['period'] < transit['duration']: # if time[n] >= transit['offset'] and
                                    p_transit[i][j][n] = True
                        print ''.join(['1' if x is True else '_' for x in p_transit[i][j]])
                    else:
                        print 'removing transit: %s at light %d' % (transit['id'],i)


        #print 'P_MAX_ext=', P_MAX_ext



        # initial conditions
        q0 =    [ q['q0']     for q in data['Queues'] ]
        q0_in = [ q['q0_in'] + q['Q_IN'] * DT[0] if q['Q_IN'] * DT[0] < q['Q_MAX'] else q['Q_MAX'] for q in data['Queues'] ]
        q0_out =[ q['q0_out'] for q in data['Queues'] ]
        q0_stop = [ 0 for q in data['Queues'] ]
        p0 = [ [ p for p in light['p0']] for light in data['Lights'] ]
        d0 = [ [ d for d in light['d0']] for light in data['Lights'] ]
        f0 = [[[0 for n in range(N)] for j in range(Q)] for i in range(Q)]
        for i in range(Q):
            for j in range(Q):
                f_ij = '%d_%d' % (i,j)
                if f_ij in data['Flows'] and i != j:
                    f0[i][j] = data['Flows'][f_ij]['f0']
        # initial conditions (using previous results if found in file)
        init_prev_file = False
        if fixed_plan == None and 'Out' in data and step > 0 and mip_start is None:
            init_prev_file = True
            out=data['Out']
            if run != None:
                out = out['Run'][run]
            if step != None and step > 0:
                out = out['Step'][step-1]
            m0 = 0
            for n,tn in enumerate(out['t']):
                if tn == t0:
                    m0 = n
                    break
                if tn > t0:
                    m0 = n-1
                    break
            m1=m0+1
            if m1>= len(out['t']): m1=m0
            dt_ratio = DT[0] / out['DT'][m0-1]
            print 'DT[0]',DT[0],'out["DT"][m0]',out['DT'][m0]
            td = t0-out['t'][m0]
            alpha = 1-(td / out['DT'][m0]) #(out['t'][m1] - out['t'][m0]))
            print 'alpha',alpha,'m0',m0,'m1',m1,'dt_ratio',dt_ratio
            #print 'q_{5,in} =',out['q_{5,in}']
            #print 'sum(q_{5,in}) =',sum(out['q_{5,in}'])
            #print 'q_{5,stop} =',out['q_{5,stop}']
            #print 'Q_MAX[5] =',Q_MAX[5]
            q0 = [ alpha * out['q_%d' % i][m0] + (1-alpha) * out['q_%d' % i][m1]     for i,q in enumerate(data['Queues']) ]
            q0_stop =  [ alpha * out['q_{%d,stop}' % i][m0] + (1-alpha) * out['q_{%d,stop}' % i][m1]     for i,q in enumerate(data['Queues']) ]
            q0_in =  [ (alpha * out['q_{%d,in}' % i][m0] + (1-alpha) * out['q_{%d,in}' % i][m1]) * dt_ratio  for i,q in enumerate(data['Queues']) ]
            q_in_prev = [ out['q_{%d,in}' % i] for i,q in enumerate(data['Queues']) ]; # print 'q_in_prev',q_in_prev
            q_stop_prev = [ out['q_{%d,stop}' % i] for i,q in enumerate(data['Queues']) ]
            t_prev = out['t']
            DT_prev = out['DT']
            q0_out = [ (alpha * out['q_{%d,out}' % i][m0] + (1-alpha) * out['q_{%d,out}' % i][m1]) * dt_ratio for i,q in enumerate(data['Queues']) ]
            p0 = [ [ out['p_{%d,%d}' %(i,j)][m0] for j,p in enumerate(light['p0'])] for i,light in enumerate(data['Lights']) ]
            d0 = [ [ out['d_{%d,%d}' %(i,j)][m0] for j,d in enumerate(light['p0'])] for i,light in enumerate(data['Lights']) ]

            #q0 =    [ out['q_%d' % i][m0] for i,q in enumerate(data['Queues']) ] #[ alpha * out['q_%d' % i][m0] + (1-alpha) * out['q_%d' % i][m1]     for i,q in enumerate(data['Queues']) ]
            #q0_stop = [ out['q_{%d,stop}' % i][m0] for i,q in enumerate(data['Queues']) ] #[ alpha * out['q_{%d,stop}' % i][m0] + (1-alpha) * out['q_{%d,stop}' % i][m1]     for i,q in enumerate(data['Queues']) ]
            #q0_in = [ out['q_{%d,in}' % i][m0] for i,q in enumerate(data['Queues']) ] #[ (alpha * out['q_{%d,in}' % i][m0] + (1-alpha) * out['q_{%d,in}' % i][m1]) * dt_ratio  for i,q in enumerate(data['Queues']) ]
            #q_in_prev = [ out['q_{%d,in}' % i] for i,q in enumerate(data['Queues']) ]
            #q_stop_prev = [ out['q_{%d,stop}' % i] for i,q in enumerate(data['Queues']) ]
            #t_prev = out['t']
            #DT_prev = out['DT']
            #q0_out = [ out['q_{%d,out}' % i][m0] for i,q in enumerate(data['Queues']) ] #[ (alpha * out['q_{%d,out}' % i][m0] + (1-alpha) * out['q_{%d,out}' % i][m1]) * dt_ratio for i,q in enumerate(data['Queues']) ]
            #p0 = [ [ out['p_{%d,%d}' %(i,j)][m0] for j,p in enumerate(light['p0'])] for i,light in enumerate(data['Lights']) ]
            #d0 = [ [ out['d_{%d,%d}' %(i,j)][m0] for j,d in enumerate(light['p0'])] for i,light in enumerate(data['Lights']) ] #[ [ (alpha * out['d_{%d,%d}' %(i,j)][m0] + (1-alpha) * out['d_{%d,%d}' %(i,j)][m1]) for j,d in enumerate(light['p0'])] for i,light in enumerate(data['Lights']) ]

            for i in range(Q):
                for j in range(Q):
                    f_ij = '%d_%d' % (i,j)
                    if f_ij in data['Flows'] and i != j:
                        f0[i][j] = (alpha * out['f_{%d,%d}' % (i,j)][m0] + (1-alpha) * out['f_{%d,%d}' % (i,j)][m1]) * dt_ratio
                        #f0[i][j] = out['f_{%d,%d}' % (i,j)][m0] #(alpha * out['f_{%d,%d}' % (i,j)][m0] + (1-alpha) * out['f_{%d,%d}' % (i,j)][m1]) * dt_ratio
                    else:
                        f0[i][j] = 0

        else:
            t_prev = [t0-max(Q_DELAY),t0]
            DT_prev= [t_prev[1]-t_prev[0],DT[0]]
            q_in_prev = [[0,0] for i,q in enumerate(data['Queues']) ]
        #print 't_prev:',t_prev
        #print 'DT_prev:',DT_prev
      #  t_inv = [t_in_index(Q_DELAY[i],time_full,t_prev[0:-1]) for i in range(Q)]
        #for i in range(Q):
        #    print 't_inv q_%d = %s' % (i,t_inv[i])
        # Create a new model
        m = Model("flow")

        # feasrelax contraint and variable lists and penalties
        relax_constr=[]
        relax_vars=[]
        lbpen=[]
        ubpen=[]
        rhspen=[]

        min_relax_constr=[]
        min_relax_vars=[]
        min_lbpen=[]
        min_ubpen=[]
        min_rhspen=[]

        fij_relax_constr=[]
        fij_relax_vars=[]
        fij_lbpen=[]
        fij_ubpen=[]
        fij_rhspen=[]

        # Create variables
        p = [[[m.addVar(vtype=GRB.BINARY, name="p%d_%d_%d" % (i,j,n))  for n in range(N)] for j in range(len(l[i]))] for i in range(L)]
        d = [[[m.addVar(name="d%d_%d @ %d" % (i,j,n))  for n in range(N)] for j in range(len(l[i]))] for i in range(L)]
        q = [[m.addVar(lb=0, name="q%d @ %d" % (i,n)) for n in range(N)] for i in range(Q)]
        q_in = [[m.addVar(lb=0, name="q%d_in @ %d" % (i,n)) for n in range(N)] for i in range(Q)]
        q_stop = [[m.addVar(lb=0, name="q%d_stop @ %d" % (i,n)) for n in range(N)] for i in range(Q)]
        qm_in = [[m.addVar(lb=-1, name="qm%d_in @ %d" % (i,n)) for n in range(N)] for i in range(Q)]
        qw_in = [[m.addVar(lb=-1, name="qw%d_in @ %d" % (i,n)) for n in range(N)] for i in range(Q)]
        q_out = [[m.addVar(lb=0, name="q%d_out @ %d" % (i,n)) for n in range(N)] for i in range(Q)]
        d_1 = [[m.addVar(lb=0, name="d_(1)_%d @ %d" % (i, n)) for n in range(N)] for i in range(Q)]
        d_2 = [[m.addVar(lb=0, name="d_(2)_%d @ %d" % (i,n)) for n in range(N)] for i in range(Q)]
        fij = [[m.addVar(lb=0, name="fij_%d_in @ %d" % (i,n)) for n in range(N)] for i in range(Q)]
        fxy = [[m.addVar(lb=0, name="fxy_%d_in @ %d" % (i,n)) for n in range(N)] for i in range(Q)]


        in_q = [[m.addVar(lb=0, name="in_q%d @ %d" % (i,n)) for n in range(N)] for i in range(Q)]
        out_q = [[m.addVar(lb=0, ub=Q_OUT[i], name="out_q%d @ %d" % (i,n)) for n in range(N)] for i in range(Q)]
        zout = [[m.addVar(vtype=GRB.BINARY, name="zout_%d @ %d" % (i,n)) for n in range(N)] for i in range(Q)]
        total_stops = m.addVar(lb=0, name = "stops")

        f = [[[None for n in range(N)] for j in range(Q)] for i in range(Q)]
        z1 = [[[None for n in range(N)] for j in range(Q)] for i in range(Q)]
        z2 = [[[None for n in range(N)] for j in range(Q)] for i in range(Q)]
        phi = [[[None for n in range(N)] for j in range(Q)] for i in range(Q)]
        g = [[[None for n in range(N)] for j in range(Q)] for i in range(Q)]
        f_set = [[] for n in range(N)]
        for i in range(Q):
            for j in range(Q):
                for n in range(N):
                    f_ij = '%d_%d' % (i,j)
                    if f_ij in data['Flows']:
                        f[i][j][n] = m.addVar(lb=0, ub=data['Flows'][f_ij]['F_MAX'], name="f_%d,%d @ %d" % (i,j,n))
                        z1[i][j][n] = m.addVar(vtype=GRB.BINARY, name="z1_%d,%d @ %d" % (i,j,n))
                        z2[i][j][n] = m.addVar(vtype=GRB.BINARY, name="z2_%d,%d @ %d" % (i,j,n))
                        phi[i][j][n] = m.addVar(name="phi_%d,%d @ %d" % (i,j,n))
                        g[i][j][n] = m.addVar(name="g_%d,%d @ %d" % (i,j,n))
                        f_set[n].append(f[i][j][n])
                        min_relax_vars.append(phi[i][j][n])
                        min_ubpen.append(1)
                        min_lbpen.append(1)
                        fij_relax_vars.append(f[i][j][n])
                        fij_ubpen.append(1)
                        fij_lbpen.append(1)

        for i in range(Q):
            total_Pr_ij = 0
            num_flows = 0
            for j in range(Q):
                f_ij = '%d_%d' % (i,j)
                if f_ij in data['Flows']:
                    if "Pr" in data['Flows'][f_ij]:
                        Pr_ij = data['Flows'][f_ij]["Pr"]
                    else:
                        Pr_ij = 1.0
                    total_Pr_ij += Pr_ij
                    num_flows += 2
            if num_flows > 0 and (total_Pr_ij - 1.0 > 1e-6 or total_Pr_ij - 1.0 < -1e-6):
                print "WARNING: sum(Pr) from q_%d  = %s" % (i,total_Pr_ij)
            if num_flows > 0:
                numpy.testing.assert_array_almost_equal([total_Pr_ij],[1.0])

        dominant_flows = set()
        for f_ij in data['Flows'].keys():
            i = int(f_ij.split('_')[0])
            j = int(f_ij.split('_')[1])
            if "F_Y" in data['Flows'][f_ij]:
                for f_xy in data['Flows'][f_ij]["F_Y"]:
                    x = int(f_xy.split('_')[0])
                    y = int(f_xy.split('_')[1])
                    dominant_flows.add((x,y))
        # print 'Dominant Flows: %s' % dominant_flows

        total_travel_time = m.addVar(lb=-GRB.INFINITY, name="total_travel_time")
        c_fixed = [m.addVar( name="c_fixed_%d" % i) for i in range(L)]
        dp_fixed = [[m.addVar( name="d_fixed_%d_%d" % (i,j)) for j in range(len(l[i]))] for i in range(L)]
        c_on = [[m.addVar(lb=-GRB.INFINITY, name="fixed_cycle_time_on_%d_%d" % (i,n)) for n in range(N)] for i in range(L)]
        tct = [[m.addVar(lb=-GRB.INFINITY, name="fixed_cycle_time_on_%d_%d" % (i,n)) for n in range(N)] for i in range(L)]

        # Integrate new variables
        m.update()

        if mip_start is not None and step > 0:
            #if mip_start == 'step' or mip_start == 'final':
            out=data['Out']
            if run != None:
                out = out['Run'][run]
            if step != None and step > 0:
                out = out['Step'][step-1]
            #else:
            #    out = mip_start
            prev_mp_dt = out['DT']
            prev_mp_t = out['t']
            prev_mp_t += [prev_mp_t[-1] + prev_mp_dt[-1]]
            for i in range(L):
                for j in range(len(l[i])):
                    prev_p = out['p_{%d,%d}' % (i,j)]
                    prev_p_f = interp.interp1d(prev_mp_t,prev_p + [prev_p[-1]],kind='zero')
                    new_p = prev_p_f(time)
                    ##plt.figure(figsize=(20,5))

                    ##plt.plot(prev_mp_t[0:-1],prev_p,'-x')

                    ##plt.plot(time,new_p,'-',marker='.')
                    #plt.plot(time,new_t,'-',marker='o')
                    ##plt.ylim(-0.1,1.1)
                    ##plt.show();
                    for n in range(N):
                        p[i][j][n].start = int(new_p[n] + 0.25)

        if fixed_plan is not None:
            p_fixed_plan = [[[ 0 for n in range(N) ] for j in range(len(l[i]))] for i in range(L)]
            d_fixed_plan = [[[ fixed_plan['d_{%d,%d}' % (i,j)][0] if n==0 else 0 for n in range(N) ] for j in range(len(l[i]))] for i in range(L)]
            t_fixed_plan = numpy.linspace(fixed_plan['t'][0],fixed_plan['t'][-1],len(fixed_plan['t']))
            #print 'len(p_fixed) =',len(p_fixed[0][0])
            #print 'len(fixed_plan[p_{0,0}]) =',len(fixed_plan['p_{%d,%d}' % (0,0)])
            #print 't_fixed_plan:',t_fixed_plan[0],t_fixed_plan[-1],t_fixed_plan
            #print 'time:',time[0],time[n_samples],time
            for i in range(L):
                for j in range(len(l[i])):
                    time_x_samples = int((t_fixed_plan[-1] - t_fixed_plan[0]) / DT[0])
                    time_x = numpy.linspace(t_fixed_plan[0],t_fixed_plan[-1],time_x_samples)
                    print len(t_fixed_plan),len(fixed_plan['p_{%d,%d}' % (i,j)])
                    p_fixed_f = interp.interp1d(t_fixed_plan,fixed_plan['p_{%d,%d}' % (i,j)],kind='zero')
                    print 't_fixed_plan:',t_fixed_plan[0],t_fixed_plan[-1]
                    print 'time:', time[0], time[-1]
                    print 'n_samples',n_samples
                    print 'time[n_samples-1]:',time[n_samples-1]
                    print 'time_x[-1]',time_x[-1]
                    print 'time_x_samples', time_x_samples
                    p_fixed_plan[i][j][0:time_x_samples] = p_fixed_f(time_x[0:time_x_samples])

                    for n in range(1,len(p_fixed_plan[i][j])):
                        if p_fixed_plan[i][j][n] == 1 and p_fixed_plan[i][j][n-1] == 0:
                            d_fixed_plan[i][j][n]=0
                        elif p_fixed_plan[i][j][n] == 0 and p_fixed_plan[i][j][n-1] == 0:
                            d_fixed_plan[i][j][n]=d_fixed_plan[i][j][n-1]
                        else:
                            d_fixed_plan[i][j][n]=d_fixed_plan[i][j][n-1] + DT[n-1]*p_fixed_plan[i][j][n-1]


            # for i in range(L):
            #     for j in range(len(l[i])):
            #         k=0
            #         for n in range(n_samples):
            #             #if i==0 and j==0 and k+1<len(t_fixed):
            #             #    print time[n], '>=', t_fixed[k+1],time[n] >= t_fixed[k+1],
            #             if k+1<len(t_fixed_plan) and time[n] >= t_fixed_plan[k+1]-1e-6:
            #                 k+=1
            #             p_fixed_plan[i][j][n]=fixed_plan['p_{%d,%d}' % (i,j)][k]
            #             #if i==0 and j==0:
            #             #    print 't_fixed[k]=%f'%t_fixed[k],'time[n]=%f'%time[n],'n=',n,'k=',k,'p_{%d,%d}=' % (i,j),p_fixed[i][j][n],
            #             #if n<n_samples and k+1 < len(t_fixed) and time[n]>t_fixed[k+1]:
            #
            #             if n>0:
            #                 if p_fixed_plan[i][j][n] == 1 and p_fixed_plan[i][j][n-1] == 0:
            #                     d_fixed_plan[i][j][n]=0
            #                 elif p_fixed_plan[i][j][n] == 0 and p_fixed_plan[i][j][n-1] == 0:
            #                     d_fixed_plan[i][j][n]=d_fixed_plan[i][j][n-1]
            #                 else:
            #                     d_fixed_plan[i][j][n]=d_fixed_plan[i][j][n-1] + DT[n-1]*p_fixed_plan[i][j][n-1]
            #             #if i==0 and j==0:
            #             #    print 'd=',d_fixed[i][j][n]

        #if mip_start is not None:
        #    if
        #    for i in range(L):
        #        for j in range(len(l[i])):

        print 'Objective: %s alpha=%s beta=%s gamma=%s' % (obj,alpha_obj,beta_obj,gamma_obj)
        delay = quicksum([quicksum([time[n] * q_out[i][n] if Q_OUT[i]>0 else 0 for n in range(N)]) for i in range(Q) ])
        vehicle_holding = quicksum([quicksum([time[n] * q_out[i][n] if Q_OUT[i]==0 else 0 for n in range(N)]) for i in range(Q) ])
        in_flow = quicksum([quicksum([(T_MAX-time[n] + 1) * in_q[i][n] if Q_IN[i]>0 else 0 for n in range(N)]) for i in range(Q) ])
        out_flow = quicksum([quicksum([(T_MAX-time[n] + 1) * out_q[i][n] if Q_OUT[i]>0 else 0 for n in range(N)]) for i in range(Q) ])
        #m.setObjective(delay - beta*in_flow - beta*out_flow, GRB.MINIMIZE)
        #m.setObjective(delay + beta* vehicle_holding, GRB.MINIMIZE)

        sum_in =  quicksum([quicksum([time[n] * q_in[i][n] if Q_IN[i]>0 else 0 for n in range(N-1)]) for i in range(Q) ])
        sum_out = quicksum([quicksum([time[n] * q_out[i][n] if Q_OUT[i]>0 else 0 for n in range(N-1)]) for i in range(Q) ])
        m.addConstr(total_travel_time == sum_out - sum_in)
        m.addConstr(total_stops == 0.5 * quicksum([quicksum([d_2[i][n] + d_1[i][n] for i in range(Q)]) for n in range(0, N)]))
        #m.addConstr( sum_out == sum_in)
        if obj == 'MAX_OUT':
            out_flow = quicksum([ quicksum([ (T_MAX-time[n] + 1) * out_q[i][n] * DT[n] for n in range(0,N)]) for i in range(Q) ])
            in_flow = quicksum( [ quicksum([ (T_MAX-time[n] + 1) * in_q[i][n] * DT[n] for i in range(Q) ]) for n in range(0,N)])
            #flow = quicksum( [ quicksum([ (T_MAX-time[n] + 1) * f[j][i][n] if '%d_%d' % (j,i) in data['Flows'] and i != j else 0 for j in range(Q)]) for n in range(0,N)])
            m.setObjective(alpha_obj * out_flow  + beta_obj * in_flow, GRB.MAXIMIZE)
        elif obj == 'MIN_TT':
            out_flow = quicksum([ quicksum([ (T_MAX-time[n] + 1) * out_q[i][n] * DT[n] for n in range(0,N)]) for i in range(Q) ])
            in_flow = quicksum( [ quicksum([ (T_MAX-time[n] + 1) * in_q[i][n] * DT[n] for i in range(Q) ]) for n in range(0,N)])
            #flow = quicksum( [ quicksum([ (T_MAX-time[n] + 1) * f[j][i][n] if '%d_%d' % (j,i) in data['Flows'] and i != j else 0 for j in range(Q)]) for n in range(0,N)])
            m.setObjective(alpha_obj * out_flow  + beta_obj * in_flow, GRB.MAXIMIZE)
        elif obj == 'MAX_OUT2':
            flow_set = []
            for i in range(Q):
                if Q_OUT[i] == 0: flow_set.append(i)
            print 'Internal queue out flows:',flow_set
            out_flow = quicksum([ quicksum([ (T_MAX - time[n] + 1) * q_out[i][n] for n in range(N)]) if Q_OUT[i]  > 0 else 0 for i in range(Q) ])
            flow     = quicksum([ quicksum([ (T_MAX - time[n] + 1) * q_out[i][n] for n in range(N)]) if Q_OUT[i] == 0 else 0 for i in range(Q) ])
            in_flow  = quicksum([ quicksum([ (T_MAX - time[n] + 1) * in_q[i][n]  for n in range(N)])                         for i in range(Q) ])

            m.setObjective(alpha_obj * (out_flow  + in_flow) - (1.0 - alpha_obj) * total_stops + beta_obj * flow, GRB.MAXIMIZE)
        elif obj == 'MAX_OUT3':
            flows = []
            flow_pairs = []
            for f_ij in data['Flows'].keys():
                i = int(f_ij.split('_')[0])
                j = int(f_ij.split('_')[1])
                flows.append(f[i][j])
                flow_pairs.append((i,j))
            out_flow = quicksum([ quicksum([ (T_MAX - time[n] + 1) * out_q[i][n] for n in range(N)])  for i in range(Q) ])
            in_flow  = quicksum([ quicksum([ (T_MAX - time[n] + 1) * in_q[i][n]  for n in range(N)])  for i in range(Q) ])
            flow     = quicksum([ quicksum([ (T_MAX - time[n] + 1) * f_ij[n] for f_ij in flows ]) for n in range(N) ])
            #print 'out_flows:',[ i if Q_OUT[i]  > 0 else 0 for i in range(Q) ]
            #print 'in_flows:',[ i for i in range(Q) ]
            print 'flows:',flow_pairs
            m.setObjective(alpha_obj * (out_flow  + in_flow) - (1.0 - alpha_obj) * total_stops + beta_obj * flow, GRB.MAXIMIZE)
        elif obj == 'MAX_OUT4':
            flows = []
            flow_pairs = []
            for f_ij in data['Flows'].keys():
                i = int(f_ij.split('_')[0])
                j = int(f_ij.split('_')[1])
                flows.append(f[i][j])
                flow_pairs.append((i,j))
            external_flow = quicksum([ quicksum([ (T_MAX - time[n] + 1) * DT[n] * (out_q[i][n] + in_q[i][n]) for n in range(N)])  for i in range(Q) ])
            internal_flow = quicksum([ quicksum([ (T_MAX - time[n] + 1) * DT[n] * f_ij[n] for f_ij in flows ]) for n in range(N) ])
            #print 'out_flows:',[ i if Q_OUT[i]  > 0 else 0 for i in range(Q) ]
            #print 'in_flows:',[ i for i in range(Q) ]
            print 'flows:',flow_pairs
            m.setObjective(alpha_obj * external_flow - (1.0 - alpha_obj) * total_stops + beta_obj * internal_flow, GRB.MAXIMIZE)
        elif obj == 'MAX_QOUT':
            flow = quicksum([ quicksum([ (T_MAX-time[n] + 1) * q_out[i][n] for n in range(N)]) if Q_OUT[i]>0 else 0 for i in range(Q) ])
            in_flow = quicksum( [ quicksum([ (T_MAX-time[n] + 1) * in_q[i][n] * DT[n-1] for i in range(Q) ]) for n in range(0,N)])
            m.setObjective(alpha_obj * flow  -  (1-alpha_obj)*total_stops + beta_obj*in_flow, GRB.MAXIMIZE)
            #m.setObjective(flow + beta*in_flow, GRB.MAXIMIZE)
        elif obj == 'MAX_ALL_QOUT':
            m.setObjective(quicksum([(T_MAX-time[n] + 1) * q_out[i][n] + beta_obj * ((T_MAX-time[n] + 1) * in_q[i][n])  for i in range(Q) for n in range(0,N)]), GRB.MAXIMIZE)
            # m.setObjective(quicksum([(T_MAX-time[n] + 1) * q_out[i][n] + 1*((T_MAX-time[n] + 1) * in_q[i][n]) for i in range(Q) for n in range(N)]), GRB.MAXIMIZE)
        elif obj == 'MAX_ALL_FLOWS':
            obj_flow_weights = []
            gamma_flow_weights = []
            for f_ij in data['Flows'].keys():
                i = int(f_ij.split('_')[0])
                j = int(f_ij.split('_')[1])
                if "F_Y" in data['Flows'][f_ij]:
                    for f_xy in data['Flows'][f_ij]["F_Y"]:
                        x = int(f_xy.split('_')[0])
                        y = int(f_xy.split('_')[1])
                        gamma_flow_weights.append((x,y,gamma_obj))
                obj_flow_weights.append((i,j,beta_obj))
            print 'Objective function flow weights: %s' % obj_flow_weights
            print 'Gamma flow weights: %s' % gamma_flow_weights
            in_flow = quicksum([quicksum([(T_MAX - time[n] + 1) * in_q[i][n] if Q_IN[i] > 0 else 0 for n in range(N)]) for i in range(Q) ])
            out_flow = quicksum([quicksum([(T_MAX - time[n] + 1) * out_q[i][n] if Q_OUT[i] > 0 else 0 for n in range(N)]) for i in range(Q) ])
            mid_flow = quicksum([(T_MAX - time[n] + 1) * f[i][j][n] for i,j,w in obj_flow_weights for n in range(0,N)])
            maj_flow = quicksum([(T_MAX - time[n] + 1) * f[i][j][n] for i,j,w in gamma_flow_weights for n in range(0,N)])
            m.setObjective(alpha_obj * out_flow + alpha_obj * in_flow + beta_obj * mid_flow + gamma_obj * maj_flow, GRB.MAXIMIZE)
            # m.setObjective(quicksum([(T_MAX-time[n] + 1) * q_out[i][n] + 1*((T_MAX-time[n] + 1) * in_q[i][n]) for i in range(Q) for n in range(N)]), GRB.MAXIMIZE)
        elif obj == 'MIN_LIN_WANG':
            obj_flows = []
            for f_ij in data['Flows'].keys():
                i = int(f_ij.split('_')[0])
                j = int(f_ij.split('_')[1])
                obj_flows.append((i,j))
            #print['%d(%d)' % (i,Q_OUT[i]) if Q_OUT[i] > 0 else '%d(_)' % i for i in range(Q) ]
            #print['%d(%d)' % (i,Q_OUT[i]) if Q_OUT[i] == 0 else '%d(_)' % i for i in range(Q) ]
            out_flow = quicksum([quicksum([(time[n]) * (q_out[i][n]) if Q_OUT[i] > 0 else 0 for n in range(N)]) for i in range(Q) ])
            flow = quicksum([quicksum([(time[n]) * (q_out[i][n]) if Q_OUT[i] == 0 else 0 for n in range(N)]) for i in range(Q) ])
            m.setObjective(alpha_obj * out_flow + beta_obj * flow, GRB.MINIMIZE)
        else:
            print 'No objective: %s' % obj
            return None

        # initial conditions at n = 0
        # for i in range(L):
        #     for j in range(len(l[i])):
        #         m.addConstr(p[i][j][0] == p0[i][j])
        #         if args.fixed_phase:
        #             #print
        #             m.addConstr(d[i][j][0] <= dp_fixed[i][j] + P_MAX[i][j] * (p0[i][j]))
        #             m.addConstr(d[i][j][0] >= dp_fixed[i][j] - P_MAX[i][j] * (p0[i][j]))
        #             m.addConstr(dp_fixed[i][j] <= P_MAX[i][j])
        #             m.addConstr(dp_fixed[i][j] >= P_MIN[i][j])
        #         else:
        #             m.addConstr(d[i][j][0] == d0[i][j])
        #         m.addConstr(c_on[i][0] == 0)
        #         m.addConstr(tct[i][0] == 0)

        for i in range(Q):
            m.addConstr(q[i][0] == q0[i])
            # if flow_weights != None:
            #     if solver_model == 'QTM':
            #         m.addConstr(in_q[i][0] == Q_IN[i]*Q_IN_weight[i][0])
            #     else:
            #         m.addConstr(in_q[i][0] == Q_IN[i]*Q_IN_weight[i][0] * DT[0])
            #     #Q_in[i].append(Q_IN[i]*Q_IN_weight[i][0])
            # else:
            #     if solver_model == 'QTM':
            #         m.addConstr(in_q[i][0] == Q_IN[i])
            #     else:
            #         m.addConstr(in_q[i][0] == Q_IN[i] * DT[0])
            #     #Q_in[i].append(Q_IN[i])
            # #print 'q0_in[%d]=' % i,q0_in[i]
            # m.addConstr(q_in[i][0] == in_q[i][0] * DT[0]) # q0_in[i]) #in_q[i][0] * DT[0] + quicksum([f[j][i][0]*DT[0] if '%d_%d' % (j,i) in data['Flows'] and i != j else 0 for j in range(Q)]))
            # m.addConstr(q_stop[i][0] == q0_stop[i])
            # m.addConstr(qm_in[i][0] == -1)
            # m.addConstr(qw_in[i][0] == -1)
            # m.addConstr(q_out[i][0] == q0_out[i])
            # for j in range(Q):
            #     f_ij = '%d_%d' % (i,j)
            #     if f_ij in data['Flows'] and i != j:
            #         m.addConstr(f[i][j][0] == f0[i][j])

        # for f_ij in data['Flows'].keys():
        #         i = int(f_ij.split('_')[0])
        #         j = int(f_ij.split('_')[1])
        #         if "F_Y" in data['Flows'][f_ij]:
        #             for f_xy in data['Flows'][f_ij]["F_Y"]:
        #                 x = int(f_xy.split('_')[0])
        #                 y = int(f_xy.split('_')[1])
        #                 m.addConstr( quicksum([ (1 + time[n]) * (1 + f[i][j][n]) for n in range(0,N)])
        #                             >=
        #                              quicksum([ (1 + time[n]) * (1 + f[x][y][n]) for n in range(0,N)]))


        cars_in =0
        cars_in_1 =0

        #print 'n\ttime\tt_m\tt_w\tm0\tw0\tDTm\tDTw\tDTw1'
        queue_print = -1

        for n in range(0,N):
            debug('==============================')
            debug('n=%d' % n)
            debug('==============================')
            for i in range(Q):

                debug( '------------------------------')
                debug( 'q=%d' % i)
                debug( '------------------------------')
                if 'In_Flow_limit' in data and flow_weights == None:
                    # if time[n-1] <= data['In_Flow_limit'] and data['In_Flow_limit'] < time[n]:
                    #     flow_alpha = (data['In_Flow_limit'] - time[n-1]) / (time[n]-time[n-1])
                    #     if i==1: print time[n-1],'flow_alpha=',flow_alpha
                    #     m.addConstr(in_q[i][n-1] <= flow_alpha*Q_IN[i])
                    #     cars_in+=flow_alpha*Q_IN[i]*DT[n-1]
                    #     Q_in[i].append(flow_alpha*Q_IN[i])
                    #     if i==1:
                    #         cars_in_1+=flow_alpha*Q_IN[i]*DT[n-1]
                    #         #print "cars_in_1 =",cars_in_1, ' @',time[n], ' alpha =',flow_alpha ,' limit =',data['In_Flow_limit'],time[n] < data['In_Flow_limit'] and data['In_Flow_limit'] < time[n+1]
                    if time[n] < data['In_Flow_limit']:
                        if solver_model == 'QTM':
                            m.addConstr(in_q[i][n] <= Q_IN[i])
                            Q_in[i].append(Q_IN[i])
                            cars_in += Q_IN[i]
                        else:
                            #print (n,i, Q_IN[i])
                            m.addConstr(in_q[i][n] == Q_IN[i] * DT[n])
                            Q_in[i].append(Q_IN[i] * DT[n])
                            cars_in += Q_IN[i]*DT[n]

                        if i==1:
                            cars_in_1+=Q_IN[i]*DT[n]
                            #print "cars_in_1 =",cars_in_1, ' @',time[n]
                    else:
                        #print (n,i, 0)
                        Q_in[i].append(0)
                        m.addConstr(in_q[i][n] == 0)

                elif flow_weights != None:
                    if solver_model == 'QTM':
                        m.addConstr(in_q[i][n] == Q_IN[i] * Q_IN_weight[i][n])
                        Q_in[i].append(Q_IN[i ] *Q_IN_weight[i][n])
                        cars_in += Q_IN[i] * Q_IN_weight[i][n]
                    else:
                        m.addConstr(in_q[i][n] == Q_IN[i]*Q_IN_weight[i][n] * DT[n])
                        Q_in[i].append(Q_IN[i] * Q_IN_weight[i][n] * DT[n])
                        cars_in += Q_IN[i] * Q_IN_weight[i][n] * DT[n]

                else:
                    if solver_model == 'QTM':
                        m.addConstr(in_q[i][n] == Q_IN[i])
                        cars_in += Q_IN[i]
                        Q_in[i].append(Q_IN[i])

                    else:
                        m.addConstr(in_q[i][n] == Q_IN[i] * DT[n])
                        cars_in += Q_IN[i] * DT[n]
                        Q_in[i].append(Q_IN[i] * DT[n])


                if solver_model == 'CTM':
                    W = 0.5

                    #m.addConstr(in_q[i][n] == Q_IN[i])
                    m.addConstr(q[i][n] <= Q_MAX[i])

                    next_cell = None
                    prev_cell = None
                    F_MAX_ij = 0
                    for j in range(Q):
                        f_ij = '%d_%d' % (i,j)
                        if f_ij in data['Flows'] and i != j:
                            m.addConstr(q_out[i][n] <= W * (Q_MAX[j] - q[j][n-1]) )
                            next_cell = j
                            F_MAX_ij = data['Flows'][f_ij]['F_MAX']
                        f_ji = '%d_%d' % (j,i)
                        if f_ji in data['Flows'] and i != j:
                            prev_cell = j

                    if next_cell is None: # destination cell
                        m.addConstr(q_out[i][n] == q[i][n])
                        m.addConstr(out_q[i][n] == q_out[i][n])
                        if n > 0:
                            m.addConstr(q[i][n] == q[i][n-1] + q_out[prev_cell][n-1] - q_out[i][n-1])
                        m.addConstr(q_in[i][n] == q_out[prev_cell][n])
                    elif prev_cell is None: # origin cell
                        #print (n,i)
                        if n > 0:
                            m.addConstr(q[i][n] == q[i][n-1] + in_q[i][n-1] - q_out[i][n-1])
                        m.addConstr(q_in[i][n] == in_q[i][n])
                        m.addConstr(q_out[i][n] <= q[i][n])

                    else: # ordinary cell
                        if Q_p[i] is None: # ordinary cell
                            m.addConstr(q_out[i][n] <= F_MAX_ij * DT[n])
                        else: # intersection cell
                            if fixed_plan == None:
                                m.addConstr(q_out[i][n] <= F_MAX_ij * DT[n] * quicksum([ p[Q_p[i][0]][q_p][n] for q_p in Q_p[i][1:] ]) )
                            else:
                                sum_fixed = sum([ p_fixed_plan[Q_p[i][0]][q_p][n] for q_p in Q_p[i][1:] ])
                                if sum_fixed < 0: print 'WARNING: sum(p_fixed_plan[q_%d,l_%d] @ n = %d) = %f' % (i,Q_p[i][0],n,sum_fixed)
                                state = [ p_fixed_plan[Q_p[i][0]][q_p][n] > 0 for q_p in Q_p[i][1:] ]
                                if True in state:
                                    m.addConstr(q_out[i][n] <= F_MAX_ij * DT[n])
                                else:
                                    m.addConstr(q_out[i][n] == 0)
                        m.addConstr(q_out[i][n] <= q[i][n])
                        if n > 0:
                            m.addConstr(q[i][n] == q[i][n-1] + q_out[prev_cell][n-1] - q_out[i][n-1])
                        m.addConstr(q_in[i][n] == q_out[prev_cell][n])

                    m.addConstr(q_out[i][n] - q_in[i][n-1] == d_1[i][n] - d_2[i][n])



                else: # QTM

                    fij_relax_constr.append(m.addConstr(q_in[i][n] == in_q[i][n] * DT[n] + quicksum([f[j][i][n]*DT[n] if '%d_%d' % (j,i) in data['Flows'] and i != j else 0 for j in range(Q)])))
                    fij_rhspen.append(1)
                    if obj == 'MIN_LIN_WANG':
                        if Q_OUT[i] > 0:
                            m.addConstr(out_q[i][n] == q[i][n])
                    # else:
                    #     if Q_OUT[i] > 0:
                    #         m.addConstr(out_q[i][n] == q[i][n] + q_stop[i][n])
                    #     else:
                    #         m.addConstr(out_q[i][n] == 0)
                    if exact: # and n < N - 1:
                        min2_constr(m, out_q[i][n], Q_OUT[i],
                                    (1.0 / DT[n]) * (q[i][n] + q_stop[i][n]),
                                    zout[i][n])
                    fij_relax_constr.append(m.addConstr(q_out[i][n] == out_q[i][n] * DT[n] + quicksum([f[i][j][n]*DT[n] if '%d_%d' % (i,j) in data['Flows'] and i != j else 0 for j in range(Q)])))
                    fij_rhspen.append(1)

                    if n == N - 1:
                        m.addConstr( q_out[i][n] <= q[i][n] + q_stop[i][n])
                    if n > 0:
                        m.addConstr(q[i][n] == q[i][n-1] - q_out[i][n-1]  + q_stop[i][n-1] ) #q_in[i][m0-1] * (DT[n-1]/DT[m0-1])  )

                    # relax_vars.append(q_out[i][n])
                    # ubpen.append(100)
                    # lbpen.append(100)
                    # relax_vars.append(q_in[i][n])
                    # ubpen.append(100)
                    # lbpen.append(100)
                    # relax_vars.append(q[i][n])
                    # ubpen.append(100)
                    # lbpen.append(100)
                    # relax_vars.append(q_stop[i][n])
                    # ubpen.append(100)
                    # lbpen.append(100)

                    t_m = time[n]-Q_DELAY[i]
                    t_w = time[n]-Q_DELAY[i] + DT[n]
                    #m0 = t_inv[i][n]
                    #w0 = t_inv[i][n+1]

                    debug(( 't0=',t0))
                    debug(( 't1=',t1))
                    debug(( 'N=',N))
                    debug(( 'Q_DELAY[i]=',Q_DELAY[i]))
                    debug(( 't[n]=',time[n]))
                    debug(( 't_m=',t_m))
                    debug(( 't_w=',t_w))
                    if i==queue_print:
                        debug(( n,'\t',time[n],'\t',t_m,'\t',t_w,))
                    if t_m >= time_full[0]:
                        m1 = 1
                        t_m1 = time_full[1]
                        debug(( 'if 1 m1:'))
                        while t_m1 <= t_m: ###and m1 < N - 1:
                            m1 += 1
                            debug(( m1,))
                            t_m1 = time_full[m1]
                        debug(( 'end if 1 m1'))
                        m0 = m1 - 1
                        w1 = m1 + 1
                        DTm = ((time_full[m1] - t_m) / DT[m0])
                        if w1 < N:
                            t_w1 = time_full[w1]
                            debug(( 'if 1 w1:'))
                            while t_w1 <= t_w: ###and w1 < N - 1:
                                w1 += 1
                                debug(( w1))
                                t_w1 = time_full[w1]
                            debug(( 'end if 1 w1'))
                        else:
                            w1 = m1
                        w0 = w1 - 1
                        DTw = ((t_w - time_full[w0]) / DT[w0])
                        DTw1 = ((time_full[w1] - t_w) / DT[w0])

                        #alpha = (t_m-time[m0])/(time[m1]-time[m0])
                        #if i==1: print '@',time[n],'alpha=',alpha,'t_m=',t_m,'t_n0=',time[m0],'t_m1=',time[m1],'1/DT_n0-1=',(1.0/DT[m0-1]),'t_m-Q_DELAY-t_n0=',(time[n] - Q_DELAY[i] - time[m0])
                        #m.addConstr(q[i][n] == q[i][n-1] - q_out[i][n-1] + (1 - alpha) * q_in[i][m0] + alpha * q_in[i][m1])

                        m.addConstr(q[i][n] + q_in[i][m0] * DTm + quicksum([q_in[i][k] for k in range(m1,n)]) <= Q_MAX[i],
                                    name='q_%d_%d_capacity(%s,%s){%d,%d}' % (i,n,t_m-t0,t_w-t0,m1,n))

                        m.addConstr(q_stop[i][n] == q_in[i][m0] * DTm + quicksum([q_in[i][k] for k in range(m1,w0)]) + q_in[i][w0] * DTw )

                        m.addConstr(qm_in[i][n] == m0)

                        if i == queue_print:
                            debug(( '\t',m0,'\t',w0,))
                            debug(( '\t',DTm,'\t',DTw,'\t',DTw1,' t_m >= 0 and t_w >= 0',))

                    elif t_w >= time_full[0] and t_m < time_full[0]:
                        m1 = 1
                        t_m1 = t_prev[1]
                        debug(( 'if 2 m1:'))
                        while t_m1 <= t_m: ### and m1 < len(t_prev) - 1:
                            m1 += 1
                            debug(( m1,))
                            t_m1 = t_prev[m1]
                        debug(( 'end if 2 m1'))
                        m0 = m1 - 1
                        m_end = m1
                        t_m_end = t_prev[m_end]
                        debug(( 'if 2 m_end:'))
                        while m_end < len(t_prev) - 1 and t_m_end < time_full[0]:
                            m_end += 1
                            debug(( m_end,))
                            t_m_end = t_prev[m_end]
                        debug(( 'end if 2 m_end'))
                        DTm = ((t_prev[m1] - t_m) / DT_prev[m0])
                        w1 = 1
                        t_w1 = time_full[w1]
                        debug(( 'if 2 w1:'))
                        while t_w1 <= t_w and w1 < N - 1:
                            w1 += 1
                            debug(( w1,))
                            t_w1 = time_full[w1]
                        debug(( 'end if 2 w1'))
                        w0 = w1 - 1
                        DTw = ((t_w - time_full[w0]) / DT[w0])
                        DTw1 = ((time_full[w1] - t_w) / DT[w0])
                        #print '\t',m1,'\t',m_end,'\t',range(m1,m_end)

                        m.addConstr(q[i][n] + q_in_prev[i][m0] * DTm
                                    + quicksum([q_in_prev[i][k] for k in range(m1,m_end)])
                                    + quicksum([q_in[i][k] for k in range(n)]) <= Q_MAX[i],
                                    name='q_%d_%d_capacity(%s,%s){%d,%d=%s}' % (i,n,t_m-t0,t_w-t0,
                                            m1,m_end,sum([q_in_prev[i][k] for k in range(m1,m_end)])))

                        m.addConstr(q_stop[i][n] == q_in_prev[i][m0] * DTm + q_in[i][w0] * DTw
                                    + quicksum([q_in_prev[i][k] for k in range(m1,m_end)])
                                    + quicksum([q_in[i][k] for k in range(w0)])  )

                        m.addConstr(qm_in[i][n] == m0)

                        if i==queue_print:
                            debug(( '\t',m0,'\t',w0,))
                            debug(( '\t',DTm,'\t',DTw,'\t',DTw1,' t_m < 0 and t_w >= 0',))

                    else:
                        m1 = 1
                        t_m1 = t_prev[1]
                        debug(( 'if 3 m1:'))
                        while t_m1 <= t_m: ### and m1 < len(t_prev) - 1:
                            m1 += 1
                            debug(( m1,))
                            t_m1 = t_prev[m1]
                        debug(( 'end if 3 m1'))
                        m0 = m1 - 1
                        m_end = m1
                        t_m_end = t_prev[m_end]
                        debug(( 'if 3 m_end:'))
                        while m_end < len(t_prev) - 1 and t_m_end < time_full[0]:
                            m_end += 1
                            debug(( m_end,))
                            t_m_end = t_prev[m_end]
                        debug(( 'end if 3 m_end'))
                        DTm = ((t_prev[m1] - t_m) / DT_prev[m0])
                        w1 = 1
                        t_w1 = t_prev[w1]
                        debug(( 'if 3 w1:'))
                        while t_w1 <= t_w: ### and w1 < len(t_prev) - 1:
                            w1 += 1
                            debug(( w1,))
                            t_w1 = t_prev[w1]
                        debug(( 'end if 3 w1'))
                        w0 = w1 - 1
                        DTw = ((t_w - t_prev[w0]) / DT_prev[w0])
                        DTw1 = ((t_prev[w1] - t_w) / DT_prev[w0])

                        m.addConstr(q[i][n] + q_in_prev[i][m0] * DTm
                                    + quicksum([q_in_prev[i][k] for k in range(m1,m_end)])
                                    + quicksum([q_in[i][k] for k in range(n)]) <= Q_MAX[i],
                                    name='q_%d_%d_capacity(%s,%s){%d,%d=%s}' % (i,n,t_m-t0,t_w-t0,
                                            m1,m_end,sum([q_in_prev[i][k] for k in range(m1,m_end)])))

                        m.addConstr(q_stop[i][n] == q_in_prev[i][m0] * DTm
                                    + quicksum([q_in_prev[i][k] for k in range(m1,w0)])
                                    + q_in_prev[i][w0] * DTw )

                        m.addConstr(qm_in[i][n] == m0)

                        if i==queue_print:
                            debug(( '\t',m0,'\t',w0,))
                            debug(( '\t',DTm,'\t',DTw,'\t',DTw1,' t_m < 0 and t_w < 0',))

                    if n > 0:
                        m.addConstr(q[i][n] - q[i][n-1] == d_1[i][n] - d_2[i][n])


                    if i==queue_print:
                        debug(())

                if fixed_plan == None:
                    for j in range(Q):
                        f_ij = '%d_%d' % (i,j)
                        if f_ij in data['Flows'] and i != j:
                            F_ij = data['Flows'][f_ij]['F_MAX']
                            if 'Pr' in data['Flows'][f_ij]:
                                Pr_ij = data['Flows'][f_ij]['Pr']
                            else:
                                Pr_ij = 1.0
                            if (i,j) not in dominant_flows and "F_Y" not in data['Flows'][f_ij] and not exact: # and False:
                                if Q_p[i] != None:
                                    m.addConstr( f[i][j][n] <= F_ij * quicksum([ p[Q_p[i][0]][q_p][n] for q_p in Q_p[i][1:] ]) )
                                m.addConstr( f[i][j][n] <= Pr_ij * ( quicksum([f[i][k][n] if '%d_%d' % (i,k) in data['Flows'] and i != k else 0 for k in range(Q)]) ) )

                            else:
                                if Q_p[i] != None:
                                    F_max = F_ij * quicksum([ p[Q_p[i][0]][q_p][n] for q_p in Q_p[i][1:] ])
                                else:
                                    if "F_Y" in data['Flows'][f_ij]:
                                        for x_y in data['Flows'][f_ij]["F_Y"]:
                                            x = int(x_y.split('_')[0])
                                            y = int(x_y.split('_')[1])
                                            f_xy = '%d_%d' % (x,y)
                                            if f_xy in data['Flows']:
                                                F_xy = data['Flows'][f_xy]['F_MAX']
                                            #m.addConstr( f[i][j][n] <= F_ij / F_xy  * (F_xy - f[x][y][n]) , name = 'f_%d_%d_yeild_to_f_%d_%d' % (i,j,x,y))

                                            F_max = F_ij / F_xy  * (F_xy - f[x][y][n])
                                    else:
                                        F_max = F_ij
                                        #print 'Adding min3 for %s yielding to %s ' % (f_ij,f_xy)
                                constr = min3_constr(m, f[i][j][n], F_max, # Pr_ij * F_max
                                                     Pr_ij * (1.0/DT[n]) * (Q_MAX[j] - q[j][n]),
                                                     Pr_ij * (1.0/DT[n]) * (q_stop[i][n] + q[i][n]),
                                                     z1[i][j][n], z2[i][j][n], phi[i][j][n])
                                for c in constr:
                                    min_relax_constr.append(c)
                                    min_rhspen.append(1)

                                #m.addConstr( f[i][j][n] <= F_max)
                                #m.addConstr( f[i][j][n] <= Pr_ij * ( quicksum([f[i][k][n] if '%d_%d' % (i,k) in data['Flows'] and i != k else 0 for k in range(Q)]) ) )

                                # m.addConstr( fij[i][n] == Pr_ij * (1.0/DT[n]) * (q_stop[i][n] + q[i][n]) )
                                # else:
                                # #print f_ij
                                # if Q_p[i] != None:
                                #     F_max = F_ij * quicksum([ p[Q_p[i][0]][q_p][n] for q_p in Q_p[i][1:] ])
                                # else:
                                #     F_max = F_ij
                                # min3_constr(m, f[i][j][n], F_max,
                                #             Pr_ij * (1.0/DT[n]) * (Q_MAX[j] - q[j][n]),
                                #             Pr_ij * (1.0/DT[n]) * (q_stop[i][n] + q[i][n]))
                                # #m.addConstr(fij[i][n] == 2)
                                # m.addConstr( fij[i][n] == Pr_ij * (1.0/DT[n]) * (q_stop[i][n] + q[i][n]) )



                                        #m.addConstr( fij[i][n] == quicksum([ (T_MAX - time[nn] + 1) * (1.0 / F_ij) * f[i][j][nn] for nn in range(n)])) #(T_MAX - time[n]) * (1.0 / F_ij) * f[i][j][n] )
                                        #m.addConstr( fxy[i][n] == quicksum([ (T_MAX - time[nn] + 1) * (1.0 / F_xy) * f[x][y][nn] for nn in range(n)])) #(T_MAX - time[n]) * (1.0 / F_xy) * f[x][y][n] )
                                        #m.addConstr( (T_MAX - time[n]) * (1.0 / F_xy) * f[x][y][n] <= (T_MAX - time[n]) * (1.0 / F_ij) * f[i][j][n] )

                else: # Fixed Plan
                    for j in range(Q):
                        f_ij = '%d_%d' % (i,j)
                        if f_ij in data['Flows'] and i != j:
                            F_ij = data['Flows'][f_ij]['F_MAX']
                            if 'Pr' in data['Flows'][f_ij]:
                                Pr_ij = data['Flows'][f_ij]['Pr']
                            else:
                                Pr_ij = 1.0
                            if (i,j) not in dominant_flows and "F_Y" not in data['Flows'][f_ij] and not exact: # and False:
                                if Q_p[i] != None:
                                    sum_fixed = sum([p_fixed_plan[Q_p[i][0]][q_p][n] for q_p in Q_p[i][1:]])
                                    if sum_fixed < 0: print 'WARNING: sum(p_fixed_plan[q_%d,l_%d] @ n = %d) = %f' % (
                                    i, Q_p[i][0], n, sum_fixed)
                                    state = [p_fixed_plan[Q_p[i][0]][q_p][n] > 0 for q_p in Q_p[i][1:]]
                                    if True in state:
                                        F_max = F_ij  # * quicksum([ p[Q_p[i][0]][q_p][n] for q_p in Q_p[i][1:] ])
                                    else:
                                        F_max = 0
                                    m.addConstr(f[i][j][n] <= F_max) # m.addConstr( f[i][j][n] <= F_ij * quicksum([ p[Q_p[i][0]][q_p][n] for q_p in Q_p[i][1:] ]) )
                                m.addConstr( f[i][j][n] <= Pr_ij * ( quicksum([f[i][k][n] if '%d_%d' % (i,k) in data['Flows'] and i != k else 0 for k in range(Q)]) ) )

                            else:
                                if Q_p[i] != None:
                                    sum_fixed = sum([ p_fixed_plan[Q_p[i][0]][q_p][n] for q_p in Q_p[i][1:] ])
                                    if sum_fixed < 0: print 'WARNING: sum(p_fixed_plan[q_%d,l_%d] @ n = %d) = %f' % (i,Q_p[i][0],n,sum_fixed)
                                    state = [ p_fixed_plan[Q_p[i][0]][q_p][n] > 0 for q_p in Q_p[i][1:] ]
                                    if True in state:
                                        F_max = F_ij # * quicksum([ p[Q_p[i][0]][q_p][n] for q_p in Q_p[i][1:] ])
                                    else:
                                        F_max = 0
                                else:
                                    if "F_Y" in data['Flows'][f_ij]:
                                        for x_y in data['Flows'][f_ij]["F_Y"]:
                                            x = int(x_y.split('_')[0])
                                            y = int(x_y.split('_')[1])
                                            f_xy = '%d_%d' % (x,y)
                                            if f_xy in data['Flows']:
                                                F_xy = data['Flows'][f_xy]['F_MAX']
                                            #m.addConstr( f[i][j][n] <= F_ij / F_xy  * (F_xy - f[x][y][n]) , name = 'f_%d_%d_yeild_to_f_%d_%d' % (i,j,x,y))

                                            F_max = F_ij / F_xy  * (F_xy - f[x][y][n])
                                    else:
                                        F_max = F_ij
                                        #print 'Adding min3 for %s yielding to %s ' % (f_ij,f_xy)
                                constr = min3_constr(m, g[i][j][n], F_max, # Pr_ij * F_max
                                                     Pr_ij * (1.0/DT[n]) * (Q_MAX[j] - q[j][n]),
                                                     Pr_ij * (1.0/DT[n]) * (q_stop[i][n] + q[i][n]),
                                                     z1[i][j][n], z2[i][j][n], phi[i][j][n])
                                m.addConstr(f[i][j][n] == g[i][j][n])
                                for c in constr:
                                    min_relax_constr.append(c)
                                    min_rhspen.append(1)

                    # for j in range(Q):
                    #     f_ij = '%d_%d' % (i,j)
                    #     if f_ij in data['Flows'] and i != j:
                    #         F_ij = data['Flows'][f_ij]['F_MAX']
                    #         if Q_p[i] != None:
                    #             sum_fixed = sum([ p_fixed_plan[Q_p[i][0]][q_p][n] for q_p in Q_p[i][1:] ])
                    #             if sum_fixed < 0: print 'WARNING: sum(p_fixed_plan[q_%d,l_%d] @ n = %d) = %f' % (i,Q_p[i][0],n,sum_fixed)
                    #             state = [ p_fixed_plan[Q_p[i][0]][q_p][n] > 0 for q_p in Q_p[i][1:] ]
                    #             if True in state:
                    #                 F_max = F_ij
                    #                 if 'Pr' in data['Flows'][f_ij]:
                    #                     Pr_ij = data['Flows'][f_ij]['Pr']
                    #                 else:
                    #                     Pr_ij = 1.0
                    #                 min3_constr(m, f[i][j][n], F_max, # Pr_ij * F_max
                    #                         Pr_ij * (1.0/DT[n]) * (Q_MAX[j] - q[j][n]),
                    #                         Pr_ij * (1.0/DT[n]) * (q_stop[i][n] + q[i][n]))
                    #                 # m.addConstr( f[i][j][n] <= data['Flows'][f_ij]['F_MAX']  )
                    #             else:
                    #                 F_max = 0
                    #                 m.addConstr( f[i][j][n] == 0 )
                    #         else:
                    #             min3_constr(m, f[i][j][n], F_ij, # Pr_ij * F_max
                    #                          (1.0/DT[n]) * (Q_MAX[j] - q[j][n]),
                    #                          (1.0/DT[n]) * (q_stop[i][n] + q[i][n]))
                    #             #m.addConstr( f[i][j][n] <= data['Flows'][f_ij]['F_MAX'] * sum([ p_fixed_plan[Q_p[i][0]][q_p][n] for q_p in Q_p[i][1:] ]) )
                    #
                    #
                    #             # m.addConstr( f[i][j][n] <= Pr_ij * ( quicksum([f[i][k][n] if '%d_%d' % (i,k) in data['Flows'] and i != k else 0 for k in range(Q)]) ) )
                    #
                    #         if "F_Y" in data['Flows'][f_ij]:
                    #
                    #             for x_y in data['Flows'][f_ij]:
                    #                 x = x_y.splt('_')[0]
                    #                 y = x_y.splt('_')[1]
                    #                 f_xy = '%d_%d' % (x,y)
                    #                 if f_xy in data['Flows']:
                    #
                    #                     F_ij = data['Flows'][f_ij]['F_MAX']
                    #                     F_xy = data['Flows'][f_xy]['F_MAX']
                    #                     m.addConstr( f[i][j][n] <= Fij / F_xy  * (F_xy - f[x][y][n]) , name = 'f_%d_%d_yeild_to_f_%d_%d' % (i,j,x,y))
                    #                     min_constr(m, f[x][y][n], F_xy, (1.0/DT[n]) * Q_MAX[y] - q[y][n], (1.0/DT[n]) * q[x][n-1])
                    #                     #m.addConstr( fij[i][n] == quicksum([ (T_MAX - time[nn] + 1) * (1.0 / F_ij) * f[i][j][nn] for nn in range(n)])) #(T_MAX - time[n]) * (1.0 / F_ij) * f[i][j][n] )
                    #                     #m.addConstr( fxy[i][n] == quicksum([ (T_MAX - time[nn] + 1) * (1.0 / F_xy) * f[x][y][nn] for nn in range(n)])) #(T_MAX - time[n]) * (1.0 / F_xy) * f[x][y][n] )

            if fixed_plan == None:
                for i in range(L):
                    m.addConstr(quicksum([p[i][j][n] for j in range(len(l[i]))]) == 1)
                    np=len(l[i])
                    #transit_extra = 0
                    #if transit[i] is not None:
                    #    for j in range(np):
                    #        if transit[i][j] is not None and P_MAX[i][j] < transit[i][j][1] and time[n] >= transit[i][j][0] and (time[n] - transit[i][j][0]) % transit[i][j][2] < transit[i][j][1]:
                    #            transit_extra = transit[i][j][1] - P_MAX[i][j]


                    for j in range(np):
                        if TRANSIT and any([phase[n] for phase in p_transit[i]]):
                            if p_transit[i][j][n] is True:
                                m.addConstr(p[i][j][n] == 1)
                            else:
                                m.addConstr(p[i][j][n] == 0)
                            if n > 0:
                                m.addConstr(d[i][j][n] == d[i][j][n-1])

                        else:

                            if time[n] > time[0] + C_MAX[i] and args.fixed_phase:
                                m.addConstr(d[i][j][n] <= dp_fixed[i][j] + P_MAX[i][j] * (p[i][j][n]), name='fixed_phase_lb_%d_%d_%d' % (i,j,n))
                                m.addConstr(d[i][j][n] >= dp_fixed[i][j] - P_MAX[i][j] * (p[i][j][n]), name='fixed_phase_ub_%d_%d_%d' % (i,j,n))

                            else:

                                relax_constr.append(m.addConstr(d[i][j][n] >= P_MIN[i][j] * (1 - p[i][j][n])))
                                rhspen.append(2)


                                relax_constr.append(m.addConstr(d[i][j][n] <= P_MAX[i][j] ) )
                                rhspen.append(2)

                                relax_vars.append(d[i][j][n])
                                rhspen.append(2)
                            if n > 0:
                                relax_constr.append(m.addConstr(d[i][j][n] <= P_MAX[i][j] * (1 - p[i][j][n] + p[i][j][n-1]), name='d_reset_%d_%d_%d' % (i,j,n)))
                                rhspen.append(2)
                                #ubpen.append(1)
                                #lbpen.append(1)

                                m.addConstr(p[i][j][n-1] <= p[i][j][n] + p[i][(j+1) % np][n])
                                #m.addConstr(p[i][j][n] + p[i][(j+1) % np][n] <= 1)
                                m.addConstr(d[i][j][n] >= d[i][j][n-1] + p[i][j][n-1] * DT[n-1] - 10*P_MAX[i][j] * (1 - p[i][j][n-1]), name='d_inc_ub_%d_%d_%d' % (i,j,n) )
                                m.addConstr(d[i][j][n] <= d[i][j][n-1] + p[i][j][n-1] * DT[n-1] + 10*P_MAX[i][j] * (1 - p[i][j][n-1]), name='d_inc_lb_%d_%d_%d' % (i,j,n) )

                                m.addConstr(d[i][j][n] >= d[i][j][n-1] - 10*P_MAX[i][j] * p[i][j][n],name='d_hold_ub_%d_%d_%d' % (i,j,n) )
                                m.addConstr(d[i][j][n] <= d[i][j][n-1] + 10*P_MAX[i][j] * p[i][j][n-1],name='d_hold_lb_%d_%d_%d' % (i,j,n))
                            elif init_prev_file:
                                m.addConstr(p[i][j][n] == p0[i][j])
                                m.addConstr(d[i][j][n] == d0[i][j])

                    if args.fixed_cycle and n > 0:
                        m.addConstr(d[i][0][n-1] + quicksum([d[i][j][n] for j in range(1,np)]) <= c_fixed[i] + C_MAX[i] * (1 - ( p[i][0][n] - p[i][0][n-1])))
                        m.addConstr(d[i][0][n-1] + quicksum([d[i][j][n] for j in range(1,np)]) >= c_fixed[i] - C_MAX[i] * (1 - ( p[i][0][n] - p[i][0][n-1])))
                    if n > 0:
                        m.addConstr(c_on[i][n] == 1 - ( p[i][0][n] - p[i][0][n-1]))
                        m.addConstr(tct[i][n] == d[i][0][n-1] + quicksum([d[i][j][n] for j in range(1,np)]))
                    else:
                        m.addConstr(c_on[i][n] == 0)
                        m.addConstr(tct[i][n] == 0)
                    if TRANSIT and any([xx[n] for xx in p_transit[i]]) is False and n > 0:
                    #if any(p_transit[i]) is False:
                        relax_constr.append(m.addConstr(d[i][0][n-1] + quicksum([d[i][j][n] for j in range(1,np)]) <= C_MAX[i] ))
                        rhspen.append(2)
                        relax_constr.append(m.addConstr(d[i][0][n-1] + quicksum([d[i][j][n] for j in range(1,np)]) >= C_MIN[i] * (p[i][0][n] - p[i][0][n-1])))
                        rhspen.append(2)



        print 'cars_in =',cars_in

        # Switch off console output from Gurobi
        if not verbose:
            m.setParam(GRB.Param.LogToConsole,0)
        if nthreads>0:
            m.setParam(GRB.Param.Threads,nthreads)
        if accuracy>0:
            m.setParam(GRB.Param.MIPGap,accuracy/100)
        if timelimit>0:
            m.setParam(GRB.Param.TimeLimit,timelimit)
        if seed != 0:
            m.setParam(GRB.Param.Seed,seed)

        if tune==True:
            m.tune()
            for i in range(m.tuneResultCount):
                m.getTuneResult(i)
                m.write(tune_file+str(i)+'.prm')
            m.getTuneResult(0)
        # rub the Gurobi optimizer
        if param != None:
            m.read(param)
        print 'relax_constr=',len(relax_constr)
        print 'rhspen=',len(rhspen)
        print 'relax_vars=',len(relax_vars)
        print 'ubpen=',len(ubpen)
        print 'lbpen=',len(lbpen)
        setup_time = clock_time.time() - start_time
        m.optimize()
        solve_time = clock_time.time() - start_time

        status_codes = [ ['NONE', 0,'Not a status code'],
            ['LOADED', 1, 'Model is loaded, but no solution information is available.'],
            ['OPTIMAL', 2,
             'Model was solved to optimality (subject to tolerances), and an optimal solution is available.'],
            ['INFEASIBLE', 3, 'Model was proven to be infeasible.'],
            ['INF_OR_UNBD', 4,
             'Model was proven to be either infeasible or unbounded. To obtain a more definitive conclusion, set the DualReductions parameter to 0 and reoptimize.'],
            ['UNBOUNDED', 5,
             '''Model was proven to be unbounded. Important note: an unbounded status indicates the presence of an unbounded ray that allows the objective to improve without limit.
             It says nothing about whether the model has a feasible solution. If you require information on feasibility, you should set the objective to zero and reoptimize.'''],
            ['CUTOFF', 6,
             'Optimal objective for model was proven to be worse than the value specified in the Cutoff parameter. No solution information is available.'],
            ['ITERATION_LIMIT', 7,
             '''Optimization terminated because the total number of simplex iterations performed exceeded the value specified in the IterationLimit parameter,
             or because the total number of barrier iterations exceeded the value specified in the BarIterLimit parameter.'''],
            ['NODE_LIMIT', 8,
             'Optimization terminated because the total number of branch-and-cut nodes explored exceeded the value specified in the NodeLimit parameter.'],
            ['TIME_LIMIT', 9,
             'Optimization terminated because the time expended exceeded the value specified in the TimeLimit parameter.'],
            ['SOLUTION_LIMIT', 10,
             'Optimization terminated because the number of solutions found reached the value specified in the SolutionLimit parameter.'],
            ['INTERRUPTED', 11, 'Optimization was terminated by the user.'],
            ['NUMERIC', 12, 'Optimization was terminated due to unrecoverable numerical difficulties.'],
            ['SUBOPTIMAL', 13, 'Unable to satisfy optimality tolerances; a sub-optimal solution is available.'],
            ['INPROGRESS', 14,
             'An asynchronous optimization call was made, but the associated optimization run is not yet complete.'],
        ]

        if m.status == GRB.INFEASIBLE or m.status == GRB.INF_OR_UNBD:
            #print "Model Infeasible, calulating IIS: ",
            #m.computeIIS()
            #m.write('model_iis.ilp')
            #print 'Done. Wrote to model_iis.ilp'

            print 'min_relax_constr=',len(min_relax_constr)
            print 'min_rhspen=',len(min_rhspen)
            print 'min_relax_vars=',len(min_relax_vars)
            print 'min_ubpen=',len(min_ubpen)
            print 'min_lbpen=',len(min_lbpen)
            print 'fij_relax_vars=',len(min_relax_vars)
            print 'fij_ubpen=',len(min_ubpen)
            print 'fij_lbpen=',len(min_lbpen)
            print 'Model is infeasible, relaxing model...'
            # relax_obj = m.feasRelax(1,False,None,None,None,relax_constr,rhspen)
            # relax_obj = m.feasRelax(1,False,None,None,None,fij_relax_constr,fij_rhspen)
            # relax_obj = m.feasRelax(2,False,min_relax_vars,min_lbpen,min_ubpen,min_relax_constr,min_rhspen)
            relax_obj = m.feasRelax(2,False,fij_relax_vars,fij_lbpen,fij_ubpen,None,None)
            print 'Relaxation objective value:',relax_obj
            m.optimize()
            solve_time = clock_time.time() - start_time

        if m.status == GRB.INFEASIBLE or m.status == GRB.INF_OR_UNBD:
            print "Solver status: ", status_codes[m.status][0]
            print status_codes[m.status][2]
            print "Model Infeasible, calulating IIS: ",
            m.computeIIS()
            m.write('model_iis_error.ilp')
            print 'Done. Wrote model_iis_error.ilp'
            return None
        else:
            print "Solver status: ", status_codes[m.status][0]
            print status_codes[m.status][2]
            print 'Obj:', m.objVal
            print 'Total Travel Time:', total_travel_time.x
            print 'Total Stops      :', total_stops.x
            # print 'Kappa            :', m.Kappa
            print 'Setup time: %s seconds' % setup_time
            print 'Solve time: %s seconds' % solve_time
            wh_test = {}
            if solver_model != 'CTM' and no_warning == False:

                print 'Testing for traffic withholding:',
                withholding = False
                error_msg = ''
                WITHHOLDING_TEST_TOLERANCE = 5 # AMD Opterons in cluster trip at 6 DP.
                for i in range(Q):
                    for n in range(0,N - 1):
                        error_data = []
                        try:
                            error_data.append('in_%d  : %s' % (i,in_q[i][n].x))
                            error_data.append('Q_in_%d: %s' % (i,Q_in[i][n]))
                            numpy.testing.assert_almost_equal([in_q[i][n].x],[Q_in[i][n]],
                                                              decimal = WITHHOLDING_TEST_TOLERANCE)
                        except AssertionError,e:
                            if withholding == False:
                                withholding = True
                                print
                                error_msg =  'Traffic withholding at input: in_%d t=%s' %(i,time[n])
                            print 'WARNING Traffic withholding at input: in_%d t=%s' %(i,time[n])
                            for msg in error_data:
                                print '   ',msg
                    for n in range(0, N - 1):
                        error_data = []
                        try:
                            error_data.append('out_%d                           : %s' % (i, out_q[i][n].x))
                            error_data.append('(1.0/DT[n]) * (q_stop_%d + q_%d) : %s' % (i, i, (1.0/DT[n]) * (q_stop[i][n].x + q[i][n].x)))
                            error_data.append('Q_OUT_%d                         : %s' % (i, Q_OUT[i]))
                            numpy.testing.assert_almost_equal([out_q[i][n].x],
                                                              [ min((1.0/DT[n]) * (q_stop[i][n].x + q[i][n].x), Q_OUT[i]) ],
                                                              decimal = WITHHOLDING_TEST_TOLERANCE)

                        except AssertionError, e:
                            if withholding == False:
                                withholding = True
                                print
                                error_msg = 'Traffic withholding at output: out_%d t=%s' % (i, time[n])
                            print 'WARNING Traffic withholding at output: out_%d t=%s' % (i, time[n])
                            for msg in error_data:
                                print '   ', msg

                    for flow in data['Flows'].keys():
                        x = int(flow.split('_')[0])
                        j = int(flow.split('_')[1])
                        f_ij = data['Flows'][flow]

                        if x == i:
                            wh_ij = [0] * (N - 1)
                            F_ij = f_ij["F_MAX"]
                            if 'Pr' in f_ij:
                                Pr_ij = f_ij["Pr"]
                            else:
                                Pr_ij = 1.0
                            for n in range(N - 1):
                                error_data = []
                                error_data.append('Pr_ij = %s' % Pr_ij)
                                F_max = F_ij
                                if "F_Y" in f_ij:
                                    for f_xy in f_ij["F_Y"]:
                                        x = int(f_xy.split('_')[0])
                                        y = int(f_xy.split('_')[1])
                                        if f_xy in data['Flows']:
                                            F_xy = data['Flows'][f_xy]['F_MAX']
                                            F_max *= (1.0 / F_xy)  * (F_xy - f[x][y][n].x)
                                if Q_p[i] != None:
                                    if fixed_plan is None:
                                        sum_p = sum([ p[Q_p[i][0]][q_p][n].x for q_p in Q_p[i][1:] ])
                                        error_data.append('sum_p = %d %s' % (sum_p,[ 'p_{%d,%d}=%d' % (Q_p[i][0],q_p,p[Q_p[i][0]][q_p][n].x) for q_p in Q_p[i][1:] ]))
                                    else:
                                        sum_p = sum([ p_fixed_plan[Q_p[i][0]][q_p][n] for q_p in Q_p[i][1:] ])
                                        error_data.append('sum_p = %d %s' % (sum_p,[ p_fixed_plan[Q_p[i][0]][q_p][n] for q_p in Q_p[i][1:] ]))
                                    if sum_p < 0.5:
                                        F_max = 0

                                try:
                                    error_data.append('Pr_ij * F_max: %s' % (F_max)) #Pr_ij * F_max
                                    error_data.append('(1.0/DT[n]) * Pr_ij * (q_stop[i][n].x + q[i][n].x): %s'% ((1.0/DT[n]) * Pr_ij * (q_stop[i][n].x + q[i][n].x)))
                                    error_data.append('(1.0/DT[n]) * Pr_ij * (Q_MAX[j] - q[j][n].x): %s' % ((1.0/DT[n]) * Pr_ij * (Q_MAX[j] - q[j][n].x)))
                                    error_data.append('min = %s' % min( Pr_ij * F_max, (1.0/DT[n]) * Pr_ij * (q_stop[i][n].x + q[i][n].x), (1.0/DT[n]) * Pr_ij * (Q_MAX[j] - q[j][n].x)))
                                    error_data.append('f_%d,%d = %s' % (i,j,f[i][j][n].x))
                                    numpy.testing.assert_almost_equal([f[i][j][n].x],[min( F_max, #Pr_ij * F_max
                                                                      (1.0/DT[n]) * Pr_ij * (q_stop[i][n].x + q[i][n].x),
                                                                      (1.0/DT[n]) * Pr_ij * (Q_MAX[j] - q[j][n].x))],
                                                                      decimal = WITHHOLDING_TEST_TOLERANCE)

                                except AssertionError,e:
                                    if withholding == False:
                                        withholding = True
                                        print
                                        error_msg =  'Traffic withholding: q_%d f_%d,%d t=%s, n=%d' %(i,i,j,time[n],n)
                                    print 'WARNING Traffic withholding: q_%d f_%d,%d t=%s n=%d' %(i,i,j,time[n],n)
                                    for msg in error_data:
                                        print '   ',msg
                                    wh_ij[n] = 1
                            wh_test[flow] = wh_ij
                        # print wh_ij

                if withholding:
                    if no_assertion_fail == False:
                        raise AssertionError(error_msg)
                else:
                    print 'None.'

            #
            t=t0
            time = []
            for _dt in DT[:-1]:
                time.append(t)
                t+=_dt
            
            if 'Out' not in data:
                data['Out'] = dict()
            if run != None:
                if 'Run' not in data['Out']:
                    data['Out']['Run'] = []
                if run >=len(data['Out']['Run']):
                    data['Out']['Run'].append(dict())
                data_out = data['Out']['Run'][run]
            else:
                data_out = data['Out']
            if step != None and mip_start != 'final':
                if 'Step' not in data_out:
                    data_out['Step'] = []
                data_out['Step'].append(dict())
                data_out = data_out['Step'][step]

            data_out['N'] = n_samples
            data_out['t'] = time
            data_out['DT'] = DT
            data_out['DT_offset'] = DT_offset
            data_out['gurobi_version'] = '.'.join(map(str,gurobi.version()))
            data_out['setup_time'] = setup_time
            data_out['solve_time'] = solve_time
            data_out['solver_runtime'] = m.Runtime
            data_out['objval'] = m.objVal
            data_out['obj'] = obj
            data_out['status'] = status_codes[m.status][0]
            data_out['alpha'] = alpha_obj
            data_out['beta'] = beta_obj
            data_out['gamma'] = gamma_obj
            data_out['total_travel_time'] = total_travel_time.x
            data_out['total_stops'] = total_stops.x
            data_out['seed'] = seed
            data_out['cpu'] = get_processor_name()
            data_out['num_vars'] = m.NumVars
            data_out['num_binvars'] = m.NumBinVars
            data_out['num_constrs'] = m.NumConstrs
            data_out['lost_time'] = lost_time
            data_out['solver_model'] = solver_model
            data_out['buffer_input'] = buffer_input
            data_out['withholding'] = withholding
            if timelimit<1e30:
                data_out['time_limit'] = timelimit
            else:
                data_out['time_limit'] = timelimit
            data_out['accuracy'] = accuracy
            if label != None:
                data_out['label'] = label
            else:
                label = (data['out_filename'].split('.')[0]).replace('_',' ')
                data_out['label'] = label
            for i,q_i in enumerate(data['Queues']):
                # q_i['q0']  =  q[i][n].x
                # q_i['q0_in'] = q_in[i][n].x
                # q_i['q0_out'] = q_out[i][n].x
                data_out[r'q_%d' % i]  =  [q[i][n].x for n in range(N-1)]
                data_out[r'q_{%d,in}' % i] = [q_in[i][n].x for n in range(N-1)]
                data_out[r'q_{%d,stop}' % i] = [q_stop[i][n].x for n in range(N-1)]
                data_out[r'qm_{%d,in}' % i] = [qm_in[i][n].x for n in range(N-1)]
                data_out[r'qw_{%d,in}' % i] = [qw_in[i][n].x for n in range(N-1)]
                data_out[r'total_q_{%d,in}' % i] = sum(data_out[r'q_{%d,in}' % i])
                if major_frame==0: print 'total q_in,%d=' % i, sum(data_out[r'q_{%d,in}' % i])
                data_out[r'q_{%d,out}' % i] = [q_out[i][n].x for n in range(N-1)]
                data_out[r'total_q_{%d,out}' % i] = sum(data_out[r'q_{%d,out}' % i])
                if major_frame==0: print 'total q_out,%d=' % i, sum(data_out[r'q_{%d,out}' % i])
                data_out[r'dq_{%d,1}' % i] = [d_1[i][n].x for n in range(N - 1)]
                data_out[r'dq_{%d,2}' % i] = [d_2[i][n].x for n in range(N-1)]
                data_out[r'stops_q_%d' % i] = [d_1[i][n].x + d_2[i][n].x for n in range(N - 1)]
                data_out[r'in_%d' % i] = [in_q[i][n].x for n in range(N-1)]
                data_out[r'out_%d' % i] = [out_q[i][n].x for n in range(N-1)]

                data_out[r'fij_%d' % i] = [fij[i][n].x for n in range(N-1)]
                data_out[r'fxy_%d' % i] = [fxy[i][n].x for n in range(N-1)]

                data_out[r'q_{%d,abs}' % i] = [ abs( q[i][n+1].x - q[i][n].x ) for n in range(N-1)]
                data_out[r'c_%d' % i] = [ abs( q[i][n+1].x - q[i][n].x ) for n in range(N-1)]
            data_out[r'total_q_in'] = sum([sum(data_out[r'q_{%d,in}' % i]) for i,q_i in enumerate(data['Queues'])])
            data_out[r'total_q_out'] = sum([sum(data_out[r'q_{%d,out}' % i]) for i,q_i in enumerate(data['Queues'])])
            if major_frame==0:
                if data_out[r'total_q_in'] > data_out[r'total_q_out']:
                    print 'WARNING: total q_out < total_ q_in. Total q_in:',data_out[r'total_q_in'],'Total q_out:',data_out[r'total_q_out']
                else:
                    print 'Total q_in:',data_out[r'total_q_in'],'Total q_out:',data_out[r'total_q_out']
            for i,l_i in enumerate(data['Lights']):
                for j, _ in enumerate(l_i['p0']):
                    # l_i['p0'][j] = p[i][j][n].x
                    # l_i['c0'][j] = c[i][j][n].x
                    # l_i['d0'][j] = d[i][j][n].x
                    if fixed_plan == None:
                        data_out[r'p_{%d,%d}' % (i,j)] = [p[i][j][n].x for n in range(N-1)]
                        #data_out[r'c_{%d,%d}' % (i,j)] = [c[i][j][n].x for n in range(N-1)]
                        data_out[r'd_{%d,%d}' % (i,j)] = [d[i][j][n].x for n in range(N-1)]
                    else:
                        data_out[r'p_{%d,%d}' % (i,j)] = [p_fixed_plan[i][j][n] for n in range(N-1)]
                        #data_out[r'c_{%d,%d}' % (i,j)] = [c[i][j][n].x for n in range(N-1)]
                        data_out[r'd_{%d,%d}' % (i,j)] = [d_fixed_plan[i][j][n] for n in range(N-1)]
                    data_out[r'dfixed_{%d,%d}' % (i,j)] = dp_fixed[i][j].x
                    if 'transits' in l_i:
                        for transit in l_i['transits']:
                            if args.no_transit is None or (len(args.no_transit) > 0 and transit['id'] not in args.no_transit):
                                data_out[r'%s-l_%d' % (transit['id'],i)] = [1 if x else 0 for x in p_transit[i][transit['phase']] ]
                data_out[r'cfixed_%d' % i] = c_fixed[i].x
                data_out[r'con_%d' % i] = [c_on[i][n].x  for n in range(N-1)]
                data_out[r'tct_%d' % i] = [tct[i][n].x  for n in range(N-1)]
            for f_ij,f_i in data['Flows'].iteritems():
                (i,j) = f_ij.split('_')
                i = int(i); j = int(j)
                # f_i['f0'] = f[i][j][n].x
                data_out[r'f_{%d,%d}' % (i,j)] = [f[i][j][n].x for n in range(N-1)]
                data_out[r'z1_{%d,%d}' % (i,j)] = [z1[i][j][n].x for n in range(N-1)]
                data_out[r'z2_{%d,%d}' % (i,j)] = [z2[i][j][n].x for n in range(N-1)]
                data_out[r'phi_{%d,%d}' % (i,j)] = [phi[i][j][n].x for n in range(N-1)]
                data_out[r'g_{%d,%d}' % (i,j)] = [g[i][j][n].x for n in range(N-1)]
                if f_ij in wh_test:
                    data_out[r'wh_{%d,%d}' % (i, j)] = wh_test[f_ij]

    except GurobiError,e:
        print 'Error reported: ',e.message

    return data

# def print_table(v):
#     #vars = [p[0][0],p[0][1],p[0][2],p[0][3],d[0][0],d[0][2],p[1][0],p[1][1],p[1][2],p[1][3],d[1][0],d[1][2],q[0],q[1],q[2],q[3],q[4],q[5],q[6],q[7],f[0][2],f[1][3],q_in[0],q_in[1],q_in[2],q_out[0],q_out[1],q_out[2],q_out[3],q_out[4],q_out[5],q_out[6],q_out[7]]
#     vars = [p[0][0],p[0][1],p[0][2],p[0][3],d[0][0],d[0][2],d_sl[0][0],d_sl[0][1],d_sl[0][2],d_sl[0][3],re[0],rc[0],rs[0],q_sl[0],q_sl[1],q[0],q[1],q[2],f[0][2],f[1][2],q_in[0],q_in[1],q_in[2],q_out[0],q_out[1],q_out[2]]
#
#
#     for v in vars:
#         for n in range(N):
#             if n==0:
#                 print "%6s" % (v[0].varName),
#
#             if v[n].vType == 'B':
#                 if abs(v[n].x) < 0.1:
#                     print "  0",
#                 else:
#                     print " %2.0f" % (v[n].x),
#             else:
#                 print " %2.0f" % (v[n].x),
#         print

def rm_vars(data):
    for key in data.keys():
        if key[0:2] in ['q_','d_','p_','f_','dq','c_','qw','qm','in','ou','co','tc','df','to'] or key in ['Fixed_Plan']:
            del data[key]

def DT_alpha_n_blend(dt_0,dt_1,N):
    DT = []
    t = 0
    n = 1
    while n <= N:
        alpha = float(n) / float(N)
        DT.append(dt_0 * (1 - alpha) + dt_1 * alpha)
        n += 1
        t += DT[-1]
    return DT

def DT_alpha_t_blend(dt_0,dt_1,t0,t1):
    DT = []
    t=t0
    if t1 != t0:
        while t <= t1:
            alpha = (t-t0)/(t1-t0)
            DT.append(dt_0 * (1-alpha) + dt_1 * alpha)
            t+=DT[-1]
    return DT

def plan_solver(data,args):
    if not ( ('Plans' in data and args.plan in data['Plans']) or args.vplan or args.vplan2 or args.fplan ):
        print
        print "Plan %s not found in data file %s" % (args.plan, args.file)
        print
        return None
    else:
        if args.seed:
            random.seed(args.seed)
        else:
            random.seed(0)
        start_time = clock_time.time()
        av_travel_time=0
        av_solve_time=0
        total_steps=0
        DT_start = None
        if args.vplan:
            minor_frame = args.vplan[0]
            major_frame = args.vplan[1]
            horizon = args.vplan[2]
            blend_frame = args.vplan[3]
            DT_start = args.vplan[4]
            DT_stop = args.vplan[5]
            t=0
            DT = []
            while t < minor_frame:
                DT.append(DT_start)
                t += DT[-1]
            DT += DT_alpha_t_blend(DT_start,DT_stop, 0, blend_frame)
            t = sum(DT)
            #DT.append(minor_frame + blend_frame - t)
            while t < major_frame:
                DT.append(DT_stop)
                t += DT[-1]
            plan =  {
                "label": "$\\Delta t=%f,%f$, $\\Pi=%f$, $\\pi=%f$" % (DT_start,DT_stop,major_frame,minor_frame),
                "minor_frame": minor_frame,
                "major_frame": major_frame,
                "horizon" : horizon,
                "blend_frame" : blend_frame,
                "N" : None,
                "DT_vari": [{ "DT": DT_start, "DT_vec": DT}] # "DT_vari": [{ "DT": DT_start, "start": 0.0, "stop": 0.5}, { "DT": DT_stop, "start": 0.5, "stop": 1.0}]

            }
        elif args.vplan2:
            minor_frame = args.vplan2[0]
            horizon = args.vplan2[1]
            N = args.vplan2[2]
            rate = args.vplan2[3]
            DT_start = args.vplan2[4]
            DT_stop = args.vplan2[5]
            DT = DT_alpha_n_blend(DT_start,DT_stop, N - (minor_frame / DT_start))
            major_frame = minor_frame + sum(DT)
            blend_frame = major_frame - minor_frame
            plan =  {
                "label": "$\\Delta t=%f,%f$, $\\Pi=%f$, $\\pi=%f$" % (DT_start,DT_stop,major_frame,minor_frame),
                "minor_frame": minor_frame,
                "major_frame": major_frame,
                "horizon" : horizon,
                "blend_frame" : None,
                "N" : N,
                "DT_vari": [{ "DT": DT_start, "DT_vec": DT}]

            }
        # elif args.vplan3:
        #     vplan3 = json.loads(args.vplan3)
        #     minor_frame = vplan3.get('minor_frame')
        #     horizon =  vplan3.get('major_frame')
        #     N = args.vplan2[2]
        #     rate = args.vplan2[3]
        #     DT_list = vplan3.get('DT_steps')
        #     DT_stop = args.vplan2[5]
        #     DT = DT_alpha_blend(DT_start,DT_stop, N - (minor_frame / DT_start))
        #     major_frame = minor_frame + sum(DT)
        #     blend_frame = major_frame - minor_frame
        #     plan =  {
        #         "label": "$\\Delta t=%f,%f$, $\\Pi=%f$, $\\pi=%f$" % (DT_start,DT_stop,major_frame,minor_frame),
        #         "minor_frame": minor_frame,
        #         "major_frame": major_frame,
        #         "horizon" : horizon,
        #         "blend_frame" : None,
        #         "N" : N,
        #         "DT_vari": [{ "DT": DT_start, "DT_vec": DT}]
        #
        #     }

        elif args.fplan:
            minor_frame = args.fplan[0]
            major_frame = args.fplan[1]
            horizon = args.fplan[2]
            DT_fixed = args.fplan[3]
            DT_start = DT_fixed
            plan =  {
                "label": "$\\Delta t=%f, $\\Pi=%f$, $\\pi=%f$" % (DT_fixed,major_frame,minor_frame),
                "minor_frame": minor_frame,
                "major_frame": major_frame,
                "horizon" : horizon,
                "DT_fixed": DT_fixed

            }
        else:
            plan = data['Plans'][args.plan]

        minor_frame = plan['minor_frame']
        major_frame = plan['major_frame']
        horizon = plan['horizon']
        label = plan['label']
        blend_frame=None
        print 'Plan:' ,plan
        if 'DT_fixed' in plan:
            DT = plan['DT_fixed']*args.DT_factor
            n_samples = int(major_frame / DT)
            DT_vari=None
        else:
            blend_frame=plan['blend_frame']
            DT_vari = plan['DT_vari']
            n_samples=plan['N']
            DT= DT_vari[0]['DT']*args.DT_factor
            data['DT_factor']=args.DT_factor

        for run in range(int(args.average)):
            print
            print '============ Run %d ==========' % (run + 1)
            print
            prev_step=None
            t0 = 0
            K=int(horizon/minor_frame)
            print 'Doing %d minor frames of %f over %f horizon ' % (K,minor_frame,horizon)
            epsilon = 1e-6
            for k in range(K):
                t1 = t0+major_frame
                if args.tune != None and k==int(args.tune[0][1]):

                    tune = True
                    tune_file = args.tune[0][0]
                else:
                    tune = False
                    tune_file=''
                if args.average and args.average==1:
                    run_index=None
                else:
                    run_index=run
                print
                print '------------ Run %d Frame %d ----------' % (run + 1, k + 1)
                print
                if args.seed == 0:
                    seed = 0
                else:
                    seed = random.randint(1,1e9)
                if milp_solver(data,t0=t0,t1=t1,n_samples=n_samples, DT_vari=DT_vari,minor_frame=minor_frame,major_frame=major_frame,
                               blend_frame=blend_frame,fixed_plan=None,nthreads=args.threads,timelimit=args.timelimit,
                               accuracy=args.accuracy,verbose=args.verbose,
                               label=label+' step %d' % k,
                               step=k,run=run_index,obj=args.obj,alpha_obj=args.alpha,beta_obj=args.beta,gamma_obj=args.gamma,DT_offset=args.DT_offset,
                               seed=seed,tune=tune,tune_file=tune_file,param=args.param,lost_time = args.lost_time, solver_model=args.solver_model,
                               no_assertion_fail=args.no_assertion_fail,no_warning=args.no_warning,buffer_input=args.buffer_input,exact=args.exact) is None:
                    return None
                t0+=minor_frame
                if run_index != None:
                    data_step = data['Out']['Run'][run]['Step']
                else:
                    data_step = data['Out']['Step']

                av_solve_time+=data_step[k]['solver_runtime']
                total_q_in = data_step[k]['total_q_in']
                total_q_out = data_step[k]['total_q_out']
                print 'total_q_in=',total_q_in
                print 'total_q_out=',total_q_out
                if total_q_in < epsilon and total_q_out < epsilon:
                    print 'No more traffic flow. Finished at %f in %d steps' % ((k + 1) * minor_frame, k + 1)
                    #del data_step[k]
                    # k -= 1
                    break
                    #print 'total_steps:',type(total_steps),total_steps
                    #print 'k:',type(k),k
            total_steps += (k + 1)

            K_horizon = (k + 1) * minor_frame
            K_steps = k + 1

            print 'Run %d Completed in %d Frames' % (run + 1, k + 1)
            print
            print '======== Generating final solution over frames ========'
            print


            if run_index != None:
                fixed_plan = data['Out']['Run'][run]['Fixed_Plan'] = dict()
            else:
                fixed_plan = data['Out']['Fixed_Plan'] = dict()
            DT = DT_start #args.DT_final
            minor_frame_n = int(minor_frame / DT)
            print 'minor_frame_n:',minor_frame_n
            fixed_plan['DT'] = [DT] * (K_steps * minor_frame_n)
            print 'k,minor_frame,K_horizon',k,minor_frame,K_horizon
            print 'DT',DT
            fixed_plan['t'] = list(numpy.arange(0,K_horizon,DT))
            # f, ax = plt.subplots(len(data['Lights'])*2, 1, sharex=True,figsize=(12,12))
            t0 = 0
            n = 0
            for k in range(K_steps):

                t1 = t0+minor_frame
                if run_index != None:
                    step_data = data['Out']['Run'][run]['Step'][k]
                else:
                    step_data = data['Out']['Step'][k]
                step_time = step_data['t']
                # for i in range(len(data['Lights'])):
                #     ax[i * 2].plot(step_data['t'][0:minor_frame_n],step_data[r'p_{%d,%d}' % (i,0)][0:minor_frame_n],'k:')
                #     ax[i * 2 + 1].plot(step_data['t'][0:minor_frame_n],step_data[r'd_{%d,%d}' % (i,0)][0:minor_frame_n],'k:')

                for i,l_i in enumerate(data['Lights']):
                    for j, _ in enumerate(l_i['p0']):
                        if r'p_{%d,%d}' % (i,j) not in fixed_plan:
                            fixed_plan[r'p_{%d,%d}' % (i,j)] = [0] * (K_steps * minor_frame_n)
                            fixed_plan[r'd_{%d,%d}' % (i,j)] = [0] * (K_steps * minor_frame_n)
                        fixed_plan[r'p_{%d,%d}' % (i,j)][n:n + minor_frame_n] = step_data[r'p_{%d,%d}' % (i,j)][0:minor_frame_n]
                        fixed_plan[r'd_{%d,%d}' % (i,j)][n:n + minor_frame_n] = step_data[r'd_{%d,%d}' % (i,j)][0:minor_frame_n]

                # while n < len(step_time) and t0 > step_time[n]: n+=1
                # while n < len(step_time) and step_time[n] <= t1:
                #     #ratio = int(step_data['DT'][n]/DT)
                #     DT  = step_data['DT'][n]
                #     #for dt_i in range(ratio):
                #     for i,l_i in enumerate(data['Lights']):
                #         for j, _ in enumerate(l_i['p0']):
                #             if r'p_{%d,%d}' % (i,j) not in fixed_plan:
                #                 fixed_plan[r'p_{%d,%d}' % (i,j)]=[]
                #                 fixed_plan[r'd_{%d,%d}' % (i,j)]=[]
                #             fixed_plan[r'p_{%d,%d}' % (i,j)].append(step_data[r'p_{%d,%d}' % (i,j)][n])
                #             fixed_plan[r'd_{%d,%d}' % (i,j)].append(step_data[r'd_{%d,%d}' % (i,j)][n])

                    # fixed_plan['DT'].append(DT)
                    # if n>0:
                    #     fixed_plan['t'].append(fixed_plan['t'][-1]+DT)
                    # else:
                    #     fixed_plan['t'].append(step_time[0])
                n += minor_frame_n
                t0 += minor_frame
            #print "FIXED_PLAN t:",fixed_plan['t']
            #print r'd_{%d,%d}=' % (0,0),fixed_plan[r'd_{%d,%d}' % (0,0)]
            if args.DT_final != None:
                DT_final = args.DT_final
            else:
                DT_final = fixed_plan['DT'][0]

            if milp_solver(data,t0=0,t1=K_horizon,n_samples=int(K_horizon/DT_final), fixed_plan=fixed_plan,nthreads=args.threads,
                   timelimit=args.timelimit,accuracy=args.accuracy,verbose=args.verbose,seed=args.seed,
                   label=label,step=None,run=run_index,obj=args.obj,alpha_obj=args.alpha,beta_obj=args.beta,gamma_obj=args.gamma,param=args.param,
                    lost_time = args.lost_time, solver_model = args.solver_model,no_assertion_fail=args.no_assertion_fail,no_warning=args.no_warning,
                           buffer_input=args.buffer_input,exact=args.sim_exact | args.exact) is None:
                return None
            # for i in range(len(data['Lights'])):
            #     ax[i * 2].plot(data['Out']['t'],data['Out'][r'p_{%d,%d}' % (i,0)],'k-')
            #     ax[i * 2 + 1].plot(data['Out']['t'],data['Out'][r'd_{%d,%d}' % (i,0)],'k-')
            # plt.xlim(0,30)
            # plt.show()
            if run_index != None:
                #print data['Out']['Run'][run].keys()
                #print data['Out'].keys()
                av_travel_time += data['Out']['Run'][run]['total_travel_time']
            else:
                av_travel_time += data['Out']['total_travel_time']

            solve_time = clock_time.time() - start_time
            if run_index != None:
                data['Out']['Run'][run]['solve_time'] = solve_time
            if args.nostepvars:
                if 'Run' in data['Out']:
                    for run_data in data['Out']['Run']:
                        for step in run_data['Step']:
                            rm_vars(step)
                if 'Step' in data['Out']:
                    for step in data['Out']['Step']:
                        rm_vars(step)

            solve_time = clock_time.time() - start_time
            print 'Total Plan Solve time so far: %s seconds' % solve_time
            data['Out']['solve_time'] = solve_time
            data['Out']['plan'] = plan
            data['Out']['DT_offset'] = args.DT_offset
            data['Out']['av_travel_time'] = av_travel_time / (run + 1)
            data['Out']['av_solve_time'] = av_solve_time / total_steps
            data['Out']['seed'] = args.seed
            write_file(data,args)

            #if args.average>1:
            #    if 'run' not in data: data['run']=[]
            #    data['run'].append(copy.deepcopy(data['results']))


        solve_time = clock_time.time() - start_time
        print 'Total Plan Solve time: %s seconds' % solve_time
        data['Out']['solve_time'] = solve_time
        data['Out']['plan'] = plan
        data['Out']['DT_offset'] = args.DT_offset
        data['Out']['av_travel_time'] = av_travel_time / args.average
        data['Out']['av_solve_time'] = av_solve_time / total_steps
        if args.novars:
            if 'Run' in data['Out']:
                for run_data in data['Out']['Run']:
                    for step in run_data['Step']:
                        rm_vars(step)
                    rm_vars(run)
            if 'Step' in data['Out']:
                for step in data['Out']['Step']:
                    rm_vars(step)
            rm_vars(data['Out'])
        print
        print 'Done.'
        print
        return data



def DT_final_solver(data,args):
    start_time = clock_time.time()
    data=milp_solver(data,t0=args.t0,t1=args.t1,n_samples=args.nsamples, fixed_plan=fixed,nthreads=args.threads,timelimit=args.timelimit,accuracy=args.accuracy,
                    verbose=args.verbose,
                    step=0,
                    obj=args.obj,alpha_obj=args.alpha,beta_obj=args.beta,gamma_obj=args.gamma,DT_offset=args.DT_offset,seed=args.seed,
                    no_warning=args.no_warning,buffer_input=args.buffer_input)

    DT = args.DT_final
    fixed_plan = data['Out']['Fixed_Plan'] = dict()
    fixed_plan['t'] = []
    fixed_plan['DT'] = []


    k=0
    t0=args.t0
    t1=args.t1



    step_data = data['Out']['Step'][k]
    step_time = step_data['t']

    n=0
    while n< len(step_time) and t0>step_time[n]: n+=1
    while n< len(step_time) and step_time[n]<t1:
        ratio = int(step_data['DT'][n]/DT)
        #print 'r=',ratio,
        for dt_i in range(ratio):
            for i,l_i in enumerate(data['Lights']):
                for j, _ in enumerate(l_i['p0']):
                    if r'p_{%d,%d}' % (i,j) not in fixed_plan:
                        fixed_plan[r'p_{%d,%d}' % (i,j)]=[]
                        fixed_plan[r'd_{%d,%d}' % (i,j)]=[]
                    fixed_plan[r'p_{%d,%d}' % (i,j)].append(step_data[r'p_{%d,%d}' % (i,j)][n])
                    fixed_plan[r'd_{%d,%d}' % (i,j)].append(step_data[r'd_{%d,%d}' % (i,j)][n])

            fixed_plan['DT'].append(DT)
            if n>0:
                fixed_plan['t'].append(fixed_plan['t'][-1]+DT)
            else:
                fixed_plan['t'].append(step_time[0])
        n+=1

    if milp_solver(data,t0=t0,t1=t1,n_samples=int((t1-t0)/DT), fixed_plan=data['Out']['Fixed_Plan'],nthreads=args.threads,
           timelimit=args.timelimit,accuracy=args.accuracy,verbose=args.verbose,
           step=None,obj=args.obj,alpha_obj=args.alpha,beta_obj=args.beta,gamma_obj=args.gamma,
           no_warning=args.no_warning,buffer_input=args.buffer_input) is None:
        return None


    solve_time = clock_time.time() - start_time
    print 'Total Plan Solve time: %s seconds' % solve_time
    data['Out']['solve_time'] = solve_time
    print (data['Out']).keys()
    return data

def bootstrap_solver(data,args,average_runs=1,boot_accuracy=None):
    if args.seed:
        random.seed(args.seed)
    else:
        random.seed(0)
    av_travel_time=0
    av_solve_time=0
    start_time = clock_time.time()
    for run in range(average_runs):
        base_N = args.nsamples
        for i in range(args.bootstrap+1):
            print 'base_N=',base_N
            base_N *= 2
        run_start_time = clock_time.time()
        base_N = args.nsamples
        accuracy = args.accuracy
        #prev_run = None
        data_itr = copy.deepcopy(data)
        if average_runs==1:
            run_index=None
        else:
            run_index=run

        for k in range(args.bootstrap + 1):
            print
            print '------------ Run %d Frame %d ----------' % (run + 1, k + 1)
            print
            if k == args.bootstrap:
                mip_start = 'final'
            else:
                mip_start = 'step'
            if args.seed == 0:
                seed = 0
            else:
                seed = random.randint(1,1e9)
            if boot_accuracy is not None and k < len(boot_accuracy) - 1:
                accuracy = boot_accuracy[k]
            else:
                accuracy = args.accuracy

            if milp_solver(data,t0=args.t0,t1=args.t1,dt0=args.dt0,dt1=args.dt1,n_samples=int(base_N),DT_file=args.DT_file, fixed_plan=fixed,nthreads=args.threads,
                timelimit=args.timelimit,accuracy=accuracy,
                verbose=args.verbose,step=k,run=run_index,
                obj=args.obj,alpha_obj=args.alpha,
                beta_obj=args.beta,gamma_obj=args.gamma,DT_offset=args.DT_offset,seed = seed,
                tune = tune,tune_file=tune_file,param=args.param,in_weight=args.in_weight,mip_start=mip_start,no_assertion_fail=args.no_assertion_fail,
                lost_time = args.lost_time, solver_model = args.solver_model,no_warning=args.no_warning,buffer_input=args.buffer_input,exact=args.exact) is None:
                return None
            #prev_run = copy.deepcopy(data_itr)
            base_N *= 2
            write_file(data, args)

        if boot_accuracy is not None:
            base_N *= 0.5
            final_accuracy_step = boot_accuracy[-1]
            final_accuracy = accuracy - final_accuracy_step
            while final_accuracy > args.accuracy:
                if milp_solver(data, t0=args.t0, t1=args.t1, dt0=args.dt0, dt1=args.dt1, n_samples=int(base_N),
                               DT_file=args.DT_file, fixed_plan=fixed, nthreads=args.threads,
                               timelimit=args.timelimit, accuracy=accuracy,
                               verbose=args.verbose, step=k, run=run_index,
                               obj=args.obj, alpha_obj=args.alpha,
                               beta_obj=args.beta, gamma_obj=args.gamma, DT_offset=args.DT_offset, seed=seed,
                               tune=tune, tune_file=tune_file, param=args.param, in_weight=args.in_weight,
                               mip_start=data['Out']['Run'][run], no_assertion_fail=args.no_assertion_fail,
                               lost_time=args.lost_time, solver_model=args.solver_model, no_warning=args.no_warning,
                               buffer_input=args.buffer_input,exact=args.exact) is None:
                    return None
                write_file(data, args)
                final_accuracy -= final_accuracy_step
                k += 1
                #
        #data = data_itr

        run_solve_time = clock_time.time() - run_start_time

        print 'Total Run Solve time: %s seconds' % run_solve_time
        print 'Run %d Completed in %d Frames' % (run + 1, k + 1)
        if run_index != None:
            #print data['Out']['Run'][run].keys()
            #print data['Out'].keys()
            av_travel_time += data['Out']['Run'][run]['total_travel_time']
            data['Out']['Run'][run]['solve_time'] = run_solve_time
        else:
            av_travel_time += data['Out']['total_travel_time']
            data['Out']['solve_time'] = run_solve_time
        av_solve_time += run_solve_time

        data['Out']['av_travel_time'] = av_travel_time / (run + 1)
        data['Out']['av_solve_time'] = av_solve_time / (run + 1)
        file_start_time = clock_time.time()
        write_file(data,args)
        file_write_time = clock_time.time() - file_start_time
        print "File write time: % seconds" % file_write_time
        #print
        #print '======== Generating final solution over frames ========'
        #print
    solve_time = clock_time.time() - start_time

    data['Out']['solve_time'] = solve_time
    data['Out']['av_travel_time'] = av_travel_time / (average_runs)
    data['Out']['av_solve_time'] = av_solve_time / (average_runs)
    print 'Average Bootstrap Solve time: %s seconds' % data['Out']['av_solve_time']
    print 'Total Bootstrap Solve time: %s seconds' % solve_time
    return data

def sim_solver(data,fixed_files, loaded_files, args):
    if 'Out' in data:
        data['Out'] = None
    for k,fixed_data in enumerate(fixed_files):
        if 'Out' in fixed_data:
            fixed_data = fixed_data['Out']
            if 'Run' not in fixed_data:
                run_data = [fixed_data]
                run_index = None
            else:
                run_data = fixed_data['Run']
                run_index = True
            runs = len(run_data)
            av_travel_time = 0
            for run in range(runs):
                print
                print '------------ Run %d ----------' % (run + 1)
                print
                if args.t0 is None or args.t1 is None or args.nsamples is None:
                    t0 = run_data[run]['t'][0]
                    t1 = run_data[run]['t'][-1]
                    nsamples = run_data[run]['N']
                else:
                    t0 = args.t0
                    t1 = args.t1
                    nsamples = args.nsamples
                if run_index is not None:
                    run_index = run
                data = milp_solver(data, t0=t0, t1=t1, dt0=args.dt0, dt1=args.dt1,
                                   n_samples=nsamples, DT_file=args.DT_file, fixed_plan=run_data[run],
                                   nthreads=args.threads, run=run_index,
                                   timelimit=args.timelimit, accuracy=args.accuracy,
                                   verbose=args.verbose, obj=args.obj, alpha_obj=args.alpha,
                                   beta_obj=args.beta, gamma_obj=args.gamma, DT_offset=args.DT_offset,
                                   seed=args.seed, param=args.param, in_weight=args.in_weight,
                                   no_assertion_fail=args.no_assertion_fail, lost_time=args.lost_time,
                                   solver_model=args.solver_model, no_warning=args.no_warning,
                                   buffer_input=args.buffer_input, exact=args.exact | args.sim_exact)
                if run_index is not None:
                    av_travel_time += data['Out']['Run'][run]['total_travel_time']
                    data_run = data['Out']['Run'][run_index]
                else:
                    av_travel_time += data['Out']['total_travel_time']
                    data_run = data['Out']
                data['Out']['av_travel_time'] = av_travel_time / (run + 1)
                if 'Step' in run_data[run]:
                    data_run['Step'] = [dict()]
                    data_run['Step'][0]['N'] = run_data[run]['Step'][0]['N']
                    data_run['Step'][0]['t'] = run_data[run]['Step'][0]['t']

        else:
            print 'File %s does not containt a solution to use as a signal plan for simulation' % args.fixed
        if args.out is not None:
            if len(args.out.split('.')) == 1:
                out_file = loaded_files[k].split('.')[0] + '_' + args.out + '.' + loaded_files[k].split('.')[1]
            else:
                out_file = args.out
            print out_file
            write_file(data, args, out_file=out_file)
    return None

def write_file(data, args, out_file=None):
    if out_file is None:
        if args.out is None:
            out_file = 'out_' + args.file
        else:
            out_file=args.out
    if not args.novars:
        if args.zip:
            out_file_zip = os.path.splitext(out_file)[0]+".zip"
            zf = zipfile.ZipFile(out_file_zip, mode='w',compression=zipfile.ZIP_DEFLATED)
            zf.writestr(out_file, json.dumps(data))
            zf.write('qtm_solve.py')
            if 'JOB_ID' in os.environ and 'JOB_NAME' in os.environ:
                job_id = os.environ['JOB_ID']
                job_name = os.environ['JOB_NAME']
                zf.write(job_name + '.o' + job_id)
            zf.close()
        else:
            f = open(out_file,'w')
            json.dump(data,f)
            f.close()
    if args.meta or args.novars:
        if 'Run' in data['Out']:
            for run in data['Out']['Run']:
                for step in run['Step']:
                    rm_vars(step)
                rm_vars(run)
        if 'Step' in data['Out']:
            for step in data['Out']['Step']:
                rm_vars(step)
        rm_vars(data['Out'])
        f = open(out_file+'.meta','w')
        json.dump(data,f)
        f.close()

def open_data_file(file):
    if os.path.isfile(file):
        if zipfile.is_zipfile(file):
            path,file_json = os.path.split(os.path.splitext(file)[0]+".json")
            zf = zipfile.ZipFile(file)
            json_file = zf.read(file_json)
            data = json.loads(json_file)
            zf.close()
        else:
            f = open(str(file),'r')
            data  = json.load(f)
            f.close()
    else:
        print 'file not found:',file
        data = None
    return data

def read_files(plot_file, return_files_opened=False):
    gc.disable()
    files = []
    if os.path.isfile(plot_file):
        path,name = os.path.split(plot_file)
        type = name.split('.')[-1]
        if type == 'json' or type == 'zip':
            files.append(plot_file)
        else:
            if len(path) > 0: path += '/'
            f = open(str(plot_file),'r')
            for line in f:
                fields = line.split(' ')
                if len(fields) > 0 and len(fields[0].strip()) > 0:
                    files.append(path+fields[0].strip())
            f.close()
        data_files = []
        files_opened = []
        for file in files:
            data = open_data_file(file)
            if data is not None:
                data_files.append(data)
                files_opened.append(file)
        gc.enable()
        gc.collect()
        if return_files_opened:
            return data_files,files_opened
        else:
            return data_files
    else:
        print 'unable to open file:',plot_file



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="the model file to solve")
    parser.add_argument("--t0", help="start time",type=int)
    parser.add_argument("--t1", help="end time",type=int)
    parser.add_argument("--dt0", help="start time step",type=float)
    parser.add_argument("--dt1", help="end time step",type=float)
    parser.add_argument("-t", "--threads", help="number of threads",type=int,default=0)
    parser.add_argument("-n", "--nsamples", help="number of sample points",type=int)
    parser.add_argument("-o", "--out", help="save the solution as OUT")
    parser.add_argument("--verbose", help="log output to console", action="store_true", default=False)
    parser.add_argument("--timelimit", help="time limit to run solver in seconds",type=int,default=0)
    parser.add_argument("--accuracy", help="percentage accuracy of objective value to stop solver",type=float, default=0)
    parser.add_argument("--fixed", help="file to use for a fixed signal plan")
    parser.add_argument("--plan", help="Plan to use in FILE for a k-step solution")
    parser.add_argument("--vplan", help="Variable plan MINOR MAJOR HORIZON BLEND DT_START DT_END ,for a k-step solution",nargs=6,type=float)
    parser.add_argument("--vplan2", help="Variable plan MINOR HORIZON N RATE DT_START DT_END ,for a k-step solution",nargs=6,type=float)
    parser.add_argument("--fplan", help="Fixed Plan with MINOR MAJOR HORIZON times, DT for a k-step solution",nargs=4,type=float)
    parser.add_argument("--average", help="Average over N runs",type=int,default=1)
    parser.add_argument("--DT_factor", help="multiplier to modify the DT used in the plan",type=float,default=1.0)
    parser.add_argument("--DT_offset", help="initial offset for DT",type=float,default=0.0)
    parser.add_argument("--DT_final", help=" DT to use in the final step of plan",type=float)
    parser.add_argument("--DT_file", help="Use DT values defined in file", action="store_true", default=False)
    parser.add_argument("--alpha", help="Obj function alpha weight",type=float,default=1.0)
    parser.add_argument("--beta", help="Obj function beta weight",type=float,default=0.001)
    parser.add_argument("--gamma", help="Obj function gamma weight",type=float,default=0.0001)
    parser.add_argument("--obj", help="Obj function to use: OLD, NEW",default='MAX_OUT')
    parser.add_argument("--seed", help="Set the random seed",type=int,default=0)
    parser.add_argument("--tune", help="Run grbtune on the model at step TUNE",action='append',nargs='*',type=str)
    parser.add_argument("--param", help="Load a Gurobi parameter prm file")
    parser.add_argument("--nostepvars", help="dont store each steps variables in the results",action="store_true", default=False)
    parser.add_argument("--novars", help="dont store any variables in the results",action="store_true", default=False)
    parser.add_argument("--meta", help="also store a meta file without variabless",action="store_true", default=False)
    parser.add_argument("--zip", help="Compress the results file",action="store_true", default=False)
    parser.add_argument("--debug", help="output debug messages", action="store_true", default=False)
    parser.add_argument("--fixed_cycle", help="Fix the cycle time across all cycles per light", action="store_true", default=False)
    parser.add_argument("--fixed_phase", help="Fix each phase time across all cycles per light", action="store_true", default=False)
    parser.add_argument("--no_transit", help="turn off tranists in list or all transits if no parameters listed", nargs='*')
    parser.add_argument("--in_weight", help="weight any input flow rates weights with WEIGHT", type=float,default=1.0)
    parser.add_argument("--Q_IN_limit", help="limit in flow weights to Q_IN ", action="store_true", default=False)
    parser.add_argument("--bootstrap", help="iterativly solve for fixed DT using N iteratations of MIP start bootstraping ", type=int)
    parser.add_argument("--no_assertion_fail", help="Do not fail on assertion errors", action="store_true", default=False)
    parser.add_argument("--no_warning", help="Do not warn about taffic withholding fails", action="store_true", default=False)
    parser.add_argument("--lost_time", help="lost_time per phase", type=float,default=0.0)
    parser.add_argument("--solver_model", help="Solver traffic flow model to use (QTM or CTM)", default="QTM")
    parser.add_argument("--buffer_input", help="buffer all input queues to prevent spill back impeding inflow", action="store_true", default=False)
    parser.add_argument("--boot_accuracy", help="list of MIP gap accuracies for each step", nargs='+',type=float )
    parser.add_argument("--exact", help="use exact formulation for flow contraints", action="store_true", default=False)
    parser.add_argument("--sim_exact", help="use exact formulation for flow contraints in simulation", action="store_true", default=False)

    args = parser.parse_args()
    if args.debug: DEBUG = True
    print 'Gurobi Version:','.'.join(map(str,gurobi.version()))
    print 'CPU:', get_processor_name()
    # min2_test(2,3)
    # min2_test(4,1)
    # min2_test(5,5)
    # min2_test(0,0)
    # min2_test(0,6)
    # min2_test(6,0)
    # min2_test(6, -1)
    # min2_test(-5, -1)
    # min2_test(-5, -10)
    # min2_test(-8, 0)
    # min2_test(0, -7)
    # min2_test(-15, -15)
    # f = open(args.file,'r')
    data = open_data_file(args.file)
    # f.close()

    if args.out:
        data['out_filename']= args.out
    else:
        data['out_filename']= args.file

    if args.fixed:
        # f = open(args.fixed,'r')
        fixed_files,loaded_files = read_files(args.fixed,return_files_opened=True)
        data = sim_solver(data,fixed_files, loaded_files, args)
        # f.close()

    elif args.plan or args.vplan or args.vplan2 or args.fplan:
        data=plan_solver(data,args)
    elif args.DT_final and not args.plan:
        DT_final_solver(data,args)
    else:
        if args.tune != None:
            tune=True
            tune_file = args.tune[0][0]
        else:
            tune=False
            tune_file = ''
        if args.bootstrap is None:

            data=milp_solver(data,t0=args.t0,t1=args.t1,dt0=args.dt0,dt1=args.dt1,n_samples=args.nsamples,DT_file=args.DT_file, fixed_plan=None,nthreads=args.threads,
                    timelimit=args.timelimit,accuracy=args.accuracy,
                    verbose=args.verbose,obj=args.obj,alpha_obj=args.alpha,
                    beta_obj=args.beta,gamma_obj=args.gamma,DT_offset=args.DT_offset,seed = args.seed,
                    tune = tune,tune_file=tune_file,param=args.param,in_weight=args.in_weight,no_assertion_fail=args.no_assertion_fail, lost_time = args.lost_time,
                    solver_model = args.solver_model,no_warning=args.no_warning, buffer_input=args.buffer_input,exact=args.exact)
        else:
            data = bootstrap_solver(data,args,average_runs=args.average,boot_accuracy = args.boot_accuracy)



    if data is not None:
        write_file(data,args)
        # out_file = 'out_'+args.file
        # if args.out:
        #     out_file=args.out
        # if not args.novars:
        #     if args.zip:
        #         out_file_zip = os.path.splitext(out_file)[0]+".zip"
        #         zf = zipfile.ZipFile(out_file_zip, mode='w',compression=zipfile.ZIP_DEFLATED)
        #         zf.writestr(out_file, json.dumps(data))
        #         zf.close()
        #     else:
        #         f = open(out_file,'w')
        #         json.dump(data,f)
        #         f.close()
        # if args.meta or args.novars:
        #     if 'Run' in data['Out']:
        #         for run in data['Out']['Run']:
        #             for step in run['Step']:
        #                 rm_vars(step)
        #             rm_vars(run)
        #     if 'Step' in data['Out']:
        #         for step in data['Out']['Step']:
        #             rm_vars(step)
        #     rm_vars(data['Out'])
        #     f = open(out_file+'.meta','w')
        #     json.dump(data,f)
        #     f.close()

