from __future__ import division
import matplotlib.pyplot as pl
import matplotlib as mp
import matplotlib.image as mpimg
from matplotlib.patches import Arc,Arrow,Circle
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.collections import LineCollection
import numpy as np
import ujson as json
import sys
import argparse
import os
import os.path
import numpy as np
import scipy.interpolate as interp
import math as math
import zipfile
import zlib
import pandas as pd
from IPython.display import display
import time as clock_time
import gc

def find_paths(data):
    paths = []
    for flow in  data["Flows"].keys():
        f = flow.split('_')
        q1 = int(f[0])
        q2 = int(f[1])
        found_q1 = False
        found_q2 = False
        p1 = None
        p2 = None
        for p in paths:
            if q1 in p:
                found_q1 = True
                p1 = p

            if q2 in p:
                found_q2 = True
                p2 = p

        if found_q1 and found_q2:
            if p1 == p2:
                print "Error! queue %d->%d already added!" % (q1,q2)
            else:
                paths.remove(p2)
                p1 += p2
        elif found_q1:
            p1.insert(p1.index(q1)+1,q2)
        elif found_q2:
            p2.insert(p2.index(q2),q1)
        else:
            paths.append([q1,q2])
        #print paths
    return paths


def calc_total_stops(data,results):
    Queues = data['Queues']
    time=results['t']
    stops=0
    for i,q in enumerate(Queues):
        for n,t in enumerate(time[1:-1]):
            stops+=abs(results['q_%d' %i ][n] - results['q_%d' %i ][n-1])
    return 0.5 * stops

def calc_total_travel_time(data,results):
    Queues = data['Queues']
    time=results['t']
    sum_in=0
    sum_out=0
    for i,q in enumerate(Queues):
        for n,t in enumerate(time):

            if Queues[i]['Q_IN'] > 0:
                sum_in+=(t*results['q_{%d,in}' %i ][n])
            if Queues[i]['Q_OUT'] > 0:
                sum_out+=(t*results['q_{%d,out}' %i ][n])
    return sum_out-sum_in

def calc_total_traffic(data,results,lanes):

    total_in_flow = 0
    for lane in lanes:
        in_flow = sum(results['q_{%d,in}' % lane[0]])
        total_in_flow+=in_flow

    return total_in_flow

def calc_free_flow_travel_time(data,results,lanes):
    queue = data['Queues']
    lane_free_flow_travel_time = []
    total_in_flow = 0
    for lane in lanes:
        q_delay = 0
        in_flow = sum(results['q_{%d,in}' % lane[0]])
        #print '%d in_flow' % lane[0],in_flow
        total_in_flow+=in_flow
        for i in lane:
            q_delay += queue[i]['Q_DELAY']
        lane_free_flow_travel_time.append(q_delay*in_flow)
    #print total_in_flow
    return sum(lane_free_flow_travel_time)

def calc_total_free_flow_travel_time(data,results):
    total_free_flow_travel_time = 0
    for queue in data['Queues']:
        total_free_flow_travel_time += queue['Q_DELAY'] * args.time_factor
    return total_free_flow_travel_time


def calc_in_flow_duration(data,results):
    Queues = data['Queues']
    time=results['t']
    max_time = 0
    EPSILON = 1e-6
    for i,queue in enumerate(Queues):
        if queue['Q_IN'] > 0:
            for n,q_in in enumerate(results['q_{%d,in}' % i]):
                if q_in > EPSILON and time[n] > max_time:
                    max_time = time[n]
    return max_time

def calc_delay(data, results, queues=[], dp=6, dt=1):

    Queues = data['Queues']
    time=results['t']
    cumu_in = []
    cumu_out= []
    cumu_delay=[]
    in_q=[]
    out_q=[]
    q_delay=0
    EPSILON = 1e-6

    if not queues or len(queues) == 0:
        for i,q in enumerate(Queues):
            if Queues[i]['Q_IN'] > 0:
                in_q.append(results['q_{%d,in}' %i ])

            if Queues[i]['Q_OUT'] > 0:
                out_q.append(results['q_{%d,out}' %i ])
    else:
        in_q.append(results['q_{%d,in}' % int(queues[0]) ])

        out_q.append(results['q_{%d,out}' % int(queues[-1]) ])
        for i in queues:
            q_delay+=Queues[i]['Q_DELAY']


    for i,t in enumerate(time):
        if i==0:
            cumu_in.append(0)
            cumu_out.append(0)

        else:
            cumu_in.append(cumu_in[-1])
            cumu_out.append(cumu_out[-1])

            for q in in_q:
                cumu_in[i] += q[i]
                #if abs(cumu_in[i - 1] - cumu_in[i]) < EPSILON:
                #    cumu_in[i] = cumu_in[i - 1]

            for q in out_q:
                cumu_out[i]+=q[i]
                #if abs(cumu_out[i - 1] - cumu_out[i]) < EPSILON:
                #    cumu_out[i] = cumu_out[i - 1]

    cumu_in = np.array(cumu_in)
    cumu_out = np.array(cumu_out)


    cumu_in = np.around(cumu_in,dp) #cumu_in[cumu_in < EPSILON] = 0
    cumu_out = np.around(cumu_out,dp) #cumu_out[cumu_out < EPSILON] = 0
    n0_in=0
    while n0_in + 1 < len(cumu_in) and cumu_in[n0_in] == 0 and cumu_in[n0_in + 1] == 0: n0_in += 1
    n1_in = len(cumu_in) - 1
    while n1_in > 0 and abs(cumu_in[n1_in - 1] - cumu_in[n1_in]) < EPSILON: n1_in -= 1

    icumu_in_f = interp.interp1d(cumu_in[n0_in:], time[n0_in:], assume_sorted = True, bounds_error = False, fill_value = time[n1_in])
    icars = np.linspace(cumu_in[n0_in], max(cumu_in), (max(cumu_in) + 1) * 20, endpoint=True)
    icars_in = icumu_in_f(icars)

    n0_out=0
    while n0_out + 1 < len(cumu_out) and cumu_out[n0_out] == 0 and cumu_out[n0_out + 1] == 0: n0_out += 1
    n1_out = len(cumu_out) - 1
    while n1_out > 0 and abs(cumu_out[n1_out - 1] - cumu_out[n1_out]) < EPSILON: n1_out -= 1

    icumu_out_f = interp.interp1d(cumu_out[n0_out:], time[n0_out:], assume_sorted = True, bounds_error = False, fill_value = time[n1_out])
    icars = np.linspace(cumu_out[n0_out], max(cumu_out), (max(cumu_out) + 1) * 20, endpoint=True)
    icars_out = icumu_out_f(icars)

    cumu_cars_in = cumu_in[n0_in:n1_in + 1]
    cumu_cars_out = cumu_cars_in

    tcars_in = np.copy(icumu_in_f(cumu_cars_in))
    tcars_out = np.copy(icumu_out_f(cumu_cars_out))
    #print len(tcars_in),len(tcars_out)
    #tcars_in.resize(max(len(tcars_in),len(tcars_out)))
    #tcars_out.resize(max(len(tcars_in),len(tcars_out)))

    trimmed_cumu_delay = tcars_out - tcars_in - q_delay

    trimmed_cumu_delay[trimmed_cumu_delay < 0] = 0
    cumu_delay = np.zeros(len(time))
    cumu_delay[n0_in:n0_in+len(trimmed_cumu_delay)] = trimmed_cumu_delay

    #pl.figure()
    #pl.plot(trimmed_cumu_delay,'rx-')
    cumu_cars_in = np.linspace(dt, max(cumu_in), max(cumu_in)/dt, endpoint=True)
    #print cumu_cars_in
    cumu_cars_out = cumu_cars_in
    tcars_in = np.copy(icumu_in_f(cumu_cars_in))
    tcars_out = np.copy(icumu_out_f(cumu_cars_out))

    delay_by_car = tcars_out - tcars_in - q_delay
    delay_by_car[delay_by_car < 0] = 0

    #pl.plot(delay_by_car,'.-')
    #pl.show()
    #print tcars_in,tcars_out
    #print len(trimmed_cumu_delay),len(delay_by_car)
    #cumu_delay = np.zeros(len(time))
    #cumu_delay[n0_in:n0_in+len(delay_by_car)] = delay_by_car
    #print delay_by_car
    #print n0_in,cumu_in[:100]
    #print n0_out,cumu_out[:100]

    #print tcars_in[:100]
    #print tcars_out[:100]
    #print cumu_delay[:100]
    #print cumu_delay
    return time,cumu_in,cumu_out,cumu_delay.tolist(),delay_by_car.tolist(),trimmed_cumu_delay.tolist()

def trim_delay(cumu_data):
    """
    :param cumu_data: tuple of cumulative data=(time vector,cumulative arrivals,cumulative depatures,delay)
    :return: a delay curve trimmed of leading and trailing zero's
    """
    cumu_in = cumu_data[1]
    #print cumu_in
    cumu_delay = cumu_data[4]
    EPSILON = 1e-6
    j = 0
    while j+1 < len(cumu_in) and (cumu_in[j+1] - cumu_in[j]) < EPSILON: j += 1
    in_start = j
    j = len(cumu_in) - 2
    #print (cumu_in[j] - cumu_in[j+1])
    while j > 0  and (cumu_in[j+1] - cumu_in[j]) < EPSILON:
        #print (cumu_in[j] - cumu_in[j+1])
        j -= 1
    #print
    in_end = j+1
    #print in_start,in_end,cumu_delay[0:in_start],cumu_delay[in_end+1:-1]
    #print '-----'
    #print cumu_delay[in_start:in_end+1]
    #print '*****'
    return cumu_delay[in_start:in_end+1]


def calc_histogram_delay(data, step, width, queues=[],oversample=10):


    results = data['Out']


    if step != None:
        if 'Step' in results:
            results = data['Out']['Step'][step]
            label = results['label']
    time = results['t']
    total_time = time[-1] - time[0]
    N = int(total_time / width)
    bins = [0 for x in range(N)]
    bin_ranges = [width*x for x in range(N+1)]

    M = N * oversample
    Q = 1
    if not queues:
        queues = [range(len(data['Queues']))]
        Q = len(queues)

    for q in queues:

        cumu_time,cumu_in,cumu_out,cumu_delay,delay_by_car,delay = calc_delay(data,step, q)
        in_start=0
        in_end=1
        for j in range(len(cumu_in)):
            if cumu_in[j] > cumu_in[in_end]: in_end=j
        j=0
        while cumu_in[in_start+1]<1e-6 and in_start<in_end-1: in_start+=1


        t=time[in_start]
        dt = (time[in_end] - time[in_start])/M

        k=in_start
        while t<time[in_end]:
            alpha = (t- time[k]) / (time[k+1] - time[k])
            delay = (1-alpha) * cumu_delay[k] + alpha * cumu_delay[k+1]
            j=0
            while delay>bin_ranges[j+1] and j<N: j+=1
            w = 1/((cumu_in[-1]) /(bin_ranges[j+1]-bin_ranges[j]))
            bins[j]+=1/oversample
            t+=dt
            if t>time[k+1]: k+=1
    return bins,bin_ranges

def plot_delay_gt(data, step, width, threshold, queues=[],plots=None,line_style=['-'],colours='krgb'):
    pl.clf()
    fig, ax = pl.subplots(nrows=1, ncols=1, sharex=True, sharey=False)
    fig.set_size_inches(15, 7)
    titles=[]

    i=0
    c_i=0

    if plots == None: plots = [1]
    offset=0
    for num_files in plots:
        plot_data = dict()
        plot_label=''
        for file in range(num_files):


            d=data[offset+file]
            title = d['Title']
            titles.append(d['Title'])
            results = d['Out']
            label =  d['Out']['label']
            if 'Step' in results:
                N = len(d['Out']['Step'][0]['t'])-1
            else:
                N = len(results['t'])-1
            if step != None:
                if 'Step' in results:
                    results = d['Out']['Step'][step]
                    label = results['label']
            if len(plot_label)==0:
                plot_label = '$'+label.split('$')[1]+'$'

            time = results['t']
            total_time = time[-1] - time[0]
            x_range = 0
            bins,bin_ranges = calc_histogram_delay(d, step, width, queues,10)
            total = sum(bins)
            #bins = [x/total /(bin_ranges[j+1]-bin_ranges[j]) for j,x in enumerate(bins)]
            above = 0
            below = 0
            for j,x in enumerate(bins):
                bins[j] = x * (bin_ranges[j+1]-bin_ranges[j])
                if bin_ranges[j]>threshold:
                    above+=bins[j]
                else:
                    below+=bins[j]
            plot_data[N]=above
        X = sorted(plot_data)
        Y = [plot_data[x] for x in X]
        ax.plot(X,Y,c=colours[c_i], label=plot_label)
        if i+1 < len(line_style): i += 1
        if c_i+1 < len(colours): c_i += 1
        offset+=num_files
    #ax.set_xlim(0, x_range)
    ax.grid()
    ax.set_xlabel('N (Samples)')
    ax.set_ylabel('Number of vehicles delayed > %0.8g' % threshold)
    if not args.no_legend:
        ax.legend(loc='best')

    pl.title('Delay > %0.1g Histogram for Queues %s' % (threshold,', '.join([str(q) for q in queues])) )


def plot_delay_histogram(data, step, width, queues=[],line_style=['--'],colours='krgb',args=None):
    pl.clf()
    fig, ax = pl.subplots(nrows=1, ncols=1, sharex=True, sharey=False)
    fig.set_size_inches(15, 7)
    titles=[]

    i=0
    c_i=0

    for d in data:
        title = d['Title']
        titles.append(d['Title'])
        results = d['Out']
        label = d['Out']['label']

        if step != None:
            if 'Step' in results:
                results = d['Out']['Step'][step]
                label = results['label']
        time = results['t']
        total_time = time[-1] - time[0]
        x_range = 0
        bins,bin_ranges = calc_histogram_delay(d, step, width, queues,10)
        total = sum(bins)
        for j,x in enumerate(bins):
            bins[j] = x *(bin_ranges[j+1]-bin_ranges[j])
            if bins[j]>1e-5 and x_range<bin_ranges[j+1]:
                if j<len(bin_ranges)-2:
                    x_range=bin_ranges[j+2]
                else:
                    x_range=bin_ranges[j+1]
        #bins = [x/total /(bin_ranges[j+1]-bin_ranges[j]) for j,x in enumerate(bins)]
        ax.plot(bin_ranges[:-1],bins,c=colours[c_i], linestyle=line_style[i], label=label)
        if i+1 < len(line_style): i += 1
        if c_i+1 < len(colours): c_i += 1
    #ax.set_xlim(0, x_range)
    ax.grid()
    ax.set_xlabel('Delay (sec)')
    ax.set_ylabel('Frequency')
    if args.x_limit != None:
        ax.set_xlim(args.x_limit[0], args.x_limit[1])
    if args.y_limit != None:
        ax.set_ylim(args.y_limit[0], args.y_limit[1])
    if not args.no_legend:
        ax.legend(loc='best')

    pl.title('Delay Histogram for Queues %s' % ', '.join([str(q) for q in queues]) )

def label_distance(theta,i):
    dx = 0
    dy = 0
    if theta > 155 or theta < -155: # Vertical down
        if i>9: dx = -3
        else: dx = 3
    elif theta > -25 and theta < 25: # Vertical up
        dx = -13
    elif theta > -115 and theta < -65: # horizontal left
        dy = 10
    elif theta > 65 and theta < 115: # horzontal right
        dy = -6
    else: # Default
        dx =  -7
    return dx,dy
def plot_circle_label(ax,label,x,y,r):
    p = Circle((x,y), r,ec='k',fc='w')
    ax.add_patch(p)
    ax.text(x-2,y-2,label,fontsize=10,color='k')

