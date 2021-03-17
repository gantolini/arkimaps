# from __future__ import annotations
from typing import Dict, List
import logging
import os

# if TYPE_CHECKING:


class Order:
    """
    Serializable instructions to prepare a product, based on a recipe and its
    input files
    """
    def __init__(
            self,
            mixer: str,
            sources: Dict[str, "inputs.InputFile"],
            recipe_name: str,
            step: int,
            order_steps: List["steps.Step"],
            log: logging.Logger):
        # Name of the Mixer to use
        self.mixer = mixer
        # Dict mapping source names to pathnames of GRIB files
        self.sources = sources
        # Destination file name (without path or .png extension)
        self.basename = f"{recipe_name}+{step:03d}"
        # Recipe name
        self.recipe_name = recipe_name
        # Product step
        self.step = step
        # Output file name, set after the product has been rendered
        self.output = None
        # Logger for this output
        self.log = log
        # List of recipe steps instantiated for this order
        self.order_steps = order_steps

    def __getstate__(self):
        state = self.__dict__.copy()
        # logger objects don't pickle correctly on python 3.6
        del state['log']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.log = logging.getLogger(f"arkimaps.order.{self.basename}")

    def __str__(self):
        return self.basename

    def __repr__(self):
        return self.basename

    def prepare(self, workdir: str):
        """
        Run all the steps of the recipe and render the resulting file
        """
        from .worktops import Worktop

        output_pathname = os.path.join(workdir, self.basename)
        worktop = Worktop(output_pathname=output_pathname)
        for step in self.order_steps:
            step.python_trace(worktop)
        for step in self.order_steps:
            step.run(worktop)
        worktop.write_python_trace()
        worktop.write_product()
        self.output = output_pathname + ".png"
