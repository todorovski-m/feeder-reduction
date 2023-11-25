function mpc = two_branches
%% MATPOWER Case Format : Version 2
mpc.version = '2';
%% system MVA base
mpc.baseMVA = 1;

%% bus data
mpc.bus = [
%   bus_i type  Pd  Qd Gs Bs area Vm Va baseKV zone Vmax Vmin
        1    3   0   0  0  0    1  1  0     10    1  1.1  0.9
        2    1   1 0.5  0  0    1  1  0     10    1  1.1  0.9
        3    1 0.8 0.3  0  0    1  1  0     10    1  1.1  0.9
];

%% generator data
mpc.gen = [
%   bus Pg Qg Qmax Qmin Vg mBase status Pmax Pmin
      1  0  0  999 -999  1   100      1  999    0
];

%% branch data
Zbase = 10^2/1;
r = 0.3/Zbase;
x = 0.1/Zbase;
mpc.branch = [
%   fbus tbus   r   x b rateA rateB rateC ratio angle status angmin angmax
       1    2 2*r 2*x 0     0     0     0     0     0      1   -360    360
       2    3 3*r 3*x 0     0     0     0     0     0      1   -360    360
];