def plot_network_figure(data,figsize=None,type='arrow',index_label_base=0,delay=False,debug=False):

    fig, ax = pl.subplots(nrows=1, ncols=1, sharex=True, sharey=False)

    green_red = LinearSegmentedColormap('green_red', {'red': ((0.0, 0.0, 0.0),
                                                            (0.5, 1.0, 1.0),
                                                          (1.0, 1.0, 1.0)),
                                                'green': ((0.0, 1.0, 1.0),
                                                          (0.5, 1.0, 1.0),
                                                          (1.0, 0.0, 0.0)),
                                                'blue':  ((0.0, 0.0, 0.0),
                                                          (1.0, 0.0, 0.0))})

    black_green_red = LinearSegmentedColormap('black_green_red', {'red': ((0.0, 0.0, 0.0),
                                                            (0.5, 1.0, 1.0),
                                                          (1.0, 1.0, 1.0)),
                                                'green': ((0.0, 0.0,0.0),
                                                          (0.1, 1.0, 1.0),
                                                          (0.5, 1.0, 1.0),
                                                          (1.0, 0.0, 0.0)),
                                                'blue':  ((0.0, 0.0, 0.0),
                                                          (1.0, 0.0, 0.0))})

    mp.cm.register_cmap('green_red',green_red)
    mp.cm.register_cmap('black_green_red',black_green_red)

    cmap_name = args.colormap
    gamma = args.gamma

    cmap = pl.get_cmap(cmap_name)
    cmap.set_gamma(gamma)

    Z = [[0,0],[0,0]]
    levels = range(0,110,10)
    CS3 = pl.contourf(Z, levels, cmap=cmap)
    pl.clf()
    pl.close('all')
    cNorm  = mp.colors.Normalize(vmin=0, vmax=1)
    scalarMap = mp.cm.ScalarMappable(norm=cNorm,cmap=cmap)

    #fig.set_size_inches(10, 5)

    cNorm  = mp.colors.Normalize(vmin=0, vmax=1)
    scalarMap = mp.cm.ScalarMappable(norm=cNorm,cmap=cmap)


    line_width = 1
    tail_width = 0
    head_width = 5
    r=15 # radius of intersection nodes
    label_space=15 # label spacing from line
    d=5 # distance to space two edges that share a pair of nodes
    width = 3 # width of bar
    track_width = 2 # width of track
    track_spacing = 5 # spacing between sleepers along track
    lx = 3 # light label x offset
    ly = 3 # light label y offset
    line_color = 'k'
    edge_color = 'k'
    light_color = 'w'
    text_color = 'k'
    font_size = 16
    ext = [-200,200,-110,110]
    bg_ext = ext
    img = None
    if 'Plot' in data:
        ext = data['Plot']['extent']
        if 'bg_image' in data['Plot']:
            if data['Plot']['bg_image'] != None:
                img = mpimg.imread(data['Plot']['bg_image'])
                if 'bg_extent' in data['Plot']:
                    bg_ext = data['Plot']['bg_extent']
                bg_alpha = 1.0
                if 'bg_alpha' in data['Plot']:
                    if data['Plot']['bg_alpha'] != None:
                        bg_alpha = data['Plot']['bg_alpha']
                #pl.imshow(img,extent=ext,alpha=bg_alpha)
        if figsize is None and 'fig_size' in data['Plot']:
            figsize = tuple(data['Plot']['fig_size'])
        if 'line_width' in data['Plot']:
            line_width = data['Plot']['line_width']
        if 'head_width' in data['Plot']:
            head_width = data['Plot']['head_width']
        if 'tail_width' in data['Plot']:
            tail_width = data['Plot']['tail_width']
        if 'line_color' in data['Plot']:
            line_color = data['Plot']['line_color']
        if 'edge_color' in data['Plot']:
            edge_color = data['Plot']['edge_color']
        if 'light_color' in data['Plot']:
            light_color = data['Plot']['light_color']
        if 'text_color' in data['Plot']:
            text_color = data['Plot']['text_color']
        if 'font_size' in data['Plot']:
            font_size = data['Plot']['font_size']
        if 'label_space' in data['Plot']:
            label_space = data['Plot']['label_space']
        if 'r_light' in data['Plot']:
            r = data['Plot']['r_light']
        if 'd_edges' in data['Plot']:
            d = data['Plot']['d_edges']
        if 'width_bar' in data['Plot']:
            width = data['Plot']['width_bar']
        if 'track_width' in data['Plot']:
            track_width = data['Plot']['track_width']
        if 'track_spacing' in data['Plot']:
            track_spacing = data['Plot']['track_spacing']
        if 'lx' in data['Plot']:
            lx = data['Plot']['lx']
        if 'ly' in data['Plot']:
            ly = data['Plot']['ly']

    if figsize is None:
        figsize = (10,5)
    print figsize
    fig, ax = pl.subplots(nrows=1, ncols=1, sharex=True, sharey=False,figsize=figsize)
    if img is not None:
        pl.imshow(img,extent=bg_ext,alpha=bg_alpha)
    nodes = []
    edges = {}

    if "Annotations" in data:
        for a in data['Annotations']:
            p = a['point']
            ax.text(p[0],p[1],a['label'],fontsize=font_size,color=text_color)

    x_min=data['Nodes'][0]['p'][0]
    y_min=data['Nodes'][0]['p'][1]
    x_max=x_min
    y_max=y_min

    for i,n in enumerate(data['Nodes']):
        nodes.append({'n':n,'e':0,'l':None})
        x=n['p'][0]
        y=n['p'][1]
        x_min=min(x_min,x)
        y_min=min(x_min,y)
        x_max=max(x_max,x)
        y_max=max(x_max,y)

    for i,q in enumerate(data['Queues']):
        n0=q['edge'][0]
        n1=q['edge'][1]
        pair = (n0,n1)
        if n1<n0 : pair = (n1,n0)
        if pair in edges:
            edges[pair]+=1
        else:
            edges[pair]=1
        q['pair']=pair

    if 'Transits' in data:
        for transit in data['Transits']:
            for i in range(1,len(transit['links'])):
                n0 = transit['links'][i-1]
                n1 = transit['links'][i]
                pair = (n0, n1)
                if n1 < n0 : pair = (n1, n0)
                if pair in edges:
                    edges[pair] += 1
                else:
                    edges[pair] = 1

                data['Queues'].append({'transit': True, 'edge': [n0,n1], 'pair': pair})

    for i,l in enumerate(data['Lights']):
        n=data['Nodes'][l['node']]
        nodes[l['node']]['l']=i
        n['light']=i
        x=n['p'][0]
        y=n['p'][1]
        if type == 'arrow':
            p = Circle((x,y), r, fc=light_color)
            ax.add_patch(p)
            ax.text(x-lx,y-ly,r'$l_{%d}$' % int(i+index_label_base),fontsize=font_size)
        else:
            r=15

    for i,q in enumerate(data['Queues']):
        pair = edges[q['pair']] > 1
        if 'label' in q:
            label = q['label']
        else:
            label = ''
        n0= data['Nodes'][q['edge'][0]]
        n1= data['Nodes'][q['edge'][1]]
        rx0=n0['p'][0]
        ry0=n0['p'][1]
        rx1=n1['p'][0]
        ry1=n1['p'][1]

        rx = rx0-rx1
        ry = ry0-ry1
        lth = math.sqrt(rx*rx+ry*ry)
        rx/=lth
        ry/=lth
        trx0=rx0
        try0=ry0
        if 'light' in n0:
            if pair and 'transit' not in q:
                theta = -math.asin(d/r)
                trx = rx * math.cos(theta) - ry * math.sin(theta);
                ry = rx * math.sin(theta) + ry * math.cos(theta);
                rx=trx
            trx0-=rx * r; try0-=ry * r
        elif pair and 'transit' not in q:
            trx0-=ry * d; try0+=rx * d
        rx = rx1-rx0
        ry = ry1-ry0
        lth = math.sqrt(rx*rx+ry*ry)
        rx/=lth
        ry/=lth
        if 'light' in n1:
            if pair and 'transit' not in q:
                theta = math.asin(d/r)
                trx = rx * math.cos(theta) - ry * math.sin(theta);
                ry = rx * math.sin(theta) + ry * math.cos(theta);
                rx=trx
            if type == 'arrow':
                rx1-=rx * (r+line_width); ry1-=ry * (r+line_width)
            else:
                rx1-=rx * (r); ry1-=ry * (r)
        elif pair and 'transit' not in q:
            rx1+=ry * d; ry1-=rx * d
        rx0=trx0
        ry0=try0
        rx = rx1-rx0
        ry = ry1-ry0
        lth = math.sqrt(rx*rx+ry*ry)
        theta = math.degrees(math.atan2(rx,ry))
        dx,dy = label_distance(theta,i)
        #if debug:
        #    dx *= 3
        #    dy *= 3
        tx=ry/lth * label_space + dx; ty=rx/lth * label_space + dy
        tc = 0.5
        if 'text_pos' in q:
            tc = q['text_pos']
        rx = rx0+(rx1-rx0)*tc
        ry = ry0+(ry1-ry0)*tc


        qtext_color = text_color
        qline_width = line_width
        qhead_width = head_width
        qtail_width = tail_width
        qedge_color = edge_color
        qline_color = line_color
        qfont_weight = None
        qfont_size = font_size
        qoutline = None
        qtrack_width = track_width
        qtrack_spacing = track_spacing
        if 'text_color' in q:
            qtext_color = q['text_color']
        if 'line_width' in q:
            qline_width = q['line_width']
        if 'head_width' in q:
            qhead_width = q['head_width']
        if 'tail_width' in q:
            qtail_width = q['tail_width']
        if 'edge_color' in q:
            qedge_color = q['edge_color']
        if 'line_color' in q:
            qline_color = q['line_color']
        if 'font_weight' in q:
            qfont_weight = q['font_weight']
        if 'font_size' in q:
            qfont_size = q['font_size']
        if 'outline' in q:
            qoutline = q['outline']
        if qfont_weight == 'bold':
            qlabel = r'$\mathbf{q_{%d}}$' % int(i+index_label_base)
        else:
            qlabel = r'$q_{%d}$' % int(i+index_label_base)
        if 'track_width' in q:
            qtrack_width = q['track_width']
        if 'track_spacing' in q:
            qtrack_spacing = q['track_spacing']
        if debug and not 'transit' in q:
            #qlabel += ',$%d,%ss$' % (q['Q_MAX'],q['Q_DELAY'])
            #if q['Q_P'] is not None:
            #    qlabel += '\n$%s$' % (q['Q_P'])
            #if q['Q_IN'] > 0:
            #    ax.text(rx0-5,ry0-5,r'%d' % q['Q_IN'],fontsize=10)
            #if q['Q_OUT'] > 0:
            #    ax.text(rx1-5,ry1-5,r'%d' % q['Q_OUT'],fontsize=10)
            #for j in range(len(data['Queues'])):
            #    flow = '%d_%d' % (i,j)
            #    if flow in data['Flows']:
            #        qlabel += '\n$f_{out,%d}=%s$' % (j,data['Flows'][flow]['F_MAX'])
            #    flow = '%d_%d' % (j,i)
            #    if flow in data['Flows']:
            #        qlabel += '\n$f_{%d,in}=%s$' % (j,data['Flows'][flow]['F_MAX'])
            rx = rx1-rx0
            ry = ry1-ry0
            plot_circle_label(ax,q['Q_MAX'],rx0+0.5*rx,ry0+0.5*ry,10)

            #qfont_size = 12
        if 'transit' in q:
            rx = rx1-rx0
            ry = ry1-ry0
            tx=(rx/lth) * qtrack_width; ty=(ry/lth) * qtrack_width
            N = int(lth / qtrack_spacing)
            dt = 1.0 / N
            t=0
            for j in range(N):
                qrx0 = rx0 + t * rx
                qry0 = ry0 + t * ry
                qrx1 = rx0 + (t+dt) * rx
                qry1 = ry0 + (t+dt) * ry
                ax.plot([qrx0+ty,qrx0-ty],[qry0-tx,qry0+tx], lw=qline_width,color=qline_color)
                t += dt
            ax.plot([rx0,rx1],[ry0,ry1], lw=qline_width*2,color=qline_color)
        else:
            if type == 'arrow':
                if qoutline != None:
                    ax.text(rx+(tx),ry-(ty), qlabel, fontsize=qfont_size+1, color=qoutline)
                ax.text(rx+(tx),ry-(ty), qlabel, fontsize=qfont_size, color=qtext_color)
                rx = rx1-rx0
                ry = ry1-ry0
                rx=(rx/lth); ry=(ry/lth)
                if 'label_inflow' in q or args.label_inflow and q['Q_IN'] > 0:
                    rx0 = rx0 - rx*3
                    ry0 = ry0 - ry*3
                #plot([rx,rx+ty],[ry,ry-tx])
                arrow = ax.arrow(rx0,ry0,rx1-rx0,ry1-ry0, shape='full', lw=qline_width,color=qline_color,length_includes_head=True, head_width=qhead_width, width=qtail_width)
                if 'label_inflow' in q or args.label_inflow:
                    if q['Q_IN'] > 0:
                        qin_label_radius = 7
                        plot_circle_label(ax,q['Q_IN'],rx0 - rx * qin_label_radius,ry0 - ry * qin_label_radius,qin_label_radius)
                arrow.set_ec(qedge_color)
                arrow.set_fc(qline_color)

            elif type == 'bar' or type == 'carrow':
                #qfont_weight = None
                #ax.text(rx+(tx),ry-(ty),'%d' % int(i+index_label_base),fontsize=font_size, fontweight=qfont_weight,color=scalarMap.to_rgba(0))
                ax.text(rx+(tx),ry-(ty),qlabel,fontsize=qfont_size, fontweight=qfont_weight,color=scalarMap.to_rgba(0))
                N=len(q['cmap'])
                t=0
                #q=0.0
                rx = rx1-rx0
                ry = ry1-ry0
                tx=(rx/lth) * width; ty=(ry/lth) * width
                qrx0=rx1 #- rx * q
                qry0=ry1 #- ry * q
                if N == 1:
                    dt = 1
                else:
                    dt=(1.0)/(N)
                # for j in range(N):
                #     qrx0=rx0 + t * rx
                #     qry0=ry0 + t * ry
                #     qrx1=rx0 + (t+dt) * rx
                #     qry1=ry0 + (t+dt) * ry
                #     colorVal = scalarMap.to_rgba(q['cmap'][j])
                #     if type == 'bar':
                #         ax.add_patch(mp.patches.Polygon([[qrx0-ty,qry0+tx],[qrx1-ty,qry1+tx],[qrx1+ty,qry1-tx],[qrx0+ty,qry0-tx]],closed=True,fill='y',color=colorVal,ec='none',lw=0.9))
                #     else:
                #         arrow = ax.arrow(qrx0,qry0,rx1-qrx0,ry1-qry0, shape='full', lw=line_width,color=colorVal,length_includes_head=True, head_width=head_width, width=tail_width)
                #         arrow.set_ec(colorVal)
                #         arrow.set_fc(colorVal)
                #     t+=dt


                t = np.linspace(0,1,N)
                x =rx0 + t * rx
                y =ry0 + t * ry
                points = np.array([x,y]).T.reshape(-1,1,2)
                segments = np.concatenate([points[:-1], points[1:]], axis=1)
                bar_cmap = np.array([scalarMap.to_rgba(q['cmap'][j]) for j in range(N)])
                bar_widths = 1 + np.array(q['cmap'])*2*width
                lc = LineCollection(segments,linewidths=bar_widths,colors=bar_cmap)
                ax.add_collection(lc)

            if type == 'bar' or type == 'carrow':
                for i,l in enumerate(data['Lights']):
                    n=data['Nodes'][l['node']]
                    nodes[l['node']]['l']=i
                    n['light']=i
                    x=n['p'][0]
                    y=n['p'][1]
                    p = Circle((x,y), r,ec=scalarMap.to_rgba(0),fc='w')
                    ax.add_patch(p)
                    ax.text(x-3,y-3,r'%d' % int(i+index_label_base),fontsize=10,color=scalarMap.to_rgba(0))



    pl.axis('scaled')
    #ax.set_ylim([x_min-10,x_max+10])
    #ax.set_xlim([y_min-10,y_max+10])
    #[-200,200,-110,110]
    #ax.set_ylim([-110,110])
    #ax.set_xlim([-200,200])
    #if debug:
    #    ax.set_ylim((ext[2]-50,ext[3]+50))
    #    ax.set_xlim((ext[0]-50,ext[1]+50))
    #else:
    ax.set_ylim(ext[2:4])
    ax.set_xlim(ext[0:2])
    pl.axis('off')
    if type == 'bar' or type == 'carrow':
        cax = fig.add_axes([0.9, 0.1, 0.03, 0.8])
        pl.colorbar(CS3,cax=cax)
    pl.tight_layout()

