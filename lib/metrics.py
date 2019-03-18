# metrics.py
# Author(s): David Joy

# This software was developed by employees of the National Institute of
# Standards and Technology (NIST), an agency of the Federal
# Government. Pursuant to title 17 United States Code Section 105, works
# of NIST employees are not subject to copyright protection in the
# United States and are considered to be in the public
# domain. Permission to freely use, copy, modify, and distribute this
# software and its documentation without fee is hereby granted, provided
# that this notice and disclaimer of warranty appears in all copies.

# THE SOFTWARE IS PROVIDED 'AS IS' WITHOUT ANY WARRANTY OF ANY KIND,
# EITHER EXPRESSED, IMPLIED, OR STATUTORY, INCLUDING, BUT NOT LIMITED
# TO, ANY WARRANTY THAT THE SOFTWARE WILL CONFORM TO SPECIFICATIONS, ANY
# IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE, AND FREEDOM FROM INFRINGEMENT, AND ANY WARRANTY THAT THE
# DOCUMENTATION WILL CONFORM TO THE SOFTWARE, OR ANY WARRANTY THAT THE
# SOFTWARE WILL BE ERROR FREE. IN NO EVENT SHALL NIST BE LIABLE FOR ANY
# DAMAGES, INCLUDING, BUT NOT LIMITED TO, DIRECT, INDIRECT, SPECIAL OR
# CONSEQUENTIAL DAMAGES, ARISING OUT OF, RESULTING FROM, OR IN ANY WAY
# CONNECTED WITH THIS SOFTWARE, WHETHER OR NOT BASED UPON WARRANTY,
# CONTRACT, TORT, OR OTHERWISE, WHETHER OR NOT INJURY WAS SUSTAINED BY
# PERSONS OR PROPERTY OR OTHERWISE, AND WHETHER OR NOT LOSS WAS
# SUSTAINED FROM, OR AROSE OUT OF THE RESULTS OF, OR USE OF, THE
# SOFTWARE OR SERVICES PROVIDED HEREUNDER.

# Distributions of NIST software should also include copyright and
# licensing statements of any third-party software that are legally
# bundled with the code in compliance with the conditions of those
# licenses.

from operator import add
from sparse_signal import SparseSignal as S
from alignment_record import *
from helpers import *

def _signal_pairs(r, s, signal_accessor, key_join_op = set.union):
    rl, sl = r.localization, s.localization
#    print "RL"
#    print signal_accessor(rl, k)
#    print "SL"
#    print sl
#    print rl
#    print [ (signal_accessor(rl, k), signal_accessor(sl, k), k) for k in key_join_op(set(rl.keys()), set(sl.keys())) ]
    return [ (signal_accessor(rl, k), signal_accessor(sl, k), k) for k in key_join_op(set(rl.keys()), set(sl.keys())) ]

def _temporal_signal_accessor(localization, k):
    #print 'localization:'
    #print localization
    return S(localization.get(k, {}))

def temporal_signal_pairs(r, s, key_join_op = set.union):
#    print "before temporal_signal_pairs"
#    print r
#    print s
#    print "return of temporal_signal_pairs"
#    print _signal_pairs(r, s, _temporal_signal_accessor, key_join_op)
    return _signal_pairs(r, s, _temporal_signal_accessor, key_join_op)

def _single_signal(s, signal_accessor, key_join_op=set.union):
    sl = s.localization
#    print "in _single_signal"
#    print sl
#    print [ (signal_accessor(sl, k), k) for k in  sl.keys() ][0]
    return [ (signal_accessor(sl, k), k) for k in  sl.keys() ][0]

def temporal_single_signal(s, key_join_op = set.union):
#    print "in temporal_single_signal"
#    print s
    return _single_signal(s, _temporal_signal_accessor, key_join_op)
    
def temporal_intersection(r, s):
    #print "temporal_intersection r:"
    #print r
    #print "temporal_intersection s:"
    #print s
#    print reduce(add, [ (r & s).area() for r, s, k in temporal_signal_pairs(r, s, set.intersection) ], 0)
    return reduce(add, [ (r & s).area() for r, s, k in temporal_signal_pairs(r, s, set.intersection) ], 0)

def temporal_union(r, s):
    return reduce(add, [ (r | s).area() for r, s, k in temporal_signal_pairs(r, s) ], 0)

def temporal_fa(r, s):
#    print "CALCULATING TEMPORAL_FA"
    return reduce(add, [ (s - (r & s)).area() for r, s, k in temporal_signal_pairs(r, s) ], 0)

def temporal_miss(r, s):
    return reduce(add, [ (r - (r & s)).area() for r, s, k in temporal_signal_pairs(r, s) ], 0)

