from qiskit.transpiler.passes import PadDynamicalDecoupling
from qiskit.transpiler.instruction_durations import InstructionDurations
from qiskit.transpiler.target import Target
from qiskit.transpiler import PassManager
from qiskit.circuit import library as lib
from qiskit.transpiler.passes import ALAPScheduleAnalysis
from qiskit import QuantumCircuit
from qiskit.transpiler import Target
from qiskit.visualization import timeline_drawer
from qiskit.transpiler import PassManager, InstructionDurations, Target, CouplingMap
from qiskit_ibm_runtime.fake_provider import FakeEssexV2

DEBUG = False
IMAGE_PATH = "img/"

# In the future also ignore parameterized rotational gates
IGNORE_GATES = set(["id", "measure"])

# Dict keys
GATE_NAME = "gate_name"
ERROR = "error"

"""
    For a target returns a dictiory of minimal error gate for each qubit
"""
def get_errors(target):
    # Dict of minimal error gate for each qubit in the form: {qubit_nr: {min_error, gate_name}}
    errors = {}

    # Get all single-qubit gate names available in the target
    single_qubit_gates = set()

    for inst in target.instructions:
        if inst[0].num_qubits == 1:
            single_qubit_gates.add(inst[0].name)

    if DEBUG:
        print("Single-qubit gates:", single_qubit_gates)

    # Ignore some single-qubit gates not used for decoupling (e.g., measurment and identity)
    filtered_single_qubit_gates = single_qubit_gates - IGNORE_GATES

    # Find minimal error gates
    for gate_name in filtered_single_qubit_gates:

        inst_props = target[gate_name]
        for qubits, props in inst_props.items():
            # If we have an error for the gate and qubit
            if(props is not None and props.error is not None):
                curr_error = props.error
                
                # Ignore gates that have no error at all, as probably are not supported on the hardware
                if curr_error == 0.0:
                    break

                # Get qubit (as we have only single qubit gates here)
                qubit = qubits[0]

                # If there was a previously found error
                if (qubit in errors):
                    prev_error = errors[qubit][ERROR]

                    # Save the current gate if it has less error
                    if(curr_error < prev_error):
                        errors[qubit] = {ERROR: curr_error, GATE_NAME: gate_name}

                else:
                    errors[qubit] = {ERROR: curr_error, GATE_NAME: gate_name}

    if DEBUG:
        print(errors)

    return errors

"""
    Uses an error dictionary to add single qubit PadDynamicalDecoupling with minimal error single qubit gates to a pass manager.
"""
def add_dyn_decoupling(pass_manager, target, errors, durations=None):

    if durations is None:
        durations = target.durations

    # For each qbit run super with minimal error gate
    for qubit_key, val in errors.items():
        # DEBUG
        if(qubit_key == 0):
            gate_name = val[GATE_NAME]

            instruction = target.operation_from_name(gate_name)
            if DEBUG:
                print("Added decoupling:")
                print(instruction)
                print(qubit_key)
            dd_sequence = [instruction, instruction]
            
            dec = PadDynamicalDecoupling(durations, dd_sequence, qubits=qubit_key)

        pass_manager.append(ALAPScheduleAnalysis(durations))
        pass_manager.append(dec)

    return pass_manager

# ---------------------------------------
# Create Mock circuit
# ---------------------------------------

circ = QuantumCircuit(4)
circ.h(0)
circ.cx(0, 1)
circ.cx(1, 2)
circ.cx(2, 3)
circ.measure_all()
durations = InstructionDurations(
    [("h", None, 50), ("cx", [0, 1], 700), ("reset", None, 10),
     ("cx", [1, 2], 200), ("cx", [2, 3], 300),
     ("x", None, 50), ("measure", None, 1000)],
    dt=1e-7
)
target = Target.from_configuration(
    ["h", "cx", "reset", "x", "measure"],
    num_qubits=4,
    coupling_map=CouplingMap.from_line(4, bidirectional=False),
    instruction_durations=durations,
    dt=1e-7,
)

# Mock errors for x gates
inst_props = target["x"]
for qubits, props in inst_props.items():
    if props is not None:
        props.error = 0.2

# Mock errors for h gates
inst_props = target["h"]
for qubits, props in inst_props.items():
    if props is not None:
        props.error = 0.1

circ.draw('mpl', filename=IMAGE_PATH+'circuit.png')

# ---------------------------------------
# Baseline without decoupling
# ---------------------------------------

# Create pass manager
pass_manager = PassManager()
pass_manager.scheduling = PassManager([ALAPScheduleAnalysis(durations)])

# Run the circuit through the pass manager
transpiled_circuit = pass_manager.run(circ)
timeline_drawer(transpiled_circuit, target=target, filename=IMAGE_PATH+"timeline.png")

# ---------------------------------------
# With Dynamic Decoupling
# ---------------------------------------

# Create pass manager
scheduling = PassManager()
scheduling.append(ALAPScheduleAnalysis(durations))

# Use balanced X-X sequence on all qubits
dd_sequence = [lib.XGate(), lib.XGate()]
scheduling.append(PadDynamicalDecoupling(durations, dd_sequence=dd_sequence))

# Run the circuit through the pass manager
transpiled_circuit = scheduling.run(circ)
timeline_drawer(transpiled_circuit, target=target, filename=IMAGE_PATH+"timeline_dyn_dec.png")

# ---------------------------------------
# With Single Qubit Optimized Dynamic Decoupling
# ---------------------------------------

# Get target specific errors
errors = get_errors(target)

# Create pass manager
scheduling = PassManager()
scheduling = add_dyn_decoupling(scheduling, target, errors, durations)

# Run the circuit through the pass manager
transpiled_circuit = scheduling.run(circ)
timeline_drawer(transpiled_circuit, target=target, filename=IMAGE_PATH+"timeline_dyn_dec_custom.png")

# ---------------------------------------
# Backend Compatiblity 
# ---------------------------------------

backend = FakeEssexV2()
target=backend.target
durations = target.durations()

# Get target specific errors
errors = get_errors(target)

# Create pass manager
scheduling = PassManager()
scheduling = add_dyn_decoupling(scheduling, target, errors, durations)

# Show created pass manager
scheduling.draw(IMAGE_PATH+"provider_pass_manager.png")