def plot_network(args):
    for f in args.files:
        data = open_data_file(f)
        if data is not None:
            plot_network_figure(data,args.figsize,index_label_base=args.index_label_base,debug=args.debug_network)

def plot_network_delay(args):
    """
    :param args:
    :return:
    """
    type = args.plot_network_delay
    if type == 'arrow': type = 'carrow'

    for f in args.files:
        data = open_data_file(f)
        if data is not None:

            results = data['Out']
            if 'Run' in results:
                if args.run:
                    results = data['Out']['Run'][args.run]
                else:
                    results = data['Out']['Run'][0]
                #if len(data['Out']['Run']) > 1:
                #        del data['Out']['Run'][1:-1]

            NQ=-1
            DT = float(results['DT'][0])
            max_delay = 10
            if args.delay_lt:
                max_delay = args.delay_lt
            if args.n <= 0:
                for i,q in enumerate(data['Queues']):

                    qi = results['q_%d' %i]
                    qi_in = np.array(results['q_{%d,in}' %i])
                    qi_out = results['q_{%d,out}' %i]
                    Q_DELAY = q['Q_DELAY']
                    N = len(qi)
                    c_in  = np.zeros(N)
                    c_out = np.zeros(N)
                    c_in[0] = qi_in[0]
                    c_out[0] = qi_out[0]
                    for n in range(1,N):
                        c_in[n]=c_in[n-1] + qi_in[n]
                        c_out[n]=c_out[n-1] + qi_out[n]
                    if i==NQ:
                        #pl.figure()
                        pl.plot(range(0,N),c_in)
                        pl.plot(range(0,N),c_out)
                    delay = ( np.sum((c_in - c_out) * DT) - (np.sum(qi_in) * Q_DELAY) ) / np.sum(qi_in)
                    q['cmap'] = [delay / max_delay]
                    #print 'q_%d' % i,'\tdelay: %f' % delay,'\tcars: %d' % np.sum(qi_in),'\tQ_DELAY: %d' %Q_DELAY
            else:
                N_dt = args.n

                dt = DT/N_dt
                print 'DT=',results['DT'][0]
                print 'dt=',dt
                t=dt
                nq = len(data['Queues'])
                qdat = []
                cdat = []
                #max_delay = 0
                for i,q in enumerate(data['Queues']):
                    qi = results['q_%d' %i]
                    qi_in = np.array(results['q_{%d,in}' %i]) * (dt/DT)
                    qi_out = np.array(results['q_{%d,out}' %i])* (dt/DT)
                    qi_in_total = np.sum(qi_in)*(DT/dt)
                    #print 'sum(q_in)=',np.sum(qi_in)
                    #print 'sum(q_out)=',np.sum(qi_out)
                    Q_DELAY = q['Q_DELAY']
                    Nt = int(len(qi_in)*N_dt)
                    N = int(math.ceil(Q_DELAY / dt))
                    #print 'N=',N
                    q_delay = float(Q_DELAY)/N
                    Q = q['Q_MAX']/N
                    #print i,N,Q
                    qs = np.zeros((N,Nt))
                    ys = np.zeros((N,Nt))
                    cy = np.zeros((N+1,Nt))
                    #ys[0,0] = qi_in[0]*q_delay
                    #ys[N-1,0] = qi_out[0]*dt_q
                    y0  = np.interp(np.linspace(0,len(qi),Nt,endpoint=False),np.linspace(0,len(qi),len(qi),endpoint=False),qi_in)
                    ys[N-1,:] = np.interp(np.linspace(0,len(qi),Nt,endpoint=False),np.linspace(0,len(qi),len(qi),endpoint=False),qi_out)
                    #print sum(qi_in)
                    for k in range(1,Nt):
                        #ys[0,k] = qi_in[int(k/N)]*dt
                        #ys[N-1,k] = qi_out[int(k/N)]

                        qs[0,k] = qs[0,k-1] + y0[k-1] - ys[0,k-1]
                        #qs[0,k] = qs[0,k-1] + qi_in[int(k/N)]*dt_q - ys[0,k-1]
                        for n in range(1,N):
                            qs[n,k] = qs[n,k-1] + ys[n-1,k-1] - ys[n,k-1]
                            qs[n,k] = max(qs[n,k],0)
                        ##qs[1:,k] = qs[1:,k-1] + ys[:-1,k-1] - ys[1:,k-1]
                        ##qs[1:,k] = np.fmax(qs[1:,k],0)
                        for n in range(0,N-1):
                            ys[n,k] = min(qs[n,k], Q-qs[n+1,k])
                            ys[n,k] = max(ys[n,k],0)
                        ##ys[:-1,k] = np.fmin(qs[:-1,k], Q-qs[1:,k])
                        ##ys[:-1,k] = np.fmax(ys[:-1,k],0)
                        #ys[N-1,k] = qi_out[int(k/N)]*dt_q

                    cy[0] = np.cumsum(y0)
                        #cy[1:,k] = cy[1:,k-1]+ys[0:,k]
                    cy[1:] = np.cumsum(ys,axis=1)
                    #print len(np.linspace(0,len(qi),len(qi)*N))
                    #y0  = np.interp(np.linspace(0,len(qi),len(qi)*N,endpoint=False),np.linspace(0,len(qi),len(qi),endpoint=False),qi_in*dt_q)
                    #print y0
                    #for k in range(1,ys.shape[1]):
                    #    cy[0,k] = cy[0,k-1]+y0[k]
                    #    cy[1:,k] = cy[1:,k-1]+ys[0:,k]
                    delay = (np.sum((cy[:-1,:] - cy[1:,:]) *dt ,axis=1 ) - qi_in_total*q_delay)# / qi_in_total
                    #print 'delay %d' %i, np.sum(delay)
                    #print 'q_%d' % i,'\tdelay: %f' % (np.sum(delay) ),'\tcars: %d' % (qi_in_total),'\tQ_DELAY: %d' % Q_DELAY
                    #pl.figure()
                    #pl.plot(range(0,len(delay)),delay)
                    #pl.title(r'$q_%d$' % i)
                    #pl.ylim(0,200)
                    #pl.figure()
                    q['cmap'] = delay / max_delay#qs[:,qs.shape[1]*0.25]/np.max(qs)#[j/float(N) for j in range(0,N)]
                    #max_delay = max(max_delay,np.max(delay))
                    #max_delay = 3.0
                    #print np.max(qs)
                    qdat.append(qs)
                    cdat.append(cy)

                    #if i == 0:
                    #    print len(qi)*N
                    #    print len(np.linspace(0,len(qi),len(qi)*N))
                    #    print cdat[0].shape[1]
                        #pl.plot(range(0,len(qi_in)),qi_in)
                        #pl.plot(range(0,len(qi_in)),qi_out)
                        #pl.plot(range(0,len(qi_in)),qi)


            #pl.figure()
            #pl.plot(range(0,qdat[0].shape[1]),qdat[0][0,:])
            #pl.plot(range(0,qdat[0].shape[1]),qdat[0][-1,:])
                #pl.figure()

                #pl.plot(np.linspace(0,len(qi),cdat[NQ].shape[1],endpoint=False),cdat[NQ][0,:])
                #pl.plot(np.linspace(0,len(qi),cdat[NQ].shape[1],endpoint=False),cdat[NQ][1,:])
                #pl.plot(np.linspace(0,len(qi),cdat[NQ].shape[1],endpoint=False),cdat[NQ][-2,:] - cdat[NQ][-1,:])
                print 'max_delay',max_delay
                #max_delay = 2
                #q['cmap'] = q['cmap'] / max_delay
            for i,q in enumerate(data['Queues']):

                qi = results['q_%d' %i]
                qi_in = np.array(results['q_{%d,in}' %i])
                qi_out = results['q_{%d,out}' %i]
                Q_DELAY = q['Q_DELAY']
                N = len(qi)
                c_in  = np.zeros(N)
                c_out = np.zeros(N)
                c_in[0] = qi_in[0]
                c_out[0] = qi_out[0]
                for n in range(1,N):
                    c_in[n]=c_in[n-1] + qi_in[n]
                    c_out[n]=c_out[n-1] + qi_out[n]
                if i==NQ:
                    #pl.figure()
                    pl.plot(range(0,N),c_in)
                    pl.plot(range(0,N),c_out)
                delay = np.sum((c_in - c_out) * DT) - (np.sum(qi_in) * Q_DELAY)
                #print 'q_%d' % i,'\tdelay: %f' % delay,'\tcars: %d' % np.sum(qi_in),'\tQ_DELAY: %d' %Q_DELAY
            #pl.xlim(0,600)
            #pl.ylim(75,100)
            plot_network_figure(data,args.figsize,type=type,index_label_base=args.index_label_base)


def plot_delay(data, step, queues=[],line_style=['--'],args=None):
    # print len(time),time
    # print len(cumu_in),cumu_in
    # print len(cumu_out),cumu_out
    pl.clf()
    fig, ax = pl.subplots(nrows=1, ncols=1, sharex=True, sharey=False)
    if args.figsize:
        fig.set_size_inches(args.figsize[0], args.figsize[1])
    else:
        fig.set_size_inches(15, 7)
    ax2 = ax.twinx()

    i=0
    c_i=0
    l_i=0
    m_i=0
    lab_i=0
    labels=['']
    if args.labels: labels=args.labels




    if args.markerfill == 'n':
        mfc = ['None'] * len(args.color)
    else:
        mfc = [args.color[i] if args.markerfill[i]=='y' else 'None' for i in range(len(args.markerfill))]

    mevery = args.markevery
    if len(mevery) < len(args.marker):
        mevery = mevery + [1] * (len(args.marker) - len(mevery))
    i=0
    arrival_plot = False
    for d in data:
        results = d['Out']
        if 'Run' in results:
            results = d['Out']['Run'][0]
        if not queues:
            queues = [range(len(d['Queues']))]
        #label = results['Out']['label']
        if step != None:
            if 'Step' in results['Out']:
                label = results['Out']['Step'][step]['label']
        for q in queues:
            #title = d['Title']
            #titles.append(d['Title'])
            time,cumu_in,cumu_out,cumu_delay,delay_by_car,delay = calc_delay(d, results, queues=q)
            if args.normalize:
                print
                cumu_out /= np.max(cumu_out)
                cumu_in /= np.max(cumu_in)
            if arrival_plot == False:
                ax.plot(time,cumu_in,color=args.color[c_i], linestyle=line_style[i], label='Cumulative arrivals', marker=args.marker[m_i],markeredgecolor=args.color[c_i], markerfacecolor=mfc[c_i],markevery=mevery[m_i])
                if i+1 < len(line_style): i += 1
                if c_i+1 < len(args.color): c_i += 1
                if m_i+1 < len(args.marker): m_i += 1
                arrival_plot = True
            if labels[lab_i] == "" or labels[lab_i] == " " or labels[lab_i] is None:
                label_c = 'Cumulative departures'
                label_d = 'Delay'
            else:
                label_c = '%s cumulative departures' % labels[lab_i]
                label_d = '%s delay' % labels[lab_i]
            ax.plot(time,cumu_out,color=args.color[c_i],linestyle=line_style[i], label=label_c, marker=args.marker[m_i],markeredgecolor=args.color[c_i],markerfacecolor=mfc[c_i],markevery=mevery[m_i])
            if i+1 < len(line_style): i += 1
            if c_i+1 < len(args.color): c_i += 1
            if m_i+1 < len(args.marker): m_i += 1
            ax2.plot(time,cumu_delay,color=args.color[c_i], linestyle=line_style[i], label=label_d, marker=args.marker[m_i],markeredgecolor=args.color[c_i],markerfacecolor=mfc[c_i],markevery=mevery[m_i])
            #ax.plot(time,[10 * cumu_delay[i]/q if q != 0 else 0 for i,q in enumerate(cumu_in)],label='norm delay')
            if i+1 < len(line_style): i += 1
            if c_i+1 < len(args.color): c_i += 1
            if m_i+1 < len(args.marker): m_i += 1

        if lab_i+1 < len(labels): lab_i += 1
    if args.x_limit:
        ax.set_xlim(args.x_limit[0], args.x_limit[1])
    ax.grid()
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Vehicles')
    ax2.set_ylabel('Delay (s)')
    if args.y_limit != None:
        ax.set_ylim(args.y_limit[0], args.y_limit[1])
    if args.y_limit2 != None:
        ax2.set_ylim(args.y_limit2[0], args.y_limit2[1])
    #else:
    #    ax2.set_ylim(0, 25)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    if not args.no_legend:
        ax.legend(h1+h2, l1+l2, loc='upper left')
    if args.title:
        #pl.title('Arrival Curves and Delay for Queues %s' % ', '.join([str(q) for q in queues]) )
        pl.title(args.title[0] )

def calc_min_travel_time(data,args):
    print data.keys()
    results = data['Out']
    if 'Run' in results:
        results = d['Out']['Run'][0]
    if args.step != None:
        if 'Step' in results:
            if len(data['Out']['Step']) > args.step:
                results = data['Out']['Step'][args.step]
    min_travel_time=0
    total_q_in=0
    if args.queues != None:
        for qs in args.queues:
            delay = 0
            for q in qs:
                delay+=data['Queues'][q]['Q_DELAY']
            q_in = sum(results['q_{%d,in}' % qs[0] ])
            min_travel_time+=q_in*delay
            total_q_in+=q_in
    return min_travel_time,total_q_in

def plot_annotations(ax,args):
    if args.annotate_labels is not None and args.annotate_x is not None and args.annotate_y is not None:
        assert len(args.annotate_labels) == len(args.annotate_x) == len(args.annotate_y)
        for i,_ in enumerate(args.annotate_labels):
            if args.annotate_size is not None:
                size = args.annotate_size[i]
            else:
                size = 8
            ax.text(args.annotate_x[i],args.annotate_y[i],args.annotate_labels[i],size=size)
            if args.annotate_vline is not None and args.annotate_vline[i]:
                ax.axvline(args.annotate_x[i],color='k',linestyle = args.annotate_vline_style[i])
    if args.annotation_arrow is not None:
        #print args.annotation_arrow
        for annotation in args.annotation_arrow:
            kwargs = json.loads(annotation[1])
            ax.annotate(annotation[0],**kwargs)
    if args.annotation_text is not None:
        #print args.annotation_text
        for annotation in args.annotation_text:
            kwargs = json.loads(annotation[3])
            x = annotation[0]
            y = annotation[1]
            text = annotation[2]
            ax.text(x,y,text,**kwargs)

