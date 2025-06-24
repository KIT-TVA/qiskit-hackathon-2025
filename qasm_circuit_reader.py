import os
import csv
from qiskit import qasm2

circuit_path = "circuits_target_qiskit"

# read open qasm circuits from directory:
data = []
data.append(['name', 'num_qubits', 'width', 'depth'])
for filename in os.listdir(circuit_path):
    path = os.path.join(circuit_path, filename)
    # interpret openqasm als qiskit QuantumCircuit
    circuit = qasm2.load(filename=path, 
        custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
    # add explanatory variables to data
    data.append([filename, circuit.num_qubits, circuit.width(), circuit.depth()])

# write data in .csv file
with open('circuit_data.csv', mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerows(data)