def temporal_intersection_over_union(r, s):
    intersection = temporal_intersection(r, s)
    union = temporal_union(r, s)
    #print intersection
    #print union
    # Not sure if this is the best way to handle union == 0; but in
    # practise should never encounter this case
    return float(intersection) / union if union != 0 else 0.0

def _spatial_signal_accessor(localization, k):
    if k in localization:
        return localization.get(k).spatial_signal
    else:
        return S()

def spatial_signal_pairs(r, s, key_join_op = set.union):
    return _signal_pairs(r, s, _spatial_signal_accessor, key_join_op)

def simple_spatial_intersection(r, s):
    return r.join_nd(s, 2, min).area()

def simple_spatial_union(r, s):
    return r.join_nd(s, 2, max).area()

def simple_spatial_intersection_over_union(r, s):
    intersection = simple_spatial_intersection(r, s)
    #print "intersection: "
    #print intersection
    union = simple_spatial_union(r, s)
    #print "union: "
    #print union

    # Not sure if this is the best way to handle union == 0; but in
    # practise should never encounter this case
    return float(intersection) / union if union != 0 else 0.0

def spatial_intersection(r, s):
    return reduce(add, [ simple_spatial_intersection(r, s) for r, s, k in spatial_signal_pairs(r, s, set.intersection) ], 0)

def spatial_union(r, s):
    return reduce(add, [ simple_spatial_union(r, s) for r, s, k in spatial_signal_pairs(r, s) ], 0)

def spatial_intersection_over_union(r, s):
    intersection = spatial_intersection(r, s)
    union = spatial_union(r, s)

    # Not sure if this is the best way to handle union == 0; but in
    # practise should never encounter this case
    return float(intersection) / union if union != 0 else 0.0

# aligned_pairs should be a list of tuples being (reference, system);
# where reference and system are each ActivityInstance objects
def n_mide(aligned_pairs, file_framedur_lookup, ns_collar_size, cost_fn_miss, cost_fn_fa):
    # Should consider another paramemter for for all files to consider
    # for FA denominator calculation, in the case of cross-file
    # activity instances
    num_aligned = len(aligned_pairs)

    if num_aligned == 0:
        return { "n-mide": None,
                 "n-mide_num_rejected": 0 }

    def _sub_reducer(init, pair):
        init_miss, init_fa, init_miss_d, init_fa_d = init
        rs, ss, k = pair

        ns_collar = rs.generate_collar(ns_collar_size)
        c_r = rs - ns_collar
        c_s = ss - ns_collar
        col_r = rs | ns_collar

        miss = (c_r - c_s).area()
        fa = (c_s - c_r).area()

        return (init_miss + miss, init_fa + fa, init_miss_d + c_r.area(), init_fa_d + (file_framedur_lookup.get(k) - col_r.area()))

    def _reducer(init, pair):
        r, s = pair
        # Using the _sub_reducer here is important in the case of
        # cross-file activity instances
        miss, fa, miss_denom, fa_denom = reduce(_sub_reducer, temporal_signal_pairs(r, s), (0, 0, 0, 0))
        if miss_denom > 0 and fa_denom > 0:
            init.append(cost_fn_miss(float(miss) / miss_denom) + cost_fn_fa(float(fa) / fa_denom))

        return init

    mides = reduce(_reducer, aligned_pairs, [])

    if len(mides) == 0:
        return { "n-mide": None,
                 "n-mide_num_rejected": len(aligned_pairs) }
    else:
        return { "n-mide": float(reduce(add, mides)) / len(mides),
                 "n-mide_num_rejected": len(aligned_pairs) - len(mides) }


def fa_meas(aligned_pairs, missed_ref, false_sys, file_framedur_lookup, ns_collar_size):
        # Should consider another paramemter for for all files to consider
        # for FA denominator calculation, in the case of cross-file
        # activity instances
        num_aligned = len(aligned_pairs) + len(missed_ref)
        combined_ref=[b[0] for b in aligned_pairs] + [m for m in missed_ref] #works
        ref_temp = [temporal_single_signal(r) for r in combined_ref ]
        ref_temp_add=reduce(add, [r[0] for r in ref_temp])
#        print "ref_temp_add"
#        print ref_temp_add
        not_ref=ref_temp_add.not_sig(file_framedur_lookup.get(ref_temp[0][1]))
        nr_area=not_ref.area()
#        print "not_ref"
#        print not_ref
        #print "not_ref area"
        #print not_ref.area()
        if nr_area == 0:
            return { "newfa": None,
                     "newfa_denom": None,
                     "newfa_numer": None,
                     "System_Sig": None,
                     "Ref_Sig": None,
                     "NR_Ref_Sig": None}
        combined_sys = [b[1] for b in aligned_pairs] + [f for f in false_sys]
        sys_temp = [temporal_single_signal(s) for s in combined_sys ]
        sys_temp_add=reduce(add, [s[0] for s in sys_temp])
#        print "sys_temp_add"
#        print sys_temp_add
        def _reducer(init,pair):
            r, s = pair
            inters = (r & s).area()
            init = init + inters
            return init
        numer_pairs = [[not_ref, s[0] ] for s in sys_temp]
#        print "number_pairs"
#        print numer_pairs
        numer = reduce(_reducer, numer_pairs, 0)#(not_ref & sys_temp_add).area()
        #numer=temporal_intersection(not_ref, sys_temp_add)
#        print "numer"
#        print numer
        denom=nr_area
        return { "newfa": (float(numer) / denom),
                 "newfa_denom": nr_area,
                 "newfa_numer": numer,
                 "System_Sig": sys_temp_add,
                 "Ref_Sig": ref_temp_add,
                 "NR_Ref_Sig": not_ref}


    #def _reducer(init, pair):
        #    r, s = pair
        #    p_union=temporal_intersection(r, s)
        #    print "p_union"
        #    print p_union
        #    init = init + p_union
        #    return init
       # 
        #r_s_inter=reduce(_reducer, aligned_pairs, 0)
        #print "nr_area"
        #print not_ref
        #print nr_area
        #print "sys_temp_add.area()"
        #print sys_temp_add.area()
        #print "fa"
        #print float(nr_area - sys_temp_add.area() - r_s_inter) / nr_area
        #return { "fa": (float(nr_area - sys_temp_add.area() - r_s_inter) / nr_area),
        #         "NR_area": nr_area}


def build_n_mide_metric(file_frame_dur_lookup, ns_collar_size, cost_fn_miss = lambda x: 1 * x, cost_fn_fa = lambda x: 1 * x):
    def _n_mide(pairs):
        return n_mide(pairs, file_frame_dur_lookup, ns_collar_size, cost_fn_miss, cost_fn_fa)

    return _n_mide

def build_fa_metric(file_frame_dur_lookup, ns_collar_size, cost_fn_miss = lambda x: 1 * x, cost_fn_fa = lambda x: 1 * x):
        def _fa(pairs):
            return fa_met(pairs, file_frame_dur_lookup, ns_collar_size, cost_fn_miss, cost_fn_fa)
        
        return _fa
    
def w_p_miss(num_c, num_m, num_f, denominator, numerator):
    denom = num_m + num_c + denominator
    numer = num_m + numerator
    if num_m + num_c == 0:
        return None
    else:
        return float(numer) / denom

def p_miss(num_c, num_m, num_f):
    denom = num_m + num_c
    if denom == 0:
        return None
    else:
        return float(num_m) / denom

def build_pmiss_metric():
    def _p_miss(c, m, f):
        return { "p_miss": p_miss(len(c), len(m), len(f)) }
    return _p_miss

def build_wpmiss_metric(denom, numer):
    def _w_p_miss(c, m, f):
        return { "w_p_miss": w_p_miss(len(c), len(m), len(f), denom, numer) }
    return _w_p_miss

def r_fa(num_c, num_m, num_f, denominator):
    return float(num_f) / denominator

def build_rfa_metric(denom):
    def _r_fa(c, m, f):
        return { "rfa": r_fa(len(c), len(m), len(f), denom) }

    return _r_fa

# Returns y value for lowest confidence value at each x_targ.  The
# points argument should be a list of tuples, where each tuple is of
# the form (confidence_value, metrics_dict)
def get_points_along_confidence_curve(points, x_label, x_key, y_label, y_key, x_targs, y_default = 1.0):
    if len(x_targs) == 0:
        return {}

    def _metric_str(targ):
        return "{}@{}{}".format(y_label, targ, x_label)

    # Note ** currently reporting out the 'y_default' for each targ if
    # the curve is empty
    if len(points) == 0:
        return { _metric_str(t): y_default for t in x_targs }

    sorted_targs = sorted(x_targs, reverse = True)
    curr_targ = sorted_targs[-1]

    out_metrics = {}

    x, y = None, None
    last_y = None
    last_x = 0.0
    exact_match = False
    sorted_points = sorted([ (ds, x_key(m), y_key(m)) for ds, m in points ], None, lambda x: x[0])
    while True:
        if x is not None:
            if abs(x - curr_targ) < 1e-10:
                exact_match = True
            elif x > curr_targ:
                if last_y == None:
                    out_metrics[_metric_str(curr_targ)] = y_default
                elif exact_match:
                    out_metrics[_metric_str(curr_targ)] = last_y
                    exact_match = False
                else: # interpolate
                    out_metrics[_metric_str(curr_targ)] = last_y + (y - last_y) * (float(curr_targ - last_x) / (x - last_x))

                sorted_targs.pop()
                if len(sorted_targs) == 0:
                    break
                else:
                    curr_targ = sorted_targs[-1]
                    continue

        # Only pop the next point if we're sure we haven't overstepped any remaining targs
        last_y, last_x = y, x
        if len(sorted_points) > 0:
            ds, x, y = sorted_points.pop()
        else:
            break

    # If we ran out of points but still have targets, generate the
    # metrics here
    last_y = y
    for targ in sorted_targs:
        out_metrics[_metric_str(targ)] = y_default if last_y is None else last_y

    return out_metrics

