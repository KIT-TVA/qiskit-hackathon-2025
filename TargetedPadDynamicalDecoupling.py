from qiskit.transpiler.passes import PadDynamicalDecoupling

from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.instruction_durations import InstructionDurations
from qiskit.circuit import Gate
from qiskit.transpiler.target import Target
from qiskit.transpiler import PassManager

# TODO rename and maybe extend pass manager
class TargetedPadDynamicalDecoupling():

    IGNORE_GATES = set(["id", "measure"])
    DEBUG = False
    # Dict of minimal error gate for each qubit in the form: {qubit_nr: {min_error, gate_name}}
    errors = {}
    target = None

    """
        On initialization for a target get the minimal error gate for each qubit 
    """
    def __init__(
        self,
        durations: InstructionDurations = None,
        # TODO fix parameters
        # qubits: list[int] | None = None,
        # spacing: list[float] | None = None,
        # skip_reset_qubits: bool = True,
        # pulse_alignment: int = 1,
        # extra_slack_distribution: str = "middle",
        target: Target = None,
    ):  
        # # Super with empty dd_sequence, as we will later set them individually
        # super().__init__(dd_sequence = [], target=target)
        self.target=target

        # Get all single-qubit gate names available in the target
        single_qubit_gates = set()

        for inst in target.instructions:
            if inst[0].num_qubits == 1:
                single_qubit_gates.add(inst[0].name)

        if self.DEBUG:
            print("Single-qubit gates:", single_qubit_gates)


        # Ignore some single-qubit gates not used for decoupling (e.g., measurment and identity)
        filtered_single_qubit_gates = single_qubit_gates - self.IGNORE_GATES

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

                    if self.DEBUG:
                        print(gate_name, qubit, curr_error)

                    # If there was a previously found error
                    if (qubit in self.errors):
                        prev_error = self.errors[qubit]["error"]

                        # Save the current gate if it has less error
                        if(curr_error < prev_error):
                            self.errors[qubit] = {"error": curr_error, "gate_name": gate_name}

                    else:
                        self.errors[qubit] = {"error": curr_error, "gate_name": gate_name}

        if self.DEBUG:
            print(self.errors)

    
    """
    TODO

    """
    def create(self):
        pass_manager = PassManager()

        # For each qbit run super with minimal error gate
        for qubit_key, val in self.errors.items():
            # TODO fix magic strings
            gate_name = val["gate_name"]

            instruction = self.target.operation_from_name(gate_name)
            if self.DEBUG:
                print(instruction)
            dd_sequence = [instruction, instruction]

            # TODO: pass durations
            dec = PadDynamicalDecoupling(durations, dd_sequence, qubits=qubit_key)
            # TODO: store in passmanager?
            pass_manager.append(dec)

        return pass_manager

    

from qiskit_ibm_runtime.fake_provider import FakeBoeblingenV2
from qiskit_ibm_runtime.fake_provider import FakeCairoV2
from qiskit_ibm_runtime.fake_provider import FakeVigoV2

backend = FakeBoeblingenV2()

# TODO ?!?
durations = InstructionDurations(
    [("h", 0, 50), ("cx", [0, 1], 700), ("reset", None, 10),
     ("cx", [1, 2], 200), ("cx", [2, 3], 300),
     ("x", None, 50), ("measure", None, 1000)],
    dt=1e-7
)

my_pass = TargetedPadDynamicalDecoupling(durations, target=backend.target).create()
# my_pass.draw(filename='test.png')

# # TODO example
# from qiskit import QuantumRegister, ClassicalRegister, QuantumCircuit
# from qiskit.dagcircuit import DAGCircuit
# from qiskit.converters import circuit_to_dag
# q = QuantumRegister(3, 'q')
# c = ClassicalRegister(3, 'c')
# circ = QuantumCircuit(q, c)
# circ.h(q[0])
# circ.cx(q[0], q[1])
# circ.measure(q[0], c[0])
# circ.rz(0.5, q[1])

# from qiskit.transpiler.preset_passmanagers import level_3
# from qiskit.transpiler import PassManagerConfig

# # Pretranspile
# # Create a pass manager configured for the backend
# pm_config = PassManagerConfig(backend=backend)
# pass_manager = level_3(pass_manager_config=pm_config)
# pass_manager.append(my_pass)

# # Run the circuit through the pass manager
# transpiled_circuit = pass_manager.run(circ)


