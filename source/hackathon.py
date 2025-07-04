import numpy as np
import os
import csv
import time
from collections import defaultdict
from itertools import combinations
from qiskit import QuantumCircuit, qasm2, transpile
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.circuit import library as lib
from qiskit.visualization import pass_manager_drawer, staged_pass_manager_drawer
from qiskit.passmanager.base_tasks import Task
from qiskit.transpiler import PassManager, StagedPassManager, generate_preset_pass_manager
from qiskit.transpiler.preset_passmanagers.plugin import list_stage_plugins
from qiskit.transpiler.passes import (
    ALAPScheduleAnalysis,
    InverseCancellation,
    PadDynamicalDecoupling,
    UnitarySynthesis,
    Unroll3qOrMore,
    Collect2qBlocks,
    ConsolidateBlocks,
    Optimize1qGates,
    Collect1qRuns,
    HoareOptimizer,
    Optimize1qGates,
    Optimize1qGatesDecomposition,
    Collect1qRuns,
    Collect2qBlocks,
    CollectMultiQBlocks,
    CollectAndCollapse,
    CollectLinearFunctions,
    CollectCliffords,
    ConsolidateBlocks,
    InverseCancellation,
    CommutationAnalysis,
    CommutativeCancellation,
    CommutativeInverseCancellation,
    Optimize1qGatesSimpleCommutation,
    RemoveDiagonalGatesBeforeMeasure,
    RemoveResetInZeroState,
    RemoveFinalReset,
    HoareOptimizer,
    TemplateOptimization,
    ResetAfterMeasureSimplification,
    OptimizeCliffords,
    ElidePermutations,
    OptimizeAnnotated,
    Split2QUnitaries,
    RemoveIdentityEquivalent,
    ContractIdleWiresInControlFlow,
    OptimizeCliffordT,
)

def create_pass_manager():
    backend = GenericBackendV2(num_qubits=5)
    
    basis_gates = ["rx", "ry", "rxx"]
    init = PassManager(
        [UnitarySynthesis(basis_gates, min_qubits=3), Unroll3qOrMore()]
    )
    translate = PassManager(
        [
            Collect2qBlocks(),
            ConsolidateBlocks(basis_gates=basis_gates),
            UnitarySynthesis(basis_gates),
        ]
    )
    staged_pm = StagedPassManager(
        stages=["init", "translation"], init=init, translation=translate
    )
    dd_sequence = [lib.XGate(), lib.XGate()]
    scheduling = PassManager(
        [
            ALAPScheduleAnalysis(target=backend.target),
            PadDynamicalDecoupling(target=backend.target, dd_sequence=dd_sequence),
        ]
    )
    inverse_gate_list = [
        lib.CXGate(),
        lib.HGate(),
        (lib.RXGate(np.pi / 4), lib.RXGate(-np.pi / 4)),
        (lib.PhaseGate(np.pi / 4), lib.PhaseGate(-np.pi / 4)),
        (lib.TGate(), lib.TdgGate()),
    ]
    logical_opt = PassManager([InverseCancellation(inverse_gate_list)])
    
    staged_pass_manager: StagedPassManager = generate_preset_pass_manager(optimization_level=0)
    # Add pre-layout stage to run extra logical optimization
    staged_pass_manager.pre_layout = logical_opt

    # Set scheduling stage to custom pass manager
    #pass_manager.scheduling = scheduling
    staged_pass_manager.optimization = PassManager(
        [
            Optimize1qGates(),
            Collect1qRuns(),
            HoareOptimizer(),
        ]
    )
    #print(pass_manager.optimization_method)
    print(list_stage_plugins("optimization"))
    #pass_manager_drawer(pm, filename="preset_pass_manager.png")
    #staged_pass_manager_drawer(staged_pass_manager, filename"C:\\Users\\nickp\\dev\\qiskit-hackathon\\preset_pass_manager.png")
    #staged_pass_manager.draw()

    return staged_pass_manager

# optimization_level: 0 - 3

def get_pass_manager(optimizations: list[Task]) -> StagedPassManager:
    staged_pass_manager = StagedPassManager(stages=["init", "layout", "routing", "translation"])
    # staged_pass_manager: StagedPassManager = generate_preset_pass_manager(optimization_level=0)
    staged_pass_manager.optimization = PassManager(optimizations)
    return staged_pass_manager


# Transpilation process
#circuit = get_circuit()

optimizations = [] # [ [Optimize1qGates(), Collect1qRuns(), HoareOptimizer()], [Collect1qRuns()] ]

OPTIMIZER_CLASSES = [
    Optimize1qGates,
    Optimize1qGatesDecomposition,
    Collect1qRuns,
    Collect2qBlocks,
    CollectMultiQBlocks,
    #CollectAndCollapse,
    CollectLinearFunctions,
    CollectCliffords,
    #ConsolidateBlocks,
    #InverseCancellation,
    CommutationAnalysis,
    CommutativeCancellation,
    ###CommutativeInverseCancellation, AttributeError: 'Clifford' object has no attribute 'base_class'
    ###Optimize1qGatesSimpleCommutation, AttributeError: 'Clifford' object has no attribute 'is_parameterized'
    RemoveDiagonalGatesBeforeMeasure,
    RemoveResetInZeroState,
    RemoveFinalReset,
    HoareOptimizer,
    #TemplateOptimization,
    ResetAfterMeasureSimplification,
    OptimizeCliffords,
    ElidePermutations,
    OptimizeAnnotated,
    Split2QUnitaries,
    RemoveIdentityEquivalent,
    ContractIdleWiresInControlFlow,
    OptimizeCliffordT,
]