def plot_box_plot(args):

    plot_data_files = read_files(args.files)

    pl.clf()
    nplots=len(plot_data_files)
    fig, ax = pl.subplots(nrows=1, ncols=nplots, sharex=False, sharey=True)
    #gs1 = mp.gridspec.GridSpec(4, 4)
    #gs1.update(wspace=0.025, hspace=0.05)

    if not isinstance(ax,np.ndarray): ax=[ax]

    if args.figsize:
        fig.set_size_inches(args.figsize[0], args.figsize[1])
    else:
        fig.set_size_inches(15, 7)
    titles=[]

    i=0
    c_i=0
    l_i=0
    lab_i=0
    labels=['Plot 1']
    if args.labels: labels=args.labels

    for plot_i,plot in enumerate(plot_data_files):

        plot_data = []
        plot_labels=[]

        for d in plot:



            #titles.append(file['Title'])
            results = d['Out']

            #label =  file['Out']['label']
            if args.run != None:
                runs=args.run
            else:
                if 'Run' in results:
                    runs = range(0,len(results['Run']))
                else:
                    runs=[0]
            solve_time=[]
            #if 'Run' in results:
            #    runs = range(len(results['Run']))
            delay = []
            for run in runs:
                if 'Run' in results:
                    results = d['Out']['Run'][run]


                #print 'results',results.keys()

                #total_travel_time = calc_total_travel_time(d,results)
                #min_travel_time,total_q_in = calc_min_travel_time(d,args)
                #delay = []
                for q in args.queues:
                    #trimmed_delay = trim_delay(calc_delay(d, results, queues=q))
                    # in_start=0
                    # in_end=1
                    # for j in range(len(cumu_in)):
                    #     if cumu_in[j] > cumu_in[in_end]: in_end=j
                    # j=0
                    # q_delay=0
                    # for sub_q in q:
                    #     q_delay+=d['Queues'][sub_q]['Q_DELAY']
                    #
                    # while cumu_in[in_start+1]<1e-6 and in_start<in_end-1: in_start+=1

                    _,_,_,cumu_delay,delay_by_car,trimmed_delay = calc_delay(d, results, queues=q,dt=args.dt)
                    if args.by_car == True:
                        delay += delay_by_car # q_delay #[cumu_delay[i] for i in range(in_start,in_end)]
                    else:
                        delay += trimmed_delay
                #print delay
                #average = (total_travel_time - min_travel_time) / total_q_in
                #mean = sum(delay)/len(delay)
                #if len(plot_label)==0:
                #    plot_label = '$'+label.split('$')[1]+'$'

                time = results['t']
                total_time = time[-1] - time[0]

                if 'Step' in results:
                    if 'N' in results['Step'][0]:
                        N = results['Step'][0]['N']
                    else:
                        N = len(results['Step'][0]['t'])-1
                    for step in results['Step']:
                        if 'solver_runtime' not in step:
                            solve_time.appened(step['solve_time'])
                        else:
                            solve_time.append(step['solver_runtime'])
                else:
                     N = len(results['t'])-1
            if args.plot_cpu_time:
                box_data=solve_time
            else:
                if 'delay' in results:
                    box_data = results['delay']
                else:
                    box_data = [delay_n  * args.time_factor for delay_n in delay]
            Ni = N - 0.25 + plot_i
            #if Ni in plot_data:

#                    plot_data[Ni]=[plot_data[Ni][0]+box_data,0]
#               else:
            plot_data.append(box_data) #[delay,average]
            plot_labels.append(labels[lab_i])

            if lab_i+1 < len(labels): lab_i += 1

        X = sorted(plot_data)
        Y = plot_data
        boxprops = dict(fillcolor=args.color[c_i])
        props = dict(linestyle=args.linestyle[l_i],color=args.color[c_i],markeredgecolor=args.color[c_i],
                      markerfacecolor=args.color[c_i])
        props2 = dict(color=args.color[c_i],markeredgecolor=args.color[c_i],
                      markerfacecolor=args.color[c_i])
        props3 = dict(markeredgecolor=args.color[c_i],
                      markerfacecolor=args.color[c_i])
        #print boxprops,c_i,len(args.color)

        bp = ax[plot_i].boxplot(Y, vert=True, showmeans=True, widths=0.5, whis=1e99, meanprops=dict(markersize=3),patch_artist=True) #, boxprops=props, whiskerprops=props3, capprops=props,
                      #medianprops=props, meanprops=props3)#,flierprops=props3,positions=X)
        for box in bp['boxes']:
            #box.set(facecolor = args.color[c_i] , alpha = 0.2 )
            box.set(facecolor = mp.colors.ColorConverter().to_rgba(args.color[c_i] , alpha=0.2))
            #box.set()
            box.set(edgecolor = (0, 0, 1, 1.0) )
            if c_i+1 < len(args.color): c_i += 1
        #Y = [plot_data[x][1] for x in X]
        #ax.plot(X,Y,c=args.color[c_i], label=plot_label,marker='x')
        if args.draw_vlines is not None:
            for vline_offset in args.draw_vlines:
                ax[plot_i].axvline(vline_offset,color='k')
        #ax[plot_i].axvline(3.5,color='k')
        if args.x_limit:
            ax[plot_i].set_xlim(args.x_limit[0], args.x_limit[1])
        if args.y_limit:
            ax[plot_i].set_ylim(args.y_limit[0], args.y_limit[1])
        ax[plot_i].grid()
        if args.box_plot_labels_vertical:
            rotation = 'vertical'
        else:
            rotation = 'horizontal'
        ax[plot_i].set_xticklabels(plot_labels,rotation=rotation)
        if args.title:
            ax[plot_i].set_title(args.title[plot_i % len(args.title)])
        if i+1 < len(args.linestyle): i += 1
        #if c_i+1 < len(args.color): c_i += 1
        if l_i+1 < len(args.linestyle): l_i += 1
        if plot_i >= 1:
            args.annotation_text = None
            args.annotation_arrow = None
        plot_annotations(ax[plot_i],args)

    if args.plot_cpu_time:
        ax[0].set_ylabel('Solve Time (s)')
    else:
        ax[0].set_ylabel('Delay (s)')
    #pl.tight_layout()
    #ax.set_ylabel('Total Travel Time')
    #ax.legend(loc='best')
    #if args.title:
    #    pl.title(args.title)
    #else:
    #    pl.title('Box Plot for Delay' )

def open_data_file(file):
    start_time_open_file = clock_time.time()
    debug("opening data file:" + file)
    if os.path.isfile(file):
        if zipfile.is_zipfile(file):
            path,file_json = os.path.split(os.path.splitext(file)[0]+".json")
            start_time = clock_time.time()
            debug('   Loading zip file: ...',True)
            zf = zipfile.ZipFile(file)
            debug( 'Done. %.2f sec' % (clock_time.time() - start_time))
            start_time = clock_time.time()
            debug('   Reading json    : ...',True)
            json_file = zf.read(file_json)
            debug( 'File size: %.2f MB' % (os.path.getsize(file) / float(2**20) ))
            debug( 'Done. %.2f sec' % (clock_time.time() - start_time))
            start_time = clock_time.time()
            debug('   Decoding json   : ...',True)
            data = json.loads(json_file)
            debug( 'Done. %.2f sec' % (clock_time.time() - start_time))
            zf.close()
        else:
            start_time = clock_time.time()
            debug( '  Loading file:  ...' ,True)
            f = open(str(file),'r')
            debug('Done. %.2f sec' % (clock_time.time() - start_time))
            start_time = clock_time.time()
            debug('   Decoding json: ...',True)
            data  = json.load(f)
            debug('Done. %.2f sec' % (clock_time.time() - start_time))
            f.close()
    else:
        print 'file not found:',file
        data = None
    debug('Done. %.2f sec' % (clock_time.time() - start_time_open_file))
    return data

def read_files(plot_files, return_file_sets=False,DEBUG = False):
    debug(str(plot_files))
    data_sets=[]
    file_sets=[]
    gc.disable()
    for plot_file in plot_files:
        files = []
        if os.path.isfile(plot_file):
            path,name = os.path.split(plot_file)
            type = name.split('.')[-1]
            if type == 'json' or type == 'zip':
                files.append(plot_file)

            else:
                if len(path) > 0: path += '/'
                debug('Opening plot file: '+name)
                f = open(str(plot_file),'r')

                for line in f:
                    fields = line.split(' ')
                    if len(fields) > 0 and len(fields[0].strip()) > 0:

                        files.append(path+fields[0].strip())
                        #if len(fields)>1:
                        #    labels.append(fields[1])
                f.close()
        data_files = []
        files_opened = []
        debug('  Opening files in plot file: '+str(files))

        for file in files:
            data = open_data_file(file)
            if data is not None:
                data_files.append(data)
                files_opened.append(file)
            #if os.path.isfile(file):
                # if zipfile.is_zipfile(file):
                #     path,file_json = os.path.split(os.path.splitext(file)[0]+".json")
                #     #print 'Loading zip file:',file,'...',
                #     zf = zipfile.ZipFile(file)
                #     #print 'Done.'
                #     #print '   Decoding json file:',file_json,'...',
                #     data.append(json.loads(zf.read(file_json)))
                #     #print 'Done.'
                # else:
                #     #print 'Loading file:',file,'...',
                #     f = open(str(file),'r')
                #     #print 'Done.'
                #     #print '   Decoding json file:',file,'...',
                #     data.append(json.load(f))
                #     #print 'Done.'
                #     f.close()

        data_sets.append(data_files)
        file_sets.append(files_opened)
    gc.enable()
    gc.collect()
    if return_file_sets:
        return data_sets,file_sets
    else:
        return data_sets



def plot_av_travel_time(args):
    pl.clf()
    fig, ax = pl.subplots(nrows=1, ncols=1, sharex=True, sharey=False)
    if args.figsize:
        fig.set_size_inches(args.figsize[0], args.figsize[1])
    else:
        fig.set_size_inches(15, 7)
    titles=[]
    i=0
    l_i=0
    labels=[]
    if args.labels: labels=args.labels
    if args.markerfill == 'n':
        mfc = ['None'] * len(args.color)
    else:
        mfc = [args.color[i] if args.markerfill[i]=='y' else 'None' for i in range(len(args.markerfill))]
    plot_X = []
    plot_Y = []
    plot_data_files = read_files(args.files)

    for data in plot_data_files:

        plot_X.append([])
        plot_Y.append([])

        plot_label=''
        if len(labels)>0: plot_label = labels[l_i]

        for d in data:

            titles.append(d['Title'])
            results = d['Out']

            runs=1
            if 'Run' in results:
                runs = len(results['Run'])
                d_out = results['Run'][0]
                label =  d_out
            else:
                d_out = results

            delay = []
            total_travel_time = 0
            for run in range(runs):
                if 'Run' in d['Out']:
                    results = d['Out']['Run'][run]
                for q in args.queues:
                    _,_,_,cumu_delay,delay_by_car,trimmed_delay = calc_delay(d, results, queues=q,dt=args.dt)
                    if args.by_car == True:
                        delay += delay_by_car # q_delay #[cumu_delay[i] for i in range(in_start,in_end)]
                    else:
                        delay += trimmed_delay

                av_delay = np.mean(delay)
                total_traffic_in = calc_total_traffic(d,results,args.queues)

                if len(plot_label)==0:
                    plot_label = '$'+label.split('$')[1]+'$'
            total_travel_time = results['total_travel_time']
            plot_Y[-1].append(total_travel_time/total_traffic_in)
            plot_X[-1].append(total_traffic_in)
        i += 1


    i=0
    c_i=0
    m_i=0
    l_i=0
    labels=[]
    if args.labels: labels=args.labels
    for plot_i in range(len(plot_Y)):
        if len(labels)>0:
            plot_label = labels[l_i]
        else:
            plot_label = '$'+label.split('$')[1]+'$'

        _ = ax.plot(plot_X[plot_i],plot_Y[plot_i],color=args.color[c_i], linestyle=args.linestyle[l_i], label=plot_label,
                marker=args.marker[m_i],markerfacecolor=mfc[c_i]);

        if l_i+1 < len(args.linestyle): l_i += 1
        if c_i+1 < len(args.color): c_i += 1
        if m_i+1 < len(args.marker): m_i += 1
        i += 1
    plot_annotations(ax,args)
    if args.x_limit:
        ax.set_xlim(args.x_limit[0], args.x_limit[1])
    if args.y_limit:
        ax.set_ylim(args.y_limit[0], args.y_limit[1])
    ax.grid()
    ax.set_xlabel('Total traffic through network (vehicles)')
    ax.set_ylabel('Average travel time through network (s)')
    if not args.no_legend:
        ax.legend(loc='best')
    if args.title:
        pl.title(args.title[0])
    #else:
    #    if args.plot_cpu_time:
    #        pl.title('CPU Time vs % increase in total travel time' )
    #    else:
    #        pl.title('Number of time samples vs % increase in total travel time' )

def get_av_delay(data,args):
    results = data['Out']

    runs=1
    if 'Run' in results:
        runs = len(results['Run'])

    for run in range(runs):
        if 'Run' in data['Out']:
            results = data['Out']['Run'][run]
        if 'total_traffic_in' in results:
            total_traffic_in = results['total_traffic_in']
            total_travel_time = results['total_travel_time']
            free_flow_travel_time = calc_total_free_flow_travel_time(data,results)
            average_delay = results['average_delay']
        else:
            total_traffic_in = calc_total_traffic(data,results,args.queues)
            total_travel_time = calc_total_travel_time(data,results) * args.time_factor
            free_flow_travel_time = calc_free_flow_travel_time(data,results,args.queues) * args.time_factor
            average_delay = (total_travel_time - free_flow_travel_time) / total_traffic_in

    return average_delay,total_traffic_in

def plot_delay_diff( plot_data_files, args):
    plot_X = []
    plot_Y = []
    data = plot_data_files[0][0]
    results = data['Out']
    if 'Run' in results:
        results = results['Run'][0]
    Q_IN_duration = calc_in_flow_duration(data,results) * args.time_factor
    #print args.plot_delay_diff[0] / (Q_IN_duration / 3600.0)
    #print (args.plot_delay_diff[0] / (Q_IN_duration / 3600.0)) * (Q_IN_duration / 3600.0)
    xpoint1 = args.plot_delay_diff[0] * (Q_IN_duration / 3600.0)
    xpoints = np.linspace(args.plot_delay_diff[1] / 100.0 ,args.plot_delay_diff[2] / 100.0,num=100,endpoint=True)
    traffic_points = []
    for x in list((xpoints)):
        traffic_points.append(xpoint1 - (xpoint1 * x))

    for j in range(0,len(plot_data_files),2):
        av_delay0 = []
        total_traffic_in0 = []
        av_delay1 = []
        total_traffic_in1 = []

        for data in plot_data_files[j]:
            av_delay, total_traffic_in = get_av_delay(data,args)
            av_delay0.append(av_delay)
            total_traffic_in0.append(total_traffic_in)

        for data in plot_data_files[j+1]:
            av_delay, total_traffic_in = get_av_delay(data,args)
            av_delay1.append(av_delay)
            total_traffic_in1.append(total_traffic_in)


        f_av_delay0 = interp.interp1d(total_traffic_in0, av_delay0, kind='linear')
        f_av_delay1 = interp.interp1d(total_traffic_in1, av_delay1, kind='linear')

        plot_X.append(xpoints * 100)
        plot_Y.append((f_av_delay0(xpoint1) - f_av_delay1(traffic_points)))

    return plot_X,plot_Y,'% traffic reduction','$\Delta$ in average delay per vehicle (s)'


def plot_av_delay( plot_data_files, args):
    plot_X = []
    plot_Y = []

    for i,data in enumerate(plot_data_files):

        plot_X.append([])
        plot_Y.append([])


        for d in data:
            results = d['Out']
            if 'Run' in results:
                results = results['Run'][0]

            if 'Step' in results:
                N = results['Step'][0]['N']
            else:
                N = results['N']
            av_delay, total_traffic_in = get_av_delay(d,args)
            Q_IN_duration = calc_in_flow_duration(d,results) * args.time_factor
            #print total_traffic_in,Q_IN_duration,(Q_IN_duration / 3600.0),total_traffic_in / (Q_IN_duration / 3600.0)
            plot_Y[-1].append(av_delay)
            if args.x_var == 'N':
                plot_X[-1].append(N)
            else:
                plot_X[-1].append(total_traffic_in / (Q_IN_duration / 3600.0))
        if args.x_var == 'N':
            x_label = 'N (number of time samples)'
        else:
            x_label = 'Network traffic demand (vehicles/hour)'

    return plot_X,plot_Y,x_label,'Average delay per vehicle (s)'

