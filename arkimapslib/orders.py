# from __future__ import annotations
import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

if TYPE_CHECKING:
    import datetime

    from . import inputs, steps
    from .flavours import Flavour
    from .kitchen import Kitchen
    from .recipes import Recipe


class Order:
    """
    Serializable instructions to prepare a product, based on a recipe and its
    input files
    """
    def __init__(
            self, *,
            flavour: "Flavour",
            recipe: "Recipe",
            input_files: Dict[str, "inputs.InputFile"],
            relpath: str,
            basename: str,
            instant: "inputs.Instant",
            order_steps: List["steps.Step"],
            output_options: Dict[str, Any],
            log: logging.Logger,
            ):
        # Reference to the flavour to use for summaries. It will be lost for
        # rendering, to avoid pickling the complex structure
        self.flavour: Optional["Flavour"] = flavour
        # Reference to the recipe to use for summaries. It will be lost for
        # rendering, to avoid pickling the complex structure
        self.recipe: Optional["Recipe"] = recipe
        # Name of the Mixer to use
        self.mixer = recipe.mixer
        # Dict mapping source names to pathnames of GRIB files
        self.input_files = input_files
        # Destination directory inside the output
        self.relpath = relpath
        # Destination file name (without path or .png extension)
        self.basename = basename
        # Flavour name
        self.flavour_name = flavour.name
        # Recipe name
        self.recipe_name = recipe.name
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
        # If this order generates a legend, this is information about the
        # legend to be forwarded to the summary
        self.legend_info: Optional[Dict[str, Any]] = None
        # Summary stats about the rendering
        self.render_time_ns: int = 0

    def __getstate__(self):
        state = self.__dict__.copy()
        # logger objects don't pickle correctly on python 3.6
        del state['log']
        # Avoid pickling complex structures that we don't need
        del state['flavour']
        del state['recipe']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.log = logging.getLogger(f"arkimaps.order.{self.basename}")
        self.flavour = None
        self.recipe = None

    def __str__(self):
        return self.basename

    def __repr__(self):
        return self.basename

    @classmethod
    def summarize_orders(cls, kitchen: "Kitchen", orders: List["Order"]) -> List[Dict[str, Any]]:
        """
        Summarize a list of orders into a json-able structure
        """
        result: List[Dict[str, Any]] = []

        by_fr: Dict[str, List[Order]] = defaultdict(list)

        # Group by flavour and recipe
        for order in orders:
            by_fr[(order.flavour_name, order.recipe_name)].append(order)

        for (flavour_name, recipe_name), orders_fr in by_fr.items():
            record = {
                "flavour": kitchen.flavours[flavour_name].summarize(),
                "recipe": kitchen.recipes.get(recipe_name).summarize(),
                "reftimes": {},
            }

            # Group orders by reftime
            by_rt: Dict[datetime.datetime, List[Order]] = defaultdict(list)
            for order in orders_fr:
                by_rt[order.instant.reftime].append(order)

            for reftime, orders in by_rt.items():
                inputs: Set[str] = set()
                steps: Set[int] = set()
                legend_info: Optional[Dict[str, Any]] = None
                render_time_ns: int = 0
                for order in orders:
                    inputs.update(order.input_files.keys())
                    steps.add(order.instant.step)
                    if order.legend_info:
                        legend_info = order.legend_info
                    render_time_ns += order.render_time_ns
                record_rt = {
                    "inputs": sorted(inputs),
                    "steps": sorted(steps),
                    "legend_info": legend_info,
                    "render_stats": {
                        "time_ns": render_time_ns,
                    },
                }
                record["reftimes"][reftime.strftime("%Y-%m-%d %H:%M-%S")] = record_rt

            result.append(record)

        return result
