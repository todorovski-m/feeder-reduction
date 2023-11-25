"""
Feeder reduction for the IEEE13 test feeder with data taken from OpenDSS (EPRI
Distribution System Simulator). More information about this feeder can be found
at https://cmte.ieee.org/pes-testfeeders/

We use "direct" Python interface to OpenDSS:
https://github.com/dss-extensions/dss_python
which can be installed with pip: pip install dss_python
The documentation is at https://dss-extensions.org/dss_python/dss/
"""
import numpy as np
import pandas as pd
from dss import DSS as dss_engine


def make_voltage_table(dss_engine):
    """
    Makes a pandas table with bus voltages per phase using the latest solution
    of the OpenDSS engine.
    """
    # add column with bus names
    voltages = pd.DataFrame({"bus": dss_engine.ActiveCircuit.AllBusNames})
    # add columns with phase voltages in pu
    for i in [1, 2, 3]:
        # strip last two characters from node names to get bus names
        bus_name = [x[:-2] for x in dss_engine.ActiveCircuit.AllNodeNamesByPhase(i)]
        # add voltages for buses where phase i is present
        idx = voltages["bus"].isin(bus_name)
        voltages.loc[idx, f"V{i}"] = dss_engine.ActiveCircuit.AllNodeVmagPUByPhase(i)
    # add columns with complex phase voltages in kV
    for i, row in voltages.iterrows():
        dss_engine.ActiveCircuit.SetActiveBus(row["bus"])
        values = dss_engine.ActiveCircuit.Buses.VMagAngle
        nodes = dss_engine.ActiveCircuit.Buses.Nodes
        Vmag = values[::2] / 1000
        Vangle = values[1::2]
        for n, Vm, Va in zip(nodes, Vmag, Vangle):
            voltages.at[i, f"V{n}c"] = Vm * np.exp(1j * Va / 180 * np.pi)
    voltages = voltages.fillna(0)
    # make voltage dictionary
    V = {}
    for bus in voltages["bus"]:
        idx = voltages["bus"] == bus
        V[bus] = voltages.loc[idx, ["V1c", "V2c", "V3c"]].to_numpy(dtype=complex)[0]
    return voltages, V


def make_elem_losses(dss_engine):
    """
    Makes a dictionary with element names as keys, containing element losses
    """
    DS = {}
    losses = dss_engine.ActiveCircuit.AllElementLosses
    elements_names = dss_engine.ActiveCircuit.AllElementNames
    for name, r, i in zip(elements_names, losses[0::2], losses[1::2]):
        DS[name] = (r + 1j*i) * np.ones(1, dtype=complex)
    return DS


def make_line_params(dss_engine):
    """
    Makes a dictionary with branch names as keys, containing branch impedance
    matrices Zb, admittance matrices Yb, "from buses" F and "to buses" T
    """
    Zb = {}
    Yb = {}
    F = {}
    T = {}
    omega = 120 * np.pi
    for line in dss_engine.ActiveCircuit.Lines:
        F[line.Name] = line.Bus1.split(".")[0]
        T[line.Name] = line.Bus2.split(".")[0]
        n = line.Phases
        if n == 3:
            phases = [1, 2, 3]
        else:
            phases = [int(x) for x in line.Bus1.split(".")[1:]]
        phases = np.array(phases)
        Rmatrix = np.array(line.Rmatrix).reshape((n, n)) * line.Length
        Xmatrix = np.array(line.Xmatrix).reshape((n, n)) * line.Length
        Cmatrix = np.array(line.Cmatrix).reshape((n, n)) * line.Length * 1e-9
        R = 1e6 * np.eye(3)
        X = 1e6 * np.eye(3)
        B = np.zeros((3, 3))
        if n == 1:
            f = phases[0] - 1
            R[f, f] = Rmatrix[0, 0]
            X[f, f] = Xmatrix[0, 0]
            B[f, f] = omega * Cmatrix[0, 0]
        elif n == 2:
            for i in range(2):
                f = phases[i] - 1
                R[f, phases - 1] = Rmatrix[i, :]
                X[f, phases - 1] = Xmatrix[i, :]
                B[f, phases - 1] = omega * Cmatrix[i, :]
        else:
            R = Rmatrix.copy()
            X = Xmatrix.copy()
            B = omega * Cmatrix.copy()
        Zb[line.Name] = R + 1j*X
        Yb[line.Name] = 1j * B
    return Zb, Yb, F, T