def plot_travel_time(plot_data_files,args):
    plot_X = []
    plot_Y = []

    if args.plot_travel_time_ref is not None:
        ref_file = open_data_file(args.plot_travel_time_ref)
        ref = ref_file['Out']['total_travel_time']
    else:
        ref = None

    for i,data in enumerate(plot_data_files):

        plot_X.append([])
        plot_Y.append([])


        for d in data:
            results = d['Out']
            if 'Run' in results:
                result_set = results['Run']
            else:
                result_set = [results]
            total_travel_time = 0
            for results in result_set:
                total_travel_time += results['total_travel_time']
            if ref is not None:
                plot_Y[-1].append(((total_travel_time / len(result_set)) - ref) / ref * 100)
            else:
                plot_Y[-1].append(total_travel_time / len(result_set))
            if args.x_var == 'N':
                if 'Step' in result_set[0]:
                    N = result_set[0]['Step'][0]['N']
                else:
                    N = result_set[0]['N']
                plot_X[-1].append(N)
            else:
                Q_IN_duration = calc_in_flow_duration(d,result_set[0]) * args.time_factor
                total_traffic_in = calc_total_traffic(d,result_set[0],args.queues)
                plot_X[-1].append(total_traffic_in / (Q_IN_duration / 3600.0))
        if args.x_var == 'N':
            x_label = 'N (number of time samples)'
        else:
            x_label = 'Network traffic demand (vehicles/hour)'
        if args.plot_travel_time_ref is not None:
            y_label = '% increase in total travel time'
        else:
            y_label = 'total travel time (s)'

    return plot_X,plot_Y,x_label,y_label

def plot_parameter(plot,args):

    pl.clf()
    fig, ax = pl.subplots(nrows=1, ncols=1, sharex=True, sharey=False)
    if args.figsize:
        fig.set_size_inches(args.figsize[0], args.figsize[1])
    else:
        fig.set_size_inches(15, 7)
    #start_time = clock_time.time()
    plot_data_files = read_files(args.files)
    #print 'load time:',clock_time.time() - start_time
    titles = []

    plot_X,plot_Y,xlabel,ylabel = plot( plot_data_files, args)

    i=0
    c_i=0
    m_i=0
    l_i=0
    labels=[]
    if args.labels: labels=args.labels
    mevery = args.markevery
    if len(mevery) < len(args.marker):
        mevery = mevery + [mevery[-1]] * (len(args.marker) - len(mevery))
    for plot_i in range(len(plot_Y)):
        if len(labels)>0:
            plot_label = labels[l_i]
        else:
            plot_label = 'plot %d' % i
        if args.marker_fill:
            mfc = args.color[c_i]
        else:
            mfc = 'none'
        if args.marker_color:
            mec = args.color[c_i]
        else:
            mec = 'k'
        h = ax.axhline(0,color='0.6')
        h.set_zorder(0)
        ax.plot(plot_X[plot_i],plot_Y[plot_i],color=args.color[c_i], linestyle=args.linestyle[l_i], label=plot_label,
                marker=args.marker[m_i],markeredgecolor=mec,markerfacecolor=mfc,markevery=mevery[m_i])

        if l_i+1 < len(args.linestyle): l_i += 1
        if c_i+1 < len(args.color): c_i += 1
        if m_i+1 < len(args.marker): m_i += 1
        i += 1
    plot_annotations(ax,args)
    if args.x_limit:
        ax.set_xlim(args.x_limit[0], args.x_limit[1])
    if args.y_limit:
        ax.set_ylim(args.y_limit[0], args.y_limit[1])
    ax.grid()
    if args.x_label != ' ':
        ax.set_xlabel(args.x_label)
    else:
        ax.set_xlabel(xlabel)
    if args.y_label != ' ':
        ax.set_ylabel(args.y_label)
    else:
        ax.set_ylabel(ylabel)
    if not args.no_legend:
        ax.legend(loc='best')
    if args.title:
        pl.title(args.title[0])

    if args.dump_csv is not None:
        table = {}
        for plot_i in range(len(plot_Y)):
            table['plot_y_%d' % plot_i] = plot_Y[plot_i]
            table['plot_x_%d' % plot_i] = plot_X[plot_i]
        frame_data = pd.DataFrame(table)
        write_file(args.dump_csv,frame_data)



def plot_av_travel_time_N(args):
    pl.clf()
    fig, ax = pl.subplots(nrows=1, ncols=1, sharex=True, sharey=False)
    if args.figsize:
        fig.set_size_inches(args.figsize[0], args.figsize[1])
    else:
        fig.set_size_inches(15, 7)
    titles=[]
    i=0
    c_i=0
    av_i = 0
    l_i=0
    labels=[]
    if args.labels: labels=args.labels
    min_TT = 1e9
    plot_data = []
    plot_scatter_X = []
    plot_scatter_Y = []
    plot_data_mf = []
    plot_data_results = []
    time_limit_Y = []
    # for file in args.files:
    #     files = []
    #
    #     path,name = os.path.split(file)
    #     if len(path) > 0: path += '/'
    #
    #     f = open(str(file),'r')
    #     for line in f:
    #         fields = line.split(' ')
    #         if len(fields) > 0:
    #             files.append(path+fields[0].strip())
    #             if len(fields)>1:
    #                 labels.append(fields[1])
    #     f.close()
    #     for file in files:
    #         if os.path.isfile(file):
    #             f = open(str(file),'r')
    #             data.append(json.load(f))
    #             f.close()

    plot_data_files = read_files(args.files)
    if args.plot_travel_time_ref != None:
        ref_file = open_data_file(args.plot_travel_time_ref)
    else:
        ref_file = None
    #print len(plot_data_files)
    for data in plot_data_files:
        #print data

        plot_data.append( dict())
        plot_scatter_Y.append([])
        plot_scatter_X.append([])
        time_limit_Y.append([])
        plot_data_mf.append( dict())
        plot_label=''
        if len(labels)>0: plot_label = labels[l_i]
        annotate=False
        if i < len(args.annotate) and args.annotate[i]=='y':
            annotate=True

        for d in data:
            #print d
            titles.append(d['Title'])
            results = d['Out']
            #print d.keys()
            #print results.keys()
            runs=1
            if 'Run' in results:
                runs = len(results['Run'])
                d_out = results['Run'][0]
                label =  d_out
            else:
                d_out = results
            #print 'Runs=',runs
            #print d_out.keys()
            if args.plot_travel_time_DT:
                N = int(1/d_out['DT'][0])
                #N = results['DT'][0]
            elif 'Step' in d_out:
                if 'N' in d_out['Step'][0]:
                    N = d_out['Step'][0]['N']
                else:
                    N = len(d_out['Step'][0]['t'])-1
                if args.plot_travel_time_maj:
                    N = d_out['Step'][0]['t'][-1]
                #print 'N=',N
            else:
                if 'N' in d_out:
                    N=d_out['N']
                else:
                    N = len(d_out['t'])-1
            #if args.step != None:
            #    if 'Step' in results:
            #        results = d['Out']['Step'][args.step]
            #        label = results['label']


            solve_time=0
            total_travel_time=None
            time_limit = 0
            for run in range(runs):
                if 'Run' in d['Out']:
                    #print 'run=',run
                    results = d['Out']['Run'][run]
                #print results.keys()

                #total_travel_time += calc_total_travel_time(d,results)
                if total_travel_time is not None:
                    if args.minimum[av_i] == 'y':
                        total_travel_time = min(total_travel_time,results['total_travel_time'])
                    else:
                        total_travel_time += results['total_travel_time'] / runs
                else:
                    if args.minimum[av_i] == 'y':
                        total_travel_time = results['total_travel_time']
                    else:
                        total_travel_time = results['total_travel_time'] / runs

                if args.count_time_limit:
                    if 'Step' in results:
                        for step in results['Step']:
                            if step['status'] == 'TIME_LIMIT':
                                time_limit += 1.0 / runs
                    else:
                        if results['status'] == 'TIME_LIMIT':
                            time_limit += 1.0 / runs

                solve_time=0
                if args.plot_cpu_time:
                    if 'Step' in results:
                        for step in results['Step']:
                            if 'solver_runtime' not in step:
                                solve_time+=step['solve_time']
                            else:
                                solve_time+=step['solver_runtime']

                            #print step['solver_runtime']
                            if args.plot_cpu_time:
                                if 'solver_runtime' not in step:
                                    plot_scatter_X[-1].append(step['solve_time'])
                                else:
                                    plot_scatter_X[-1].append(step['solver_runtime'])
                                plot_scatter_Y[-1].append(results['total_travel_time'])
                        #print len(results['Step'])

                        solve_time /= len(results['Step'])
                        #print 'solver_runtime=',solve_time
                    else:
                        solve_time = d['Out']['solver_runtime']/runs

                #ax.plot(N,results['total_travel_time'],'x',c=args.color[c_i])
                if not args.plot_cpu_time:
                    plot_scatter_Y[-1].append(results['total_travel_time'])
                    plot_scatter_X[-1].append(N)

                #print results['total_travel_time']
                if len(plot_label)==0:
                    plot_label = '$'+label.split('$')[1]+'$'

                #time = results['t']
                #total_time = time[-1] - time[0]
                min_TT = min(results['total_travel_time'],min_TT)
            #av_delay,total_traffic_in = get_av_delay(d,args)

            time_limit_Y[-1].append(time_limit)

            if args.plot_cpu_time:
                plot_data[-1][solve_time]=total_travel_time/runs
            else:
                plot_data[-1][N]=total_travel_time # total_travel_time/runs
            #print total_travel_time/runs
            #print min_TT
            if annotate and 'plan' in d['Out']:
                if args.plot_cpu_time:
                    plot_data_mf[-1][solve_time]=int(d['Out']['plan']['major_frame'])
                else:
                    plot_data_mf[-1][N]=int(d['Out']['plan']['major_frame'])
                #print results['plan']['major_frame']
            else:
                if args.plot_cpu_time:
                    plot_data_mf[-1][solve_time]=0
                else:
                    plot_data_mf[-1][N]=0
        i+=1
        c_i+=1
        if av_i + 1 < len(args.minimum):
            av_i += 1

    if ref_file != None:
        min_TT = ref_file['Out']['total_travel_time']
        #min_TT = calc_total_travel_time(ref_file,ref_file['Out']) #get_av_delay(ref_file,args)
    # print 'time_limit_Y:',time_limit_Y
    i=0
    c_i=0
    m_i=0
    l_i=0
    labels=[]
    if args.labels: labels=args.labels
    for plot_i,plot in enumerate(plot_data):
        if len(labels)>0:
            plot_label = labels[l_i]
        else:
            plot_label = '$'+label.split('$')[1]+'$'
        X = sorted(plot)
        Y = [((plot[x]-min_TT)/min_TT)*100 for x in X]
        ax.plot(X,Y,color=args.color[c_i], linestyle=args.linestyle[l_i], label=plot_label,marker=args.marker[m_i],markerfacecolor='None')
        if args.count_time_limit:
            ax.plot(X,time_limit_Y[plot_i],color=args.color[c_i],marker=args.marker[m_i],markerfacecolor='None')
        if args.plot_scatter:
            ax.plot(plot_scatter_X[plot_i],((np.array(plot_scatter_Y[plot_i])-min_TT)/min_TT)*100 ,'.',c=args.color[c_i])
        for j,x in enumerate(sorted(plot_data_mf[i])):
            if plot_data_mf[i][x]>0:
                label_test=True
                if args.x_limit and (X[j] < args.x_limit[0] or X[j] > args.x_limit[1]):
                    label_test=False
                if args.y_limit and (Y[j] < args.y_limit[0] or Y[j] > args.y_limit[1]):
                    label_test=False
                if label_test == True:
                    ax.text(X[j],Y[j],plot_data_mf[i][x],size=8,color=args.color[c_i])

        if l_i+1 < len(args.linestyle): l_i += 1
        if c_i+1 < len(args.color): c_i += 1
        if m_i+1 < len(args.marker): m_i += 1
        i += 1

    plot_annotations(ax,args)
    if args.x_limit:
        ax.set_xlim(args.x_limit[0], args.x_limit[1])
    if args.y_limit:
        ax.set_ylim(args.y_limit[0], args.y_limit[1])
    ax.grid()
    if args.plot_cpu_time:
        ax.set_xlabel('CPU Solve Time')
    elif args.plot_travel_time_maj:
        ax.set_xlabel('Major frame time (s)')
    else:
        ax.set_xlabel('N (number of time samples)')
    ax.set_ylabel('% increase in total travel time') #ax.set_ylabel('Total Travel Time')
    if not args.no_legend:
        ax.legend(loc='best')
    if args.title:
        pl.title(args.title[0])
    #else:
    #    if args.plot_cpu_time:
    #        pl.title('CPU Time vs % increase in total travel time' )
    #    else:
    #        pl.title('Number of time samples vs % increase in total travel time' )



# def plot_travel_time(args):
#     pl.clf()
#     fig, ax = pl.subplots(nrows=1, ncols=1, sharex=True, sharey=False)
#     if args.figsize:
#         fig.set_size_inches(args.figsize[0], args.figsize[1])
#     else:
#         fig.set_size_inches(15, 7)
#     titles=[]
#     i=0
#     c_i=0
#
#     l_i=0
#     labels=[]
#     if args.labels: labels=args.labels
#     min_TT = 1e9
#     plot_data = []
#     plot_data_mf = []
#     plot_data_results = []
#     for file in args.files:
#         files = []
#
#         path,name = os.path.split(file)
#         if len(path) > 0: path += '/'
#
#         f = open(str(file),'r')
#         for line in f:
#             fields = line.split(' ')
#             if len(fields) > 0:
#                 files.append(path+fields[0].strip())
#                 if len(fields)>1:
#                     labels.append(fields[1])
#         f.close()
#         data = []
#         for file in files:
#             if os.path.isfile(file):
#                 f = open(str(file),'r')
#                 data.append(json.load(f))
#                 f.close()
#
#         plot_data.append( dict())
#         plot_data_mf.append( dict())
#         plot_label=''
#         if len(labels)>0: plot_label = labels[l_i]
#         annotate=False
#         if i < len(args.annotate) and args.annotate[i]=='y':
#             annotate=True
#
#         for d in data:
#
#             titles.append(d['Title'])
#             results = d['Out']
#             label =  d['Out']['label']
#             if args.plot_travel_time_DT:
#                 N = int(1/results['DT'][0])
#                 #N = results['DT'][0]
#
#             elif 'Step' in results:
#
#                 N = len(d['Out']['Step'][0]['t'])-1
#             else:
#                 N = len(results['t'])-1
#             if args.step != None:
#                 if 'Step' in results:
#                     results = d['Out']['Step'][args.step]
#                     label = results['label']
#
#             total_travel_time = calc_total_travel_time(d,results)
#
#             if len(plot_label)==0:
#                 plot_label = '$'+label.split('$')[1]+'$'
#
#             time = results['t']
#             total_time = time[-1] - time[0]
#
#             plot_data[-1][N]=total_travel_time
#
#             if annotate and 'plan' in results:
#                 plot_data_mf[-1][N]=results['plan']['major_frame']
#             else:
#                 plot_data_mf[-1][N]=0
#             min_TT = min(total_travel_time,min_TT)
#         i+=1
#     i=0
#     c_i=0
#
#     l_i=0
#     labels=[]
#     if args.labels: labels=args.labels
#     for plot in plot_data:
#         if len(labels)>0:
#             plot_label = labels[l_i]
#         else:
#             plot_label = '$'+label.split('$')[1]+'$'
#         X = sorted(plot)
#         Y = [((plot[x]-min_TT)/min_TT)*100 for x in X]
#         ax.plot(X,Y,c=args.color[c_i], linestyle=args.linestyle[l_i], label=plot_label,marker=args.marker)
#         for j,x in enumerate(sorted(plot_data_mf[i])):
#             if plot_data_mf[i][x]>0:
#                 label_test=True
#                 if args.x_limit and (X[j] < args.x_limit[0] or X[j] > args.x_limit[1]):
#                     label_test=False
#                 if args.y_limit and (Y[j] < args.y_limit[0] or Y[j] > args.y_limit[1]):
#                     label_test=False
#                 if label_test == True:
#                     ax.text(X[j],Y[j],plot_data_mf[i][x],size=8,color=args.color[c_i])
#         if l_i+1 < len(args.linestyle): l_i += 1
#         if c_i+1 < len(args.color): c_i += 1
#         i += 1
#
#     if args.x_limit:
#         ax.set_xlim(args.x_limit[0], args.x_limit[1])
#     if args.y_limit:
#         ax.set_ylim(args.y_limit[0], args.y_limit[1])
#     ax.grid()
#     ax.set_xlabel('N (number of time samples)')
#     ax.set_ylabel('% increase in total travel time') #ax.set_ylabel('Total Travel Time')
#     ax.legend(loc='best')
#     if args.title:
#         pl.title(args.title[0])
#     else:
#         pl.title('Number of time samples vs % increase in total travel time' )
#


