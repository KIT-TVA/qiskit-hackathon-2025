from qiskit.transpiler.passes import PadDynamicalDecoupling

from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.instruction_durations import InstructionDurations
from qiskit.circuit import Gate
from qiskit.transpiler.target import Target
from qiskit.transpiler import PassManager

# Also ignore parameterized rotational gates
IGNORE_GATES = set(["id", "measure"])
DEBUG = False
GATE_NAME = "gate_name"
ERROR = "error"


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

                qubit = qubits[0]

                if DEBUG:
                    print(gate_name, qubit, curr_error)

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

def add_dyn_decoupling(pass_manager, target, errors):

    # For each qbit run super with minimal error gate
    for qubit_key, val in errors.items():
        gate_name = val[GATE_NAME]

        instruction = target.operation_from_name(gate_name)
        if DEBUG:
            print(instruction)
        dd_sequence = [instruction, instruction]

        durations = target.durations
        dec = PadDynamicalDecoupling(durations, dd_sequence, qubits=qubit_key)

        pass_manager.append(dec)

    return pass_manager


from qiskit.circuit import library as lib
from qiskit.transpiler.passes import (
    UnitarySynthesis,
    Unroll3qOrMore,
    Collect2qBlocks,
    ConsolidateBlocks,
    ALAPScheduleAnalysis,
    # InverseCancellation,
    # Optimize1qGates,
    # Collect1qRuns,
    # HoareOptimizer,
)
from qiskit.transpiler import StagedPassManager, generate_preset_pass_manager
from qiskit.transpiler.preset_passmanagers.plugin import list_stage_plugins
import numpy as np

def create_pass_manager(backend):
    
    # basis_gates = ["rx", "ry", "rxx"]

    basis_gates = []
    config = backend.configuration()
    for instruction in config.supported_instructions:
        basis_gates.append(instruction)

    init = PassManager(
        [
            UnitarySynthesis(basis_gates, min_qubits=3),
            # Unroll3qOrMore()
        ]
    )
    translate = PassManager(
        [
            # Collect2qBlocks(),
            # ConsolidateBlocks(basis_gates=basis_gates),
            # UnitarySynthesis(basis_gates),
        ]
    )
    staged_pm = StagedPassManager(
        # TODO
        stages=["init", "translation"], init=init, translation=translate
    )

    return staged_pm

from qiskit_ibm_runtime.fake_provider import FakeBoeblingenV2
from qiskit_ibm_runtime.fake_provider import FakeCairoV2
from qiskit_ibm_runtime.fake_provider import FakeVigoV2
from qiskit.providers.fake_provider import GenericBackendV2

backend = FakeCairoV2()
# backend = GenericBackendV2(num_qubits=12)
# TODO for a generic backend we have to mock a config
target=backend.target

# if DEBUG:
#     my_pass.draw(filename='test.png')

# # TODO example
from qiskit import QuantumRegister, ClassicalRegister, QuantumCircuit
q = QuantumRegister(3, 'q')
c = ClassicalRegister(3, 'c')
circ = QuantumCircuit(q, c)

circ.h(q[0])
circ.cx(q[0], q[2])
circ.h(q[0])
circ.cx(q[0], q[1])
circ.rz(0.5, q[1])
circ.cx(q[0], q[1])
circ.h(q[0])
circ.cx(q[0], q[1])
circ.rzz(10,q[0], q[1])
circ.h(q[0])
circ.cx(q[0], q[1])
circ.rz(0.5, q[1])
circ.cx(q[0], q[1])
circ.h(q[0])
circ.cx(q[0], q[1])
circ.rzz(10,q[0], q[1])
circ.h(q[0])
circ.cx(q[0], q[1])
circ.rz(0.5, q[1])
circ.cx(q[0], q[1])
circ.h(q[0])
circ.cx(q[0], q[1])
circ.rzz(10,q[0], q[1])
circ.h(q[0])
circ.cx(q[0], q[1])
circ.rz(0.5, q[1])
circ.cx(q[0], q[1])
circ.h(q[0])
circ.cx(q[0], q[1])
circ.rzz(10,q[0], q[1])
circ.h(q[0])
circ.cx(q[0], q[1])
circ.rz(0.5, q[1])
circ.cx(q[0], q[1])
circ.h(q[0])
circ.cx(q[0], q[1])
circ.rzz(10,q[0], q[1])

# circ.delay(1000, 0, unit='dt')   # simulate a delay


circ.cx(q[0], q[2])
circ.measure(q[0], c[0])

# from qiskit.circuit.library import efficient_su2
# circ = efficient_su2(12, entanglement="circular", reps=1)
# rng = np.random.default_rng(1234)
# circ.assign_parameters(
#     rng.uniform(-np.pi, np.pi, circ.num_parameters), inplace=True
# )

circ.draw('mpl', filename='circuit.png')
print(target.durations())

# from qiskit.transpiler.preset_passmanagers import level_3
# from qiskit.transpiler import PassManagerConfig

# # Pretranspile
# # Create a pass manager configured for the backend
# pm_config = PassManagerConfig(backend=backend)
# pass_manager = level_3(pass_manager_config=pm_config)

# Baseline

pass_manager = create_pass_manager(backend)

errors = get_errors(target)
scheduling = PassManager()
scheduling.append(ALAPScheduleAnalysis(target=backend.target))
# scheduling = add_dyn_decoupling(scheduling, target, errors)

pass_manager.scheduling = scheduling

# Run the circuit through the pass manager
transpiled_circuit = pass_manager.run(circ)
transpiled_circuit.draw('mpl', filename='circuit_transpiled.png')

# With Dyn Dec
pass_manager = create_pass_manager(backend)

errors = get_errors(target)
scheduling = PassManager()
scheduling.append(ALAPScheduleAnalysis(target=backend.target))
# TODO 
dd_sequence = [lib.XGate(), lib.XGate()]
scheduling.append(PadDynamicalDecoupling(target=backend.target, dd_sequence=dd_sequence))

pass_manager.scheduling = scheduling

# Run the circuit through the pass manager
transpiled_circuit = pass_manager.run(circ)
transpiled_circuit.draw('mpl', filename='circuit_transpiled_dyn_dec.png')
# from qiskit.visualization import timeline_drawer
# timeline_drawer(transpiled_circuit, target=target)

# With Custom Dyn Dec
pass_manager = create_pass_manager(backend)

errors = get_errors(target)
scheduling = PassManager()
scheduling.append(ALAPScheduleAnalysis(target=backend.target))
scheduling = add_dyn_decoupling(scheduling, target, errors)

pass_manager.scheduling = scheduling

# Run the circuit through the pass manager
transpiled_circuit = pass_manager.run(circ)
transpiled_circuit.draw('mpl', filename='circuit_transpiled_dyn_dec_custom.png')

