import os
import csv
from qiskit import qasm2
from qiskit.transpiler.passes import CollectLinearFunctions

from collections import defaultdict

circuit_path = "circuits_target_qiskit"

circuit = qasm2.load(filename='circuits_target_qiskit/dj_indep_qiskit_10.qasm', 
    custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
print(circuit)

exit()

# read open qasm circuits from directory:
data = []
data.append(['name', 'num_qubits', 'width', 'depth', 'num_cnot', 'num_t', 'num_2qbit', 'num_3qbit'])
for filename in os.listdir(circuit_path):
    path = os.path.join(circuit_path, filename)
    # interpret openqasm als qiskit QuantumCircuit
    circuit = qasm2.load(filename=path, 
        custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
    # add explanatory variables to data
    cnot_count = circuit.count_ops().get('cx') or 0
    t_count = circuit.count_ops().get('t') or 0
    count_multi_qbit_gates = defaultdict(int)
    for entry in circuit.data:
        count_multi_qbit_gates[len(entry.qubits)] += 1
    two_qbit_gate_count = count_multi_qbit_gates.get(2) or 0
    three_qbit_gate_count = count_multi_qbit_gates.get(3) or 0

    data.append([filename,
        circuit.num_qubits, 
        circuit.width(), 
        circuit.depth(), 
        cnot_count,
        t_count,
        two_qbit_gate_count,
        three_qbit_gate_count])

# write data in .csv file
with open('circuit_data.csv', mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerows(data)