def make_load_currents(dss_engine):
    """
    Makes a dictionary with bus names as keys, containing load currents.
    """
    Id = {}
    for load in dss_engine.ActiveCircuit.Loads:
        dss_engine.ActiveCircuit.SetActiveElement(load.Name)
        bus_name = dss_engine.ActiveCircuit.ActiveCktElement.BusNames[0]
        bus = bus_name.split(".")[0]
        phases = np.array([int(x) for x in bus_name.split(".")[1:]])
        values = dss_engine.ActiveCircuit.ActiveCktElement.Currents
        complex_values = []
        for r, i in zip(values[0::2], values[1::2]):
            complex_values.append(r + 1j*i)
        if bus not in Id:
            Id[bus] = np.zeros(3, dtype=complex)
        for phase, value in zip(phases - 1, complex_values):
            Id[bus][phase] += value
    return Id


def make_cap_currents(dss_engine):
    """
    Makes a dictionary with bus names as keys, containing capacitor currents.
    """
    Ic = {}
    for cap in dss_engine.ActiveCircuit.Capacitors:
        dss_engine.ActiveCircuit.SetActiveElement(cap.Name)
        bus_name = dss_engine.ActiveCircuit.ActiveCktElement.BusNames[0]
        bus = bus_name.split(".")[0]
        phases = np.array([int(x) for x in bus_name.split(".")[1:]])
        if phases.size == 0:
            phases = np.array([1, 2, 3])
        values = dss_engine.ActiveCircuit.ActiveCktElement.Currents
        complex_values = []
        for r, i in zip(values[0::2], values[1::2]):
            complex_values.append(r + 1j*i)
        if bus not in Ic:
            Ic[bus] = np.zeros(3, dtype=complex)
            for phase, value in zip(phases - 1, complex_values):
                Ic[bus][phase] += value
    return Ic