def generate_optimizer_combinations(min_size=1, max_size=3) -> list[list[Task]]:
    """
    Generate all combinations of optimizer passes up to max_size.
    Returns a list of lists, each inner list is a combination of instantiated passes.
    """
    all_combinations = []
    for r in range(min_size, max_size + 1):
        for combo in combinations(OPTIMIZER_CLASSES, r):
            # Instantiate each pass (no-arg constructors assumed)
            all_combinations.append([cls() for cls in combo])
    return all_combinations

def get_configuration_vector(optimizers: list[Task]) -> list[int]:
    """
    Generate a configuration vector for the given combinations of optimizer passes.
    Each pass is represented by a 1 in the vector, and 0 otherwise.
    """
    vector = [0] * len(OPTIMIZER_CLASSES)
    for i, optimizer_class in enumerate(OPTIMIZER_CLASSES):
        if optimizer_class() in optimizers:
            vector[i] = 1
    return vector

def print_circuit(circuit: QuantumCircuit):
    circuit.draw("mpl", idle_wires=False)
    print(circuit)


def get_explanatory_variables(circuit: QuantumCircuit) -> list[int]:
    """
    Extract explanatory variables from the circuit.
    Returns a list of integers representing the number of qubits, width, depth, and gate counts.
    """
    cnot_count = circuit.count_ops().get('cx') or 0
    t_count = circuit.count_ops().get('t') or 0
    count_multi_qbit_gates = defaultdict(int)
    for entry in circuit.data:
        count_multi_qbit_gates[len(entry.qubits)] += 1
    two_qbit_gate_count = count_multi_qbit_gates.get(2) or 0
    three_qbit_gate_count = count_multi_qbit_gates.get(3) or 0

    return [
        circuit.num_qubits,
        circuit.depth(),
        circuit.width(),
        circuit.size(),
        cnot_count,
        t_count,
        two_qbit_gate_count,
        three_qbit_gate_count,
    ]

def get_quality_data(circuit: QuantumCircuit) -> list[int]:
    """
    Extract quality data from the circuit.
    Returns a list of integers representing various quality metrics.
    """
    cnot_count = circuit.count_ops().get('cx') or 0
    t_count = circuit.count_ops().get('t') or 0
    return [
        circuit.depth(),
        circuit.width(),
        circuit.size(),
        cnot_count,
        t_count,
        circuit.num_ancillas,
        circuit.num_captured_stretches,
        circuit.num_captured_vars,
        circuit.num_declared_stretches,
        circuit.num_clbits,
        circuit.num_identifiers,
        circuit.num_input_vars,
        circuit.num_stretches,
        circuit.num_vars,
        circuit.num_unitary_factors(),
        circuit.num_tensor_factors(),
        circuit.num_connected_components(),
    ]

#circuit_path = "circuits_target_qiskit"
circuit_path = "circuits_qiskit_opt0"
for circuit_class_dir in os.listdir(circuit_path):
    class_dir_path = os.path.join(circuit_path, circuit_class_dir)
    if not os.path.isdir(class_dir_path):
        continue

    with open(f'./circuit_data/{circuit_class_dir}.csv', mode='a', newline='') as circuit_file:
        circuit_writer = csv.writer(circuit_file)

        for filename in os.listdir(class_dir_path):
            if not filename.endswith('.qasm'):
                continue
            
            transpiled_data_file = f'./transpiled_data/{circuit_class_dir}/{filename}.csv'
            if os.path.exists(transpiled_data_file):
                continue  # Skip if already processed

            circuit_count = filename.split("_")[-1][:-5] # Extract the number from the filename
            type = filename[:-(5 + len(circuit_count) + 1)]
            print(f"Processing circuit: {filename} with count {circuit_count} of type {type}")
            if int(circuit_count) > 25:
                continue

            class_dir_path = os.path.join(circuit_path, circuit_class_dir, filename)

            # interpret openqasm als qiskit QuantumCircuit
            circuit = qasm2.load(filename=class_dir_path, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)

            optimizer_combinations = generate_optimizer_combinations(3, 3)

            os.makedirs(f'./transpiled_data/{circuit_class_dir}', exist_ok=True)

            with open(transpiled_data_file, mode='a', newline='') as transpiled_file:
                # Do passes until optimization to get explanatory variables from the circuit we use to start the optimization
                pass_manager = StagedPassManager(stages=["init", "layout", "routing", "translation"])
                translated = pass_manager.run(circuit)
                x_variables = get_explanatory_variables(translated)
                circuit_writer.writerow([filename] + x_variables)

                transpiled_writer = csv.writer(transpiled_file)
                opt_start_time = time.perf_counter()

                for i, optimizations in enumerate(optimizer_combinations):
                    # Do optimization pass
                    optimize_pass_manager_level0 : StagedPassManager = generate_preset_pass_manager(optimization_level=0)
                    optimize_pass_manager_level0.optimization = PassManager(optimizations)

                    # load best x (10) configurations per circuit - with columns: circuit_name, features, configuration_vector
                    vec = get_configuration_vector(optimizations)

                    # Transpile it by calling the run method of the pass manager
                    start_time = time.perf_counter()
                    transpiled_level0 = optimize_pass_manager_level0.run(translated)
                    elapsed_time = time.perf_counter() - start_time

                    transpiled_writer.writerow([vec] + get_quality_data(transpiled_level0) + [elapsed_time])

                opt_elapsed_time = time.perf_counter() - opt_start_time
                print(f"Optimizations took {opt_elapsed_time:.2f} seconds for {filename} with {len(optimizer_combinations)} combinations.")