def plot_cpu_time(args):
    pl.clf()
    fig, ax = pl.subplots(nrows=1, ncols=1, sharex=True, sharey=False)
    if args.figsize:
        fig.set_size_inches(args.figsize[0], args.figsize[1])
    else:
        fig.set_size_inches(15, 7)
    titles=[]
    i=0
    c_i=0
    l_i=0
    labels=[]
    if args.labels: labels=args.labels
    for file in args.files:
        files = []
        path,name = os.path.split(file)
        if len(path) > 0: path += '/'
        f = open(str(file),'r')
        for line in f:
            fields = line.split(' ')
            if len(fields) > 0:

                files.append(path+fields[0].strip())
                if len(fields)>1:
                    labels.append(fields[1])
        f.close()
        data = []
        for file in files:
            if os.path.isfile(file):
                f = open(str(file),'r')
                data.append(json.load(f))
                f.close()

        plot_data = dict()
        plot_label=''
        if len(labels)>0: plot_label = labels[l_i]
        plot_X=[]
        plot_Y=[]
        for d in data:


            titles.append(d['Title'])
            results = d['Out']
            label =  d['Out']['label']
            if 'Step' in results:
                N = len(d['Out']['Step'][0]['t'])-1
            else:
                N = len(results['t'])-1



            if args.step != None:
                if 'Step' in results:
                    results = d['Out']['Step'][args.step]
                    label = results['label']
            #solve_time=0
            #if 'Step' in results:
            #    for step in results['Step']:
            #        solve_time+=step['solve_time']
            #solve_time/=len(results['Step'])
            total_travel_time = calc_total_travel_time(d,results)
            solve_time = results['solve_time']
            objval=results['objval']
            if len(plot_label)==0:
                plot_label = '$'+label.split('$')[1]+'$'




            time = results['t']
            total_time = time[-1] - time[0]

            plot_data[solve_time]=total_travel_time
            #if args.x_limit != None:
            #    if solve_time>args.x_limit[1]:
            #        break

            plot_X.append(solve_time)
            plot_Y.append(total_travel_time)
            #plot_Y.append(N)

        X = sorted(plot_data)
        Y = [plot_data[x] for x in X]
        #ax.plot(X,Y,c=args.color[c_i], label=plot_label,marker='x')
        ax.plot(plot_X,plot_Y,c=args.color[c_i], linestyle=args.linestyle[i], label=plot_label,marker=args.marker)
        if i+1 < len(args.linestyle): i += 1
        if c_i+1 < len(args.color): c_i += 1
        if l_i+1 < len(labels): l_i += 1

    if args.x_limit:
        ax.set_xlim(args.x_limit[0], args.x_limit[1])
    if args.y_limit:
        ax.set_ylim(args.y_limit[0], args.y_limit[1])
    ax.grid()
    ax.set_xlabel('CPU time')
    ax.set_ylabel('Total travel time')
    if not args.no_legend:
        ax.legend(loc='best')
    if args.title:
        pl.title(args.title[0])
    else:
        pl.title('CPU time vs Total Travel Time for Network' )


def plot_phase_offset(args):
    pl.clf()
    fig, ax = pl.subplots(nrows=1, ncols=1, sharex=True, sharey=False)
    if args.figsize:
        fig.set_size_inches(args.figsize[0], args.figsize[1])
    else:
        fig.set_size_inches(15, 7)
    titles=[]
    i=0
    c_i=0
    l_i=0
    labels=[]
    if args.labels: labels=args.labels
    for file in args.files:
        files = []
        path,name = os.path.split(file)
        if len(path) > 0: path += '/'
        f = open(str(file),'r')
        for line in f:
            fields = line.split(' ')
            if len(fields) > 0:
                files.append(path+fields[0].strip())
                if len(fields)>1:
                    labels.append(fields[1])

        f.close()
        data = []
        for file in files:
            if os.path.isfile(file):
                f = open(str(file),'r')
                data.append(json.load(f))
                f.close()

        plot_data = dict()
        plot_label=''
        if len(labels)>0: plot_label = labels[l_i]
        plot_X=[]
        plot_Y=[]
        for k,d in enumerate(data):


            titles.append(d['Title'])
            results = d['Out']
            label =  d['Out']['label']
            if 'Step' in results:
                N = len(d['Out']['Step'][0]['t'])-1
            else:
                N = len(results['t'])-1



            if args.step != None:
                if 'Step' in results:
                    results = d['Out']['Step'][args.step]
                    label = results['label']
            #solve_time=0
            #if 'Step' in results:
            #    for step in results['Step']:
            #        solve_time+=step['solve_time']
            #solve_time/=len(results['Step'])
            total_travel_time = calc_total_travel_time(d,results)
            #solve_time = results['solve_time']
            #objval=results['objval']

            if 'DT_offset' in results:

                if args.step == None and 'Step' in results:
                    phase = d['Out']['Step'][0]['DT_offset']

                else:
                    phase = results['DT_offset']

            else:

                phase = 0.1*k

            if len(plot_label)==0:
                plot_label = '$'+label.split('$')[1]+'$'




            time = results['t']
            total_time = time[-1] - time[0]

            #plot_data[solve_time]=total_travel_time
            #if args.x_limit != None:
            #    if solve_time>args.x_limit[1]:
            #        break

            plot_X.append(phase)
            plot_Y.append(total_travel_time)
            #plot_Y.append(N)

        #X = sorted(plot_data)
        #Y = [plot_data[x] for x in X]
        #ax.plot(X,Y,c=args.color[c_i], label=plot_label,marker='x')
        ax.plot(plot_X,plot_Y,c=args.color[c_i], linestyle=args.linestyle[i], label=plot_label,marker=args.marker)
        if i+1 < len(args.linestyle): i += 1
        if c_i+1 < len(args.color): c_i += 1
        if l_i+1 < len(labels): l_i += 1

    if args.x_limit:
        ax.set_xlim(args.x_limit[0], args.x_limit[1])
    if args.y_limit:
        ax.set_ylim(args.y_limit[0], args.y_limit[1])
    ax.grid()
    ax.set_xlabel('Phase offset (s)')
    ax.set_ylabel('Total travel time')
    if not args.no_legend:
        ax.legend(loc='best')
    if args.title:
        pl.title(args.title[0])
    else:
        pl.title('Phase Offset vs Total Travel Time for Network' )

def plot_vars(args): #data_sets,params,colors,line_styles,steps):
    pl.clf()
    fig, axes = pl.subplots(nrows=len(args.plot_vars), ncols=1, sharex=True, sharey=False)
    if args.figsize is None:
        fig.set_size_inches(15, 4*len(args.plot_vars))
    else:
        fig.set_size_inches(args.figsize[0], args.figsize[1]*len(args.plot_vars))
    ax=axes
    if not isinstance(ax, np.ndarray): ax=[axes]

    labels=[]
    data_sets = []
    files=[]


    for file in args.files:
        data_sets.append(open_data_file(file))
        labels.append(file)
    if args.labels: labels=args.labels
    xl_i=0
    yl_i=0

    for i,var in enumerate(args.plot_vars):
        k_step=0
        c_i=0
        l_i=0
        ls_i=0
        m_i=0
        for j,data in enumerate(data_sets):
            results = data['Out']

            if 'Run' in results:
                if args.run != None and len(args.run)>j:
                    results = results['Run'][args.run[j]]
                else:
                    results = results['Run'][0]
            plots = 1
            if args.step != None and len(args.step)>j and 'Step' in results:
                #print args.step[j],len(results['Step']),
                plots = max(1,min(len(results['Step']),len(args.step[j])))
                #print plots
            run_results = results
            for step_i,plot in enumerate(range(plots)):
                #print 'step:',step_i
                if 'Step' in run_results and args.step is not None and  len(args.step[j]) > 0:
                    #print 'using step:',step_i
                    results = run_results['Step'][args.step[j][step_i]]
                ls=args.linestyle[ls_i]
                col=args.color[c_i]
                marker = args.marker[m_i]
                label = labels[l_i]
                xlabel=''
                ylabel=''
                if args.x_label is not None:
                    xlabel = args.x_label[xl_i]
                if args.y_label is not None:
                    ylabel = args.y_label[yl_i]
                t=[x * args.time_factor for x in results['t']]

                if var[0:2]=='l_':
                    l = int((var.split('_'))[1])

                    if l < len(data['Lights']):
                        num_p = len(data['Lights'][l]['P_MAX'])
                        N=len(t)
                        p = [ [ results['d_{%d,%d}' % (l,k)][0] ]*N for k in range(num_p)]

                        for k in range(num_p):
                            P_MAX=data['Lights'][l]['P_MAX'][k]
                            P_MIN=data['Lights'][l]['P_MIN'][k]
                            for n,pk in enumerate(results['p_{%d,%d}' % (l,k)]):
                                if n==0 and p[k][n]==0: p[k][n]=P_MIN
                                if pk<1e-6:
                                    p[k][n]=results['d_{%d,%d}' % (l,k)][n]

                                else:
                                    if n>0: p[k][n]=p[k][n-1]

                        c = [ sum([p[k][n] for k in range(num_p) ]) for n in range(N)]

                        pl_p = [ [ 0 ]*N for k in range(num_p+1)]
                        if k>2:
                            pl_p[0] = [-c[n]/2 for n in range(N)]

                            ax[i].plot(t,[x+j*P_MAX*num_p+P_MAX for x in pl_p[0]],  marker=marker, linestyle = ls, color=col)
                            for k in range(1,num_p+1):
                                pl_p[k] = [pl_p[k-1][n]+p[k-1][n] for n in range(N)]
                                ax[i].plot(t,[x+j*P_MAX*num_p+P_MAX for x in pl_p[k]], marker=marker, linestyle = ls, color=col)
                        else:
                            ax[i].plot(t,[-x+j*P_MAX*2+P_MAX for x in p[0]],  marker=marker,  linestyle = ls, color=col)
                            ax[i].plot(t,[x+j*P_MAX*2+P_MAX for x in p[1]],  marker=marker, linestyle = ls, color=col)
                            ax[i].plot(t,[j*P_MAX*2+P_MAX for x in p[1]],  marker=marker, linestyle = ls, color=col)


                elif var[0:2]=='p_' :

                    l = int(((var[3:-1].split('_'))[0]).split(',')[0])
                    k = int(((var[3:-1].split('_'))[0]).split(',')[1])
                    if l < len(data['Lights']):
                        num_p = len(data['Lights'][l]['P_MAX'])
                        N=len(t)
                        p = results['p_{%d,%d}' % (l,k)]
                        p_f = interp.interp1d(t,p,kind='zero')

                        # P_MIN=data['Lights'][l]['P_MIN'][k]
                        # for n,pk in enumerate(results['p_{%d,%d}' % (l,k)]):
                        #     if n==0 and p[n]==0: p[n]=P_MIN
                        #     if pk<1e-6:
                        #         p[n]=results['d_{%d,%d}' % (l,k)][n]
                        #
                        #     else:
                        #         if n>0: p[n]=p[n-1]
                    t_samp = np.linspace(t[0],t[-1],N*100)
                    ax[i].plot(t_samp,p_f(t_samp), label=results['label'], marker=None, linestyle = ls, color=col)
                    ax[i].plot(t,p, marker=marker, linestyle = ' ', color=col)
                    ax[i].set_ylim(-0.1,1.1)
                elif var[0:2]=='d_' :

                    l = int(((var[3:-1].split('_'))[0]).split(',')[0])
                    k = int(((var[3:-1].split('_'))[0]).split(',')[1])
                    if l < len(data['Lights']):
                        num_p = len(data['Lights'][l]['P_MAX'])
                        N=len(t)
                        d = results['d_{%d,%d}' % (l,k)]
                        d_f1 = interp.interp1d(t,d,kind='zero')
                        d_f2 = interp.interp1d(t,d)

                        P_MAX=data['Lights'][l]['P_MAX'][k]
                        # for n,pk in enumerate(results['p_{%d,%d}' % (l,k)]):
                        #     if n==0 and p[n]==0: p[n]=P_MIN
                        #     if pk<1e-6:
                        #         p[n]=results['d_{%d,%d}' % (l,k)][n]
                        #
                        #     else:
                        #         if n>0: p[n]=p[n-1]
                    os_factor = 100
                    t_samp = np.linspace(t[0],t[-1],N*os_factor)
                    d_switch = interp.interp1d(t,[0 if -1e-6 < d[nx + 1] < 1e-6 or d[nx] == d[nx +1] else 1 for nx in range(len(t)-1)] + [0],kind='zero')
                    d_f = [d_f1(tx) if d_switch(tx)==0 else d_f2(tx) for tx in t_samp]
                    ax[i].plot(t_samp,d_f, label=results['label'], marker=None, linestyle = ls, color=col)
                    ax[i].plot(t,d, marker=marker, linestyle = ' ', color=col)
                    ax[i].set_ylim(-0.1,P_MAX+0.1)
                elif var in results.keys():
                    #if var[0] == 'l':
                    if var[0:3]=='q_{':
                        DT = results['DT']
                        #ax[i].plot(t,[results[var][0]]+[results[var][x]/DT[x-1] for x in range(1,len(t))],marker=marker, label=label, linestyle = ls, color=col) #/DT[x_i]
                        if args.io_vars_as_rate == True:
                            over_samp = 100
                            var_rate = [results[var][x] / DT[x] for x in range(0, len(t))]
                            plot_f = interp.interp1d(t,var_rate,kind='zero')
                            t_samp = np.linspace(t[0],t[-1],len(t) * over_samp)
                            ax[i].plot(t_samp,plot_f(t_samp), label=label, linestyle = ls, color=col,markevery=over_samp)
                            ax[i].plot(t, var_rate, marker=marker, label=label, linestyle = ' ', color=col)
                            #ax[i].plot(t,[results[var][x]/DT[x] for x in range(0,len(t))],marker=marker, label=label, linestyle = ls, color=col)
                        else:
                            ax[i].plot(t,[results[var][x] for x in range(0,len(t))],marker=marker, label=label, linestyle = ls, color=col)
                    else:
                        ax[i].plot(t,[results[var][x] for x in range(len(t))],marker=marker, label=label, linestyle = ls, color=col)
                    #else:
                    #    ax[i].plot(t,results[var], color=colors[j])
                else:
                    if var[0:3]=='obj':
                        wh_test = None
                        if var[4] != '{':
                            var_str = var.split('_')[1] + '_' +  var.split('_')[2]
                            qvar = results[var_str]

                        else:
                            f_ij = var.split('{')[1][0:-1].split(',')
                            # print f_ij
                            f_i = int(f_ij[0])
                            f_j = int(f_ij[1])
                        # print 'obj: %d,%d' % (f_i,f_j)
                            qvar = results['f_{%d,%d}' % (f_i,f_j)]
                            wh_ij = 'wh_{%d,%d}' % (f_i,f_j)
                            if wh_ij in results:
                                wh_test = results[wh_ij]
                        T_MAX = t[-1]
                        beta = results['beta']
                        obj_val = [(T_MAX - t_x + 1) * qvar[t_i] for t_i, t_x in enumerate(t)]
                        obj_val_cumu = [sum(obj_val[0:t_i]) for t_i in range(len(t))]
                        ax[i].plot(t, obj_val_cumu, marker=marker, label=label,
                                  linestyle=ls, color=col)
                        if wh_test is not None:
                            wh = []
                            t_wh = []
                            for t_i in range(len(t)):
                                if wh_test[t_i] == 1:
                                    wh.append(obj_val_cumu[t_i])
                                    t_wh.append(t[t_i])
                            ax[i].plot(t_wh,wh, marker='x', label='withholding',
                                   linestyle=' ', color='k')
                        if args.y_limit != None:
                            ax[i].set_ylim(args.y_limit[0], args.y_limit[1])

                if ylabel == ' ':
                    if '_' in var:
                        ax[i].set_ylabel(r'$%s_{%s}$' % (var.split('_')[0],var.split('_')[1]),fontsize=16)
                    if var =='DT':
                        ax[i].set_ylabel(r'$\Delta t$',fontsize=12)
                    else:
                        ax[i].set_ylabel(var,fontsize=16)
                else:
                    ax[i].set_ylabel(ylabel)
                if xlabel == ' ':
                    ax[i].set_xlabel('time (s)')
                else:
                    ax[i].set_xlabel(xlabel)

                if var in results.keys():
                    if var[0:3] == 'fij' or var[0:3] == 'fxy':
                        ax[i].set_ylim(-1,max(results[var]))

                    elif var[0] == 'q' or var[0] == 'f':
                        if var[2] != '{':
                            #ax[i].set_ylim(-1,data['Queues'][int(var[3:].split(',')[0])]['Q_MAX']+2)
                        #else:
                            ax[i].set_ylim(-1,data['Queues'][int(var[2:])]['Q_MAX']+2)
                    elif var[0:2] == 'dq':
                        if var[3] == '{':
                            ax[i].set_ylim(-1,data['Queues'][int(var[4:].split(',')[0])]['Q_MAX']+2)
                        else:
                            ax[i].set_ylim(-1,data['Queues'][int(var[3:])]['Q_MAX']+2)

                    elif var[0] == 'd' and var[1] != 'q':
                        # lp = var[3:-1].split(',')
                        # ax[i].set_ylim(-1,data['Lights'][int(lp[0])]['P_MAX'][int(lp[1])]+2)
                        None
                    elif var[0] == 'l':
                        l = int(var[2:])
                        ax[i].set_ylim(-1,len(data['Lights'][l]['P_MAX']) )
                    elif var[0] == 'p':
                        ax[i].set_ylim(-0.1,1.1)
                    if args.y_limit is not None:
                        ax[i].set_ylim(args.y_limit[0],args.y_limit[1])
                    #else:
                    #    ax[i].set_ylim(0,1)
                if not args.no_legend:
                    ax[i].legend(loc='best')
                if args.x_limit != None:
                    ax[i].set_xlim(args.x_limit[0],args.x_limit[1])
                ax[i].grid(True)
                if ls_i+1 < len(args.linestyle): ls_i += 1
                if c_i+1 < len(args.color): c_i += 1
                if l_i+1 < len(labels): l_i += 1
                if m_i+1 < len(args.marker): m_i += 1
        if xl_i+1 < len(args.x_label): xl_i += 1
        if yl_i+1 < len(args.y_label): yl_i += 1

    if args.title:
        pl.title(args.title[0])

def plot_flow_profiles(args): #data_sets,params,colors,line_styles,steps):

    data = open_data_file(args.files[0])
    time = data['Out']['t']
    N = len(time)
    if 'Flow_Weights' in data:
            flow_weights = data['Flow_Weights']
            for n,t in enumerate(time):
                for f in flow_weights:

                    if n==0:
                        flow_weights[f]['wt']=[0]*N
                    if t > flow_weights[f]['start'] and t <= flow_weights[f]['end']:
                        flow_weights[f]['wt'][n]=flow_weights[f]['weight']
                    else:
                        flow_weights[f]['wt'][n]=0
                    if n>1:
                        if t > flow_weights[f]['start'] and time[n-1] < flow_weights[f]['start']:
                            flow_alpha = (flow_weights[f]['start'] - time[n-1]) / (t - time[n-1])
                            flow_weights[f]['wt'][n] *= flow_alpha
                        if t > flow_weights[f]['end'] and time[n-1] < flow_weights[f]['end']:
                            flow_alpha = (flow_weights[f]['end'] - time[n-1]) / (t - time[n-1])
                            flow_weights[f]['wt'][n-1] *= flow_alpha
    else:
        print 'no flow weights in file'
        return

    Q_IN_weight = []
    for i,q in enumerate(data['Queues']):
        if 'weights' in q:
            Q_IN_weight.append([0]*N)
            for w in q['weights']:
                for n in range(N):
                    Q_IN_weight[-1][n]+=flow_weights[w]['wt'][n]
                    #if (args.Q_IN_limit or data.get('Flow_Weight_Q_IN_limit',False)) and Q_IN_weight[i][n] > 1.0:
                    #    Q_IN_weight[i][n] = 1.0

    y_max = max(max(Q_IN_weight))
    if args.labels:
        labels = args.labels
    else:
        labels = ['A','B','C','D','E','F','G','H','I']
    vars = []
    for i,var in enumerate(Q_IN_weight):
        data['Out'][labels[i]] = Q_IN_weight[i]
        vars.append(labels[i])
    pl.clf()
    fig, ax = pl.subplots(nrows=len(vars), ncols=1, sharex=True, sharey=False)
    if args.figsize is None:
        fig.set_size_inches(15, 4*len(vars))
    else:
        fig.set_size_inches(args.figsize[0], args.figsize[1]*len(vars))
    if not isinstance(ax, np.ndarray): ax=[ax]


    xl_i=0
    yl_i=0
    c_i=0
    l_i=0
    ls_i=0
    m_i=0

    for i,var in enumerate(vars):


        results = data['Out']


        ls=args.linestyle[ls_i]
        col=args.color[c_i]
        marker = args.marker[m_i]
        label = labels[l_i]
        xlabel=''
        ylabel=''
        if args.x_label is not None:
            xlabel = args.x_label[xl_i]
        if args.y_label is not None:
            ylabel = args.y_label[yl_i]
        t=results['t']
        if var in results.keys():
            x_data = results[var]
            ax[i].plot([t[x] * args.time_factor for x in range(len(x_data))],x_data,marker=marker, linestyle = ls, color=col)

        if ylabel == ' ':
            ax[i].set_ylabel(var+'      ',fontsize=16,rotation=0)
        else:
            ax[i].set_ylabel(ylabel+'  ',rotation=0)

        if args.y_limit != None:
            ax[i].set_ylim(args.y_limit[0],args.y_limit[1])

        if not args.no_legend:
            ax[i].legend(loc='best')
        if args.x_limit != None:
            ax[i].set_xlim(args.x_limit[0],args.x_limit[1])
        #ax[i].yaxis.set_ticks(np.arange(0, int(y_max)+1,1))
        ax[i].grid(True)

        if ls_i+1 < len(args.linestyle): ls_i += 1
        if c_i+1 < len(args.color): c_i += 1
        if l_i+1 < len(labels): l_i += 1
        if m_i+1 < len(args.marker): m_i += 1
    if xlabel == ' ':
        ax[-1].set_xlabel('time (s)')
    else:
        ax[-1].set_xlabel(xlabel)
    if xl_i+1 < len(args.x_label): xl_i += 1
    if yl_i+1 < len(args.y_label): yl_i += 1

    if args.title:
        pl.title(args.title[0])

def dump_keys(args): #data_sets,params,colors,line_styles,steps):


    data_sets,loaded_file_sets = read_files(args.files,return_file_sets=True)

    for file_i,data_files in enumerate(data_sets):
        for j,data in enumerate(data_files):
            file_name = loaded_file_sets[file_i][j]
            print 'File:',file_name
            print '\n  '.join(data['Out'].keys())
            if 'Run' in data['Out']:
                for i,run in enumerate(data['Out']['Run']):
                    print '====Run',i,'\n','\n    '.join(run.keys())
                    if 'Step' in run:
                        for j,step in enumerate(run['Step']):
                            print '------Step',j,'\n', '\n      '.join(step.keys())



def dump_stats(args):

    data_files = read_files(args.files)
    data = []
    for i,file in enumerate(data_files):
        data.append(file)

    # for file in args.files:
    #     if file.endswith('.json'):
    #         files.append(file)
    #     else:
    #         path,name = os.path.split(file)
    #         if len(path) > 0: path += '/'
    #         f = open(str(file),'r')
    #         for line in f:
    #             fields = line.split(' ')
    #             if len(fields) > 0:
    #
    #                 files.append(path+fields[0].strip())
    #
    #         f.close()
    #     data = []
    #     loaded_files=[]
    #     for file in files:
    #         if os.path.isfile(file):
    #             loaded_files.append(os.path.split(file)[1])
    #             f = open(str(file),'r')
    #             data.append(json.load(f))
    #             f.close()

    # for file in args.files:
    #     if file.endswith('.json'):
    #         files.append(file)
    #     else:
    #         f = open(str(file),'r')
    #         for line in f:
    #             fields = line.split(' ')
    #             if len(fields) > 2:
    #                 files.append(fields[2])
    #             else:
    #                 files.append(fields[0].strip())
    #         f.close()
    # loaded_files=[]
    # for file in files:
    #     if os.path.isfile(file):
    #         loaded_files.append(file)
    #         f = open(str(file),'r')
    #         data.append(json.load(f))
    #         f.close()



    for d in data:
        if 'Run' in d['Out']:
            for run in d['Out']['Run']:
                min_travel_time,total_q_in = calc_min_travel_time({'Out':run},args)
        else:
            min_travel_time,total_q_in = calc_min_travel_time(d,args)
        if args.debug: print 'Min Travel Time for network: %f  Total volume of traffic through network: %f' % (min_travel_time,total_q_in)

    print 'File \t\t\t   Run time   Travel time   Delay   Av delay   Stops   N   Accu       Status        Obj  Objval'

    for i,d in enumerate(data):
        if 'Run' in d['Out']:
            results = d['Out']['Run'][0]
        else:
            results = d['Out']
        label = results['label']

        if args.step != None:
            if 'Step' in results:
                if len(results['Step']) > args.step:
                    results = d['Out']['Step'][args.step]
                    label = results['label']
        if 'status' in results:
            status = results['status']
        else:
            status = 'unknown'
        if 'Step' in results:
            N = len(results['Step'][0]['t'])-1
            if 'status' in results['Step'][0]:
                status=''
                for step in results['Step']:
                    status += step['status'][0]
        else:
            N = len(results['t'])-1
        total_travel_time = calc_total_travel_time(d,results)
        total_stops = calc_total_stops(d,results)
        min_travel_time,total_q_in = calc_min_travel_time(d,args)
        accuracy = results['accuracy']
        if 'obj' in results:
            obj = results['obj']
        else:
            obj = ''
        objval = results['objval']
        print '%25s %9.1f %13.1f %7.1f %10.1f %7.1f %4d %5.2f %12s %10s %7.1f' % (loaded_files[i],results['solve_time'],total_travel_time,
                                                                  total_travel_time-min_travel_time,
                                                                  (total_travel_time-min_travel_time) / total_q_in,
                                                                  total_stops,N,accuracy,status,obj,objval)

def dump_sample_vars(args): #data_sets,params,colors,line_styles,steps):

    # data_sets = []
    # files=[]
    # if args.labels: labels=args.labels
    #
    # for file in args.files:
    #     if file.endswith('.json'):
    #         files.append(file)
    #     else:
    #         f = open(str(file),'r')
    #         for line in f:
    #             fields = line.split(' ')
    #             if len(fields) > 2:
    #                 files.append(fields[2])
    #         f.close()
    # loaded_files=[]
    # for file in files:
    #     if os.path.isfile(file):
    #         loaded_files.append(file)
    #         f = open(str(file),'r')
    #         data_sets.append(json.load(f))
    #         f.close()

    data_sets,loaded_file_sets = read_files(args.files,return_file_sets=True)

    pd.options.display.float_format = '{:20,.2f}'.format
    for file_i,data_files in enumerate(data_sets):

        for j,data in enumerate(data_files):

            # results = data['Out']
            # if args.step != None:
            #     if 'Step' in results:
            #         results = data['Out']['Step'][args.step]

            runs = 0
            results = data['Out']
            if 'Run' in results:
                runs = len(data['Out']['Run'])
                if args.run != None:
                    results = data['Out']['Run'][args.run[0]]
                else:
                    results = data['Out']['Run'][0]
            if args.step != None:
                if 'Step' in results:
                    results = results['Step'][args.step[0][0]]
            for i,var in enumerate(args.dump_sample_vars):
                if var in results.keys():
                    len_t = len(results[var])
                    break
            #for i,var in enumerate(args.dump_vars):
            #        if var in results.keys(): print var,'=',results[var]
            #for k in range(len(t)):
            #    for i,var in enumerate(args.dump_vars):
            #        if var in results.keys(): print '%5.2f' % results[var][k],
            #    print
            table = np.zeros((len(args.dump_sample_vars),len_t))
            for i,var in enumerate(args.dump_sample_vars):
                if var in results.keys():
                    var_data = results[var]
                    if var == 'DT':  var_data = var_data[:-1]
                    table[i:] = var_data
            #pd.set_option('display.width', 2000)
            print loaded_file_sets[file_i][j]
            pd.set_option('display.max_columns', 500)
            display(pd.DataFrame(table,index=args.dump_sample_vars))

def dump_vars(args): #data_sets,params,colors,line_styles,steps):

    # data_sets = []
    # files=[]
    # if args.labels: labels=args.labels
    #
    # for file in args.files:
    #     if file.endswith('.json'):
    #         files.append(file)
    #     else:
    #         f = open(str(file),'r')
    #         for line in f:
    #             fields = line.split(' ')
    #             if len(fields) > 2:
    #                 files.append(fields[2])
    #         f.close()
    # loaded_files=[]
    # for file in files:
    #     if os.path.isfile(file):
    #         loaded_files.append(file)
    #         f = open(str(file),'r')
    #         data_sets.append(json.load(f))
    #         f.close()

    data_sets,loaded_file_sets = read_files(args.files,return_file_sets=True)

    pd.options.display.float_format = '{:20,.5g}'.format
    table = {}
    file_names = []
    for file_i,data_files in enumerate(data_sets):

        #table = np.zeros((len(data_files),len(args.dump_vars)))

        for j,data in enumerate(data_files):
            runs = 0
            results = data['Out']
            result_list = []
            file_name = loaded_file_sets[file_i][j]
            column_tag = []
            #print file_name
            if 'Run' in results:
                runs = len(data['Out']['Run'])

                if args.run != None:
                    result_list.append(data['Out']['Run'][args.run[0]])
                    file_names.append('%s: Run %d' %(file_name,args.run[0]))
                    if args.steps != None:
                        if 'Step' in data['Out']['Run'][args.run[0]]:
                            result_list.append(data['Out']['Run'][args.run[0]]['Step'][args.steps[0]])
                            file_names.append('%s: Run %d Step %d' %(file_name,args.run[0],args.steps[0]))
                elif args.runs:
                    file_names.append(file_name)
                    result_list.append([])
                    for run in range(runs):
                        if args.steps != None:
                            steps = len(data['Out']['Run'][run]['Step'])
                            for step in range(steps):
                                result_list[-1].append(data['Out']['Run'][run]['Step'][step])
                                column_tag.append('(%d,%d)' % (run,step))

                        else:
                            result_list[-1].append(data['Out']['Run'][run])

                else:
                    result_list.append(data['Out']['Run'][0])
                    file_names.append('%s: Run 0' %(file_name))
            else:
                result_list.append(results)
                file_names.append(file_name)
            #print len(result_list),type(result_list[0])
            for k,result_item in enumerate(result_list):
                if not isinstance(result_item,list):
                    result_item = [result_item]
                for l,results in enumerate(result_item):
                    for i,var in enumerate(args.dump_vars):
                        if var in results.keys():
                            var_data = results[var]
                        elif var == 'runs' and 'Run' in data['Out']:
                            var_data = runs
                        else:
                            var_data = None
                        if var_data is not None:
                            var_key = var + ' (%d)' % (l)
                            if var_key not in table:
                                table[var_key] = []
                            #table[j,i] = var_data

                            table[var_key].append(var_data)
    #print len(file_names)
    #print table.keys()
    #for data in table.keys(): print len(data)
        #pd.set_option('display.width', 2000)
    pd.set_option('display.max_columns', 500)
    frame_data = pd.DataFrame(table,index=file_names)
    display(frame_data) #columns=args.dump_vars
    return frame_data
    #if args.out is not None:
    #    write_file(args.out,frame_data)

