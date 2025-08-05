from cheetah.particles import ParticleBeam
from cheetah.accelerator import Screen
import torch
from ..virtual_accelerator import VirtualAccelerator
import os


class TestVirtualAccelerator:
    def setup_method(self):
        # Create a mock initial beam distribution
        beam = ParticleBeam(
            particles=torch.tensor([[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]]),
            energy=torch.tensor(2e9 / 33.356),  # magnetic rigidity of 2 kG-m
        )

        # Initialize the virtual accelerator with a the diag0 lattice file and mapping file
        self.va = VirtualAccelerator(
            lattice_file=os.path.join(
                os.path.split(os.path.abspath(__file__))[0], "resources", "diag0.json"
            ),
            mapping_file=os.path.join(
                os.path.split(os.path.abspath(__file__))[0],
                "resources",
                "lcls_elements.csv",
            ),
            initial_beam_distribution=beam,
        )

    def test_set_pvs(self):
        # Set values for various PVS
        values = {
            "QUAD:DIAG0:190:BCTRL": 0.5,
            "XCOR:DIAG0:178:BCTRL": 0.1,
            "YCOR:DIAG0:199:BCTRL": 0.2,
            "TCAV:DIAG0:11:AREQ": 1.0,
            "TCAV:DIAG0:11:PREQ": 45.0,
        }

        self.va.set_pvs(values)

        # Verify that the values were set correctly
        assert getattr(self.va.lattice, self.va.mapping["QUAD:DIAG0:190"].lower())[
            0
        ].k1 == torch.tensor(0.5) / 2.0
        assert getattr(
            self.va.lattice, self.va.mapping["XCOR:DIAG0:178"].lower()
        ).angle == torch.tensor(0.1) / 2.0
        assert getattr(
            self.va.lattice, self.va.mapping["YCOR:DIAG0:199"].lower()
        ).angle == torch.tensor(0.2) / 2.0
        assert getattr(self.va.lattice, self.va.mapping["TCAV:DIAG0:11"].lower())[
            0
        ].voltage == torch.tensor(1.0)
        assert getattr(self.va.lattice, self.va.mapping["TCAV:DIAG0:11"].lower())[
            0
        ].phase == torch.tensor(45.0)

        # verify that the simulation ran to populate readings
        for ele in self.va.lattice.elements:
            if hasattr(ele, "reading"):
                assert ele.reading is not None, (
                    f"Element {ele.name} did not populate readings after simulation run."
                )

    def test_get_pvs(self):
        # Get values for various PVS
        pv_names = [
            "QUAD:DIAG0:190:BCTRL",
            "XCOR:DIAG0:178:BCTRL",
            "YCOR:DIAG0:199:BACT",
            "TCAV:DIAG0:11:AREQ",
            "TCAV:DIAG0:11:PREQ",
            "BPMS:DIAG0:190:XSCDT1H",
            "BPMS:DIAG0:190:YSCDT1H",
            "OTRS:DIAG0:420:Image:ArrayData",
            "OTRS:DIAG0:525:Image:ArrayData",
        ]

        values = self.va.get_pvs(pv_names)

        for name, value in values.items():
            assert torch.all(~torch.isnan(value))


    def test_set_shutter(self):
        # Set the beam shutter to open
        self.va.set_shutter(True)
        assert self.va.initial_beam_distribution.particle_charges.item() == 0.0

        # verify that there is no signal on the screen readings
        for ele in self.va.lattice.elements:
            if isinstance(ele, Screen):
                assert torch.all(ele.reading == 0.0), (
                    f"Element {ele.name} did not have zero reading after shutter opened."
                )

        # Set the beam shutter to closed
        self.va.set_shutter(False)
        assert self.va.initial_beam_distribution.particle_charges.item() == self.va.initial_beam_distribution_charge.item()

        # test with shutter PV
        self.va.beam_shutter_pv = "BEAM:SHUTTER:STATE"
        self.va.set_pvs({"BEAM:SHUTTER:STATE": True})
        assert self.va.initial_beam_distribution.particle_charges.item() == 0.0

        self.va.set_pvs({"BEAM:SHUTTER:STATE": False})
        assert self.va.initial_beam_distribution.particle_charges.item() == self.va.initial_beam_distribution_charge.item()

        assert self.va.get_pvs(["BEAM:SHUTTER:STATE"]) == {"BEAM:SHUTTER:STATE": torch.tensor(False)}
