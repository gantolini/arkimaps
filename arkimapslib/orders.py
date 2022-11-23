# from __future__ import annotations
from typing import Dict, List, Optional, Any
import logging

# if TYPE_CHECKING:
from . import inputs
from . import steps


class Order:
    """
    Serializable instructions to prepare a product, based on a recipe and its
    input files
    """
    def __init__(
            self, *,
            mixer: str,
            input_files: Dict[str, inputs.InputFile],
            relpath: str,
            basename: str,
            recipe_name: str,
            instant: "inputs.Instant",
            order_steps: List[steps.Step],
            output_options: Dict[str, Any],
            log: logging.Logger,
            ):
        # Name of the Mixer to use
        self.mixer = mixer
        # Dict mapping source names to pathnames of GRIB files
        self.input_files = input_files
        # Destination directory inside the output
        self.relpath = relpath
        # Destination file name (without path or .png extension)
        self.basename = basename
        # Recipe name
        self.recipe_name = recipe_name
        # Product instant
        self.instant = instant
        # Output file name, set after the product has been rendered
        self.output: Optional[str] = None
        # Extra options to be passed to Magics' output() macro
        self.output_options = output_options
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

    @classmethod
    def summarize_orders(cls, orders: List["Order"]) -> Dict[str, Any]:
        """
        Summarize a list of orders into a json-able structure
        """
        # TODO: group by flavour and recipe
        # TODO: group instants by reftime
        return {}