def write_file(file_name,frame_data):
        file_type = file_name[-3:]
        if file_type  == 'csv':
            frame_data.to_csv(file_name)
        else:
            print "file type %s not supported" % file_type

def dump_convergence_stats( args):
    files = [filename for filename in os.listdir('.') if filename.startswith(args.files[0])]
    print files
    data=[]
    for file in files:
        f = open(str(file),'r')
        data.append(json.load(f))
        f.close()
        print '''d['Out']['label'],d['Out']['solve_time'],travel_time,d['Out']['objval'] '''
    for d in data:
        travel_time = calc_total_travel_time(d,d['Out'])
        if 'Out' in d:
                print d['Out']['label'],d['Out']['solve_time'],travel_time,d['Out']['objval']

def dump_phases(args): #data_sets,params,colors,line_styles,steps):

    data_sets = []
    files=[]
    if args.labels: labels=args.labels

    for file in args.files:
        if file.endswith('.json'):
            files.append(file)
        else:
            f = open(str(file),'r')
            for line in f:
                fields = line.split(' ')
                if len(fields) > 2:
                    files.append(fields[2])
            f.close()
    loaded_files=[]
    for file in files:
        if os.path.isfile(file):
            loaded_files.append(file)
            f = open(str(file),'r')
            data_sets.append(json.load(f))
            f.close()


    for data in data_sets:

        results = data['Out']
        if args.step != None:
            if 'Step' in results:
                results = data['Out']['Step'][args.step]
        time = results['t']
        for i,light in enumerate(data['Lights']):
            print 'l_%d' % i
            p_transit = [[False] * len(time) for j in range(len(light['P_MAX']))]

            if 'transits' in light:
                for transit in light['transits']:
                    j = transit['phase']
                    #for k in range(len(light['P_MAX'])):
                    #    print '       ' + ''.join(['1' if x is True else '_' for x in p_transit[k]])

                    for n in range(len(time)):
                        if time[n] >= transit['offset'] and (time[n] - transit['offset'] ) % transit['period'] < transit['duration']:
                            p_transit[j][n] = True


                for k in range(len(light['P_MAX'])):
                    print 'p%d tran' % k + ''.join(['#' if x is True else '_' for x in p_transit[k]])

            for k in range(len(light['P_MAX'])):
                p = 'p_{%d,%d}' % (i,k)
                #print p + ''.join(['#' if p_transit[k][n] == True else '1' if x==1 else '_' for n,x in enumerate(results[p])])
                print p + ''.join([ '1' if x==1 else '_' for n,x in enumerate(results[p])])
            print




def dump_network(args):
    data_sets,loaded_file_sets = read_files(args.files,return_file_sets=True)

    data = data_sets[0][0]
    paths = find_paths(data)
    print paths
    print
    for path in paths:
        print '%-20s' % path,
        for k,i in enumerate(path):
            q = data['Queues'][i]
            q_in = ''
            q_out = ''
            f_ij = ''
            l = ''
            if q['Q_IN'] > 0:
                q_in = '(%d->)' % q['Q_IN']
            if q['Q_OUT'] > 0:
                q_out = '(->%d)' % q['Q_OUT']
            if k < len(path) - 1:
                flow = '%d_%d' % (path[k],path[k+1])
                if flow in data['Flows']:
                    f_ij = ' %d' % data['Flows'][flow]['F_MAX']
            if q['Q_P'] is not None:
                l = '[L%d P%d]' % (q['Q_P'][0],q['Q_P'][1])
            print '%s__%ss__%s%s %s' %(q_in,q['Q_DELAY'],q_out,f_ij,l),
        print
    print
    for path in paths:
        print '-q',
        for i in path:
            print i,
    print

DEBUG = False
IN_CR = False

def debug(msg="",CR=False):
    """
    Display debug messege
    :param msg: The message to display
    :return:
    """
    global DEBUG
    global IN_CR
    if DEBUG:
        if CR:
            print 'DEBUG: '+msg,
            IN_CR = True
        else:
            if IN_CR:
                print msg
                IN_CR = False
            else:
                print 'DEBUG: '+msg

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("files", help="the model file to plot", nargs='+')
    parser.add_argument("-q", "--queues", help="list of queues to plot the delay over", action='append', nargs='+', type=int)
    parser.add_argument("--t0", help="start point along queue of plot",type=float,default=0)
    parser.add_argument("--t1", help="end point along queue of plot",type=float,default=1)
    parser.add_argument("--linestyle", help="list of strings of matplotlib line styles for each plot",nargs='*', default=['_','_','_','_'])
    parser.add_argument("-c", "--color", help="list of matplotlib colors for each plot", default='rbgkycm')
    parser.add_argument("-o", "--out", help="save the plot as OUT")
    parser.add_argument("-n", help="number of points to plot", type=int, default=0)
    parser.add_argument("--histogram", help="plot a histogram of delay with HISTOGRAM wide bins", type=float)
    #parser.add_argument("--step", help="Use output step STEP",type=int)
    parser.add_argument("--run", help="Use output run RUN",nargs='*', type=int)
    parser.add_argument("--runs", help="Use output run RUN",action="store_true", default=False)
    parser.add_argument("--step", help="List of steps to use for each plot (use one step arg per file)", action='append', nargs='*', type=int)
    parser.add_argument("--steps", help="List of steps to use for each plot", nargs='*', type=int)
    parser.add_argument("--dump_stats", help="Dump stats from results files",action="store_true", default=False)
    parser.add_argument("--dump_convergence_stats", help="Dump stats from a set results files starting with FILE pattern",action="store_true", default=False)
    parser.add_argument("--delay_lt", help="plot delay less than DELAY_LT", type=float)
    parser.add_argument("--delay_gt", help="plot delay greater than DELAY_GT", type=float)
    parser.add_argument("--delay_gt_plots", help="list of number of results to group in each of plots delay_gt plots",  nargs='+', type=int)
    parser.add_argument("--plot_travel_time", help="Plots travel time vs N or cpu time for each file",action="store_true", default=False)
    parser.add_argument("--plot_travel_time_ref", help="file for travel time plot reference ")
    parser.add_argument("--plot_av_travel_time_N", help="Plots average travel time vs N for each file",action="store_true", default=False)
    parser.add_argument("--plot_travel_time_maj", help="Sets plot_av_travel_time_N to Plot average travel time vs major frame time for each file",action="store_true", default=False)
    parser.add_argument("--count_time_limit", help="plot average TIME_LIMIT status codes in each run",action="store_true", default=False)
    parser.add_argument("--minimum", help="List of y|n whether to plot minimum or average the points of plot_av_travel_time_N", default='n')
    parser.add_argument("--plot_av_delay", help="Plots average delay vs total traffic for each file",action="store_true", default=False)
    parser.add_argument("--plot_delay_diff", help="Plots average delay vs total traffic for each file",nargs=3, type=float)
    parser.add_argument("--plot_av_travel_time", help="Plots total travel time vs total traffic for each file",action="store_true", default=False)
    parser.add_argument("--plot_travel_time_DT", help="Plots travel time vs DT for each file",action="store_true", default=False)
    parser.add_argument("--plot_cpu_time", help="Plots CPU time vs travel time for each file",action="store_true", default=False)
    parser.add_argument("--plot_av_cpu_time", help="Plots average CPU time vs travel time for each file",action="store_true", default=False)
    parser.add_argument("--plot_scatter", help="Plots each minor frame or run as a point in a scatter plot",action="store_true", default=False)
    parser.add_argument("--plot_phase_offset", help="Plots phase offset vs travel time for each file",action="store_true", default=False)
    parser.add_argument("--plot_box_plot", help="Plots a box plot for each file",action="store_true", default=False)
    parser.add_argument("--plot_vars", help="Plots each var in list",nargs='*')
    parser.add_argument("--plot_flow_profiles", help="Plots all flow profiles found in the file",action="store_true", default=False)
    parser.add_argument("--io_vars_as_rate", help="Plots input and output vars as rate (i.e. /DT) rather than volume",action="store_true", default=False)
    parser.add_argument("--plot_network", help="Plots a network as a link and node graph",action="store_true", default=False)
    parser.add_argument("--plot_network_delay", help="Plots a network as a coloured link and node graph", default='')
    parser.add_argument("--colormap", help="the color map name to use", default='green_red')
    parser.add_argument("--gamma", type=float, help="the gamma of the color map", default=1.0)
    parser.add_argument("--x_limit", help="set the x limit of the plot",nargs='+', type=float)
    parser.add_argument("--y_limit", help="set the y limit of the plot",nargs='+', type=float)
    parser.add_argument("--y_limit2", help="set the y limit of the plot 2nd axis",nargs='+', type=float)
    parser.add_argument("--title", help="set the title of the plot",nargs='*')
    parser.add_argument("--labels", help="list of labels to use for each plot", nargs='+')
    parser.add_argument("--x_label", help="set the x axis label of the plot",nargs='+', default=' ')
    parser.add_argument("--y_label", help="set the y axis label of the plot",nargs='+', default=' ')
    parser.add_argument("--figsize", help="width and height of the plot", nargs='+',type=float)
    parser.add_argument("--marker", help="line maker for the plot",default=' ')
    parser.add_argument("--markerfill", help="List of y|n whether to fill maker",default='n')
    parser.add_argument("--marker_color", help="apply line color to maker",action="store_true",default=False)
    parser.add_argument("--marker_fill", help="fill markers",action="store_true",default=False)
    parser.add_argument("--markevery", help="maker every MARKEVERY points",nargs='+',type=int,default=[1])
    parser.add_argument("--debug", help="output debug messages", action="store_true", default=False)
    parser.add_argument("--dump_vars", help="Dump raw data for each var in the list",nargs='*')
    parser.add_argument("--dump_sample_vars", help="Dump table with each element of each sample var in the list",nargs='*')
    parser.add_argument("--dump_phases", help="Dump phases in each file as a list of strings",action="store_true")
    parser.add_argument("--label_inflow", help="label the inflows on queues in network plots",action="store_true")
    parser.add_argument("--annotate", help="List of y|n whether to annotate the points of each plot with the major frame time", default='n')
    parser.add_argument("--annotate_x", help="List of x points to plot each label in annotate_labels", nargs='*', type=float)
    parser.add_argument("--annotate_y", help="List of y points to plot each label in annotate_labels", nargs='*', type=float)
    parser.add_argument("--annotate_labels", help="List of labels to annotate on plot", nargs='*')
    parser.add_argument("--annotate_size", help="List of label font sizes for each label in annotate_label", nargs='*', type=int)
    parser.add_argument("--annotate_vline", help="List of y|n to draw vline at annotate_x", nargs='*')
    parser.add_argument("--annotate_vline_style", help="List of line syles sizes for annotate_vline", nargs='*',default=['_','_','_','_'])
    parser.add_argument("--annotation_arrow", help="optional text followed by json dictionary of matplotlib annotation parameters to plot an arrow",nargs=2,action='append')
    parser.add_argument("--annotation_text", help="x y text followed by json dictionary of matplotlib text parameters",nargs=4,action='append')
    parser.add_argument("--by_car", help="Box plot of delay from travel time per car rather than per time step", action="store_true", default=False)
    parser.add_argument("--dt", help="sampling step per car for box plots",type=float,default=1)
    parser.add_argument("--time_factor", help="time factor to apply to all plots",type=float,default=1)
    parser.add_argument("--index_label_base", help="base index of queue and light labels in network plots as INDEX_LABEL_BASE",type=int,default=0)
    parser.add_argument("--debug_network", help="annotate network plot with q vars to help debug definition",action="store_true",default=False)
    parser.add_argument("--dump_network", help="print out network definition for debugging",action="store_true",default=False)
    parser.add_argument("--dump_keys", help="dump keys in file",action="store_true",default=False)
    parser.add_argument("--draw_vlines", help="Draw vertical lines on plot at offsets in list", nargs='+', type=float)
    parser.add_argument("--x_var", help="Variable to plot on x axis", default = '')
    parser.add_argument("--box_plot_labels_vertical", help="Orient x axis labels on box plot vertically", action="store_true", default = False)
    parser.add_argument("--dpi", help="DPI to save plots in", type=int, default = 300)
    parser.add_argument("--dump_csv", help="Dump the plot data to CSV file")
    parser.add_argument("--normalize", help="Normalize cumulative plots", action="store_true",default=False)
    parser.add_argument("--no_legend", help="do not display a plot legend", action="store_true",default=False)
    args = parser.parse_args()

    linestyle_map = { '_': '-', '_ _': '--', '_.' : '-.' , '..' : ':' }

    if args.debug:
        DEBUG = True
    else:
        DEBUG = False
    IN_CR = False

    for i,style in enumerate(args.linestyle):
        if style in linestyle_map:
            args.linestyle[i]=linestyle_map[style]
    for i,style in enumerate(args.annotate_vline_style):
        if style in linestyle_map:
            args.annotate_vline_style[i]=linestyle_map[style]


    if args.plot_vars != None:
        plot_vars(args)
    elif args.plot_flow_profiles:
        plot_flow_profiles(args)
    elif args.plot_travel_time:
        plot_parameter(plot_travel_time,args)
    elif args.plot_av_travel_time:
        plot_av_travel_time(args)
    elif args.plot_av_delay:
        plot_parameter(plot_av_delay,args)
    elif args.plot_delay_diff is not None:
        plot_parameter(plot_delay_diff,args)
    elif args.plot_av_travel_time_N:
        plot_av_travel_time_N(args)
    elif args.plot_phase_offset:
        plot_phase_offset(args)

    elif args.plot_box_plot:
        plot_box_plot(args)

    elif args.plot_cpu_time:
        plot_cpu_time(args)

    elif args.plot_network:
        plot_network(args)
    elif args.plot_network_delay != '':
        plot_network_delay(args)
    elif args.dump_stats:
        dump_stats(args)
    elif args.dump_vars:
        frame_data = dump_vars(args)
    elif args.dump_sample_vars:
        dump_sample_vars(args)
    elif args.dump_phases:
        dump_phases(args)
    elif args.dump_network:
        dump_network(args)
    elif args.dump_keys:
        dump_keys(args)
    else:
        #files=[]
        #data=[]
        #for file in args.files:
        #    files.append(str(file))
        #    f = open(str(file),'r')
        #    data.append(json.load(f))
        #    f.close()

        plot_data_files = read_files(args.files)
        if args.histogram:
            if args.delay_gt:
                plot_delay_gt(data,args.step,args.histogram,args.delay_gt,args.queues,args.delay_gt_plots,args.linestyle)
            else:
                plot_delay_histogram(data,args.step,args.histogram,args.queues,args.linestyle,args=args)
        elif args.plot_travel_time:
            plot_tavel_time(data,args.step,args.delay_gt,args.queues,args.plot_travel_time,args.linestyle)
        else:
            plot_delay(plot_data_files[0],args.step,args.queues,args.linestyle,args)

    if args.out:
        file_type = args.out[-3:]
        #print file_type
        if file_type  == 'csv':
            frame_data.to_csv(args.out)
        else:
            pl.savefig(args.out, bbox_inches='tight',dpi=args.dpi)
    pl.show();