def mean_exclude_none(values):
    fv = filter(lambda v: v is not None, values)
    return { "mean": float(reduce(add, fv, 0)) / len(fv) if len(fv) > 0 else None,
             "mean_num_rejected": len(values) - len(fv) }

def mode(num_c, num_m, num_f, cost_m, cost_f):
    return float(cost_m(num_m) + cost_f(num_f)) / (num_c + num_m)

def build_mode_metric(cost_fn_m = lambda x: 1 * x, cost_fn_f = lambda x: 1 * x):
    def _mode(c, m, f):
        # Don't attempt to compute mode if there are no reference
        # objects
        num_c, num_m, num_f = len(c), len(m), len(f)
        value = mode(num_c, num_m, num_f, cost_fn_m, cost_fn_f) if num_m + num_c > 0 else None
        #print "MODE CALCULATED"
        #print value
        return { "mode": value }

    return _mode

def mote(num_c, num_m, num_f, num_id, cost_m, cost_f, cost_id):
    #print cost_m(num_m)
    #print cost_id
#    print "NUM_ID"
#    print num_id
#    print "NUM_F"
#    print num_f
    return float(cost_m(num_m) + cost_f(num_f) + cost_id(num_id)) / (num_c + num_m)
    #return float(cost_m(num_m) + cost_f(num_f)) / (num_c + num_m)

def build_mote_metric(frame_correct_align, conf_func, cost_fn_m = lambda x: 1 * x, cost_fn_f = lambda x: 1 * x, cost_fn_id = lambda x: 1 * x):
    def _mote(c, m, f):
        num_c, num_m, num_f = len(c), len(m), len(f)
        
        conf = sorted(set(map(conf_func, c + f)))[0]
        #print "CONF"
        #print conf
        num_id = 0 
        cur_align={}
        for i in frame_correct_align:
            #print i
            ar=i[1]
            #print ar
            if ar.sys.presenceConf >= conf:
                try:
                    if cur_align[ar.ref.objectID] != ar.sys.objectID:
                        num_id+=1
                        cur_align[ar.ref.objectID] = ar.sys.objectID
                except:
                    cur_align[ar.ref.objectID] = ar.sys.objectID
        #print num_id
        value = mote(num_c, num_m, num_f, num_id, cost_fn_m, cost_fn_f, cost_fn_id) if num_m + num_c > 0 else None
#        print "Calculating MOTE"
        #print value
        return { "mote": value }
    return _mote

def build_sweeper(conf_key_func, measure_funcs):
    def _sweep(alignment_records):
        c, m, f = partition_alignment(alignment_records)
        total_c = len(c)
        num_m = len(m)
        # num_f = len(f)
        #print "C Again:"
        #print c
        #print "M:"
        #print m
        #print "f:"
        #print f
        out_points = []
        current_c, current_f = [], []

        # m records don't need to be sorted as they have None
        # confidence scores
        current_m = m + sorted(c, None, conf_key_func)
        remaining_f = sorted(f, None, conf_key_func)
        uniq_confs = sorted(set(map(conf_key_func, c + f)), reverse = True)
        for conf in uniq_confs:
            while len(current_m) > 0 and current_m[-1].alignment != "MD" and conf_key_func(current_m[-1]) >= conf:
                current_c.append(current_m.pop())
            #print "current c"
            #print current_c
            while len(remaining_f) > 0 and conf_key_func(remaining_f[-1]) >= conf:
                current_f.append(remaining_f.pop())

            out_points.append((conf, reduce(merge_dicts, [ m(current_c, current_m, current_f) for m in measure_funcs ], {})))
        #print "OUT_POINTS: "
        #print out_points
        return out_points

    return _sweep

def flatten_sweeper_records(recs, keys):
    return [ [ c ] + [ d[k] for k in keys ] for c, d in recs ]

#def build_det_sweeper(conf_key_func, rfa_denom):
#    return build_sweeper(conf_key_func, [ build_rfa_metric(rfa_denom),
#                                          build_pmiss_metric(),
#                                          build_wpmiss_metric() ])