def ieee13():
    # solve the original network
    dss_engine.Text.Command = "compile IEEE13Nodeckt.dss"
    dss_engine.ActiveCircuit.Solution.Solve()
    voltages0, V0 = make_voltage_table(dss_engine)
    print("ORIGINAL FEEDER")
    print(voltages0.to_string(index=False))

    # network elements data
    Zb, Yb, F, T = make_line_params(dss_engine)
    DS = make_elem_losses(dss_engine)
    Id = make_load_currents(dss_engine)
    Ic = make_cap_currents(dss_engine)

    # calculate branch capacitive currents
    Icf = {}
    Ict = {}
    for i in F.keys():
        Icf[i] = 0.5 * np.matmul(Yb[i], 1000 * V0[F[i]])
        Ict[i] = 0.5 * np.matmul(Yb[i], 1000 * V0[T[i]])

    # eliminate feeder laterals by calculating equivalent load currents along feeder backbone
    Ibus = {
        1: np.zeros(3, dtype=complex),
        2: Id["646"] + Id["645"] + Id["634"] * 0.48 / 4.16,
        3: Id["670"],
        4: Id["611"] + Id["652"] + Id["671"] + Id["692"] + Id["675"] + Ic["611"] + Ic["675"],
        5: np.zeros(3, dtype=complex),
    }

    # add branch capacitive currents
    Ibus[1] += Icf["650632"]
    Ibus[2] += Ict["650632"] + Icf["632670"]
    for b in ["645646", "632645", "632633"]:
        Ibus[2] += Icf[b] + Ict[b]
    Ibus[3] += Ict["632670"] + Icf["670671"]
    Ibus[4] += Ict["670671"] + Icf["671680"]
    for b in ["684611", "671684", "692675"]:
        Ibus[4] += Icf[b] + Ict[b]
    Ibus[5] += Ict["671680"]

    # add generator currents
    dss_engine.ActiveCircuit.SetActiveElement("gen680")
    values = dss_engine.ActiveCircuit.ActiveCktElement.Currents
    Ig = []
    for r, i in zip(values[0::2], values[1::2]):
        Ig.append(r + 1j*i)
    Ig = np.array(Ig[:-1], dtype=complex)
    Ibus[5] += Ig

    # impedances of lines on the feeder backbone
    Z = {
        1: Zb["650632"],
        2: Zb["632670"],
        3: Zb["670671"],
        4: Zb["671680"],
    }

    # current summation for lines on feeder backbone
    n = 5
    J = {}
    for k in range(1, n):
        J[k] = np.zeros(3, dtype=complex)
        for i in range(k + 1, n + 1):
            J[k] += Ibus[i]

    # Printing elements of array up to 3 decimal places
    np.set_printoptions(formatter={"complexfloat": lambda x: f"{x.real:0.3f}{x.imag:+0.3f}j"})

    # voltage drop
    DV = V0["rg60"] - V0["680"]
    # total losess on the feeder backbone
    backbone = [
        "Line.650632",
        "Line.632670",
        "Line.670671",
        "Line.671680",
    ]
    DS_tot = 0
    for line in backbone:
        DS_tot += DS[line]

    print("\n" + "SELECTED FEEDER BACKBONE")
    for line in backbone:
        print(line)
    print(f"Voltage drop DV = {DV} kV")
    print(f"Power losses DS = {DS_tot} kVA")

    # reduce the feeder to a single line from 650 to 680
    # sum of all branch impedances
    Zs = np.zeros((3, 3), dtype=complex)
    for i in range(1, n):
        Zs += Z[i]

    print("\n" + "FEEDER REDUCTION ACCOUNTING FOR VOLTAGE DROP ONLY")
    Ze = Zs.copy()
    Ie2 = np.matmul(np.linalg.inv(Ze), DV * 1000)
    Ie1 = J[1] - Ie2
    DSe = np.sum(DV * np.conj(Ie2))
    print(f"Ze =\n{Ze} Ohms")
    print(f"Ie2 = {Ie2} A")
    print(f"Ie1 = {Ie1} A")
    print(f"Power losses DSe = {np.array([DSe])} kVA")

    print("\n" + "FEEDER REDUCTION ACCOUNTING FOR VOLTAGE DROP AND LOSSES SIMULTANEOUSLY")
    g = np.sum(np.conj(DV * 1000) * np.matmul(np.linalg.inv(Zs), DV * 1000)) / np.conj(DS_tot * 1000)
    Ze = g * Zs.copy()
    Ie2 = np.matmul(np.linalg.inv(Ze), DV * 1000)
    Ie1 = J[1] - Ie2
    DSe = np.sum(DV * np.conj(Ie2))
    print(f"g = {g}")
    print(f"Ze =\n{Ze} Ohms")
    print(f"Ie2 = {Ie2} A")
    print(f"Ie2-Ig = {Ie2-Ig} A")
    print(f"Ie1 = {Ie1} A")
    print(f"Power losses DSe = {np.array([DSe])} kVA")

    with open("IEEE13-header.dss", "r") as f:
        txt = f.read()

    Re, Xe = Ze.real, Ze.imag
    txt += "\nNew Linecode.mtx_eq nphases=3\n"
    txt += f"~ rmatrix = [{Re[0,0]} | {Re[1,0]} {Re[1,1]} | {Re[2,0]} {Re[2,1]} {Re[2,2]}]\n"
    txt += f"~ xmatrix = [{Xe[0,0]} | {Xe[1,0]} {Xe[1,1]} | {Xe[2,0]} {Xe[2,1]} {Xe[2,2]}]\n"

    txt += "\n" + "New Line.eq_line Phases=3 Bus1=rg60 Bus2=680 LineCode=mtx_eq Length=1" + "\n"
    txt += "\n" + "New Generator.gen680  Bus1=680  kV=4.16  kW=1000  PF=1" + "\n"

    model = 1
    Se1 = V0["rg60"] * np.conj(Ie1)
    Se2 = V0["680"] * np.conj(Ie2 - Ig)  # substract Ig since the gen. is added with the command New Gnerator.680 ...
    txt += "\n"
    for i in range(3):
        txt += f"New Load.rg60-{i+1} Bus1=rg60.{i+1} Phases=1 Conn=Wye Model={model} kV=2.4 kW={Se1[i].real} kvar={Se1[i].imag}\n"
    txt += "\n"
    for i in range(3):
        txt += f"New Load.680-{i+1} Bus1=680.{i+1} Phases=1 Conn=Wye Model={model} kV=2.4 kW={Se2[i].real} kvar={Se2[i].imag}\n"

    txt += "\n" + "Set Voltagebases=[115, 4.16]" + "\n"
    txt += "calcv" + "\n"
    txt += "Solve" + "\n"

    with open("IEEE13-equivalent.dss", "w") as f:
        f.write(txt)

    dss_engine.Text.Command = "compile IEEE13-equivalent.dss"
    dss_engine.ActiveCircuit.Solution.Solve()
    voltages, V = make_voltage_table(dss_engine)
    DS = make_elem_losses(dss_engine)
    DV = V["rg60"] - V["680"]
    print("\n" + "REDUCED FEEDER")
    print(voltages.to_string(index=False))
    print(f"Voltage drop DV = {DV} kV")
    print(f"Power losses DS = {DS['Line.eq_line']} kVA")


if __name__ == "__main__":
    ieee13()
