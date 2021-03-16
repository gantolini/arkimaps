# from __future__ import annotations
from typing import Dict, Any, Optional, Set

# if TYPE_CHECKING:
from . import mixers
from . import inputs
from . import flavours
# Used for kwargs-style dicts
Kwargs = Dict[str, Any]


class Step:
    """
    One recipe step provided by a Mixer
    """
    defaults: Optional[Kwargs] = None

    def __init__(self,
                 step: str,
                 step_config: "flavours.StepConfig",
                 params: Optional[Kwargs],
                 sources: Dict[str, inputs.InputFile]):
        self.name = step
        self.params = self.compile_args(step_config, params)

    def is_skipped(self) -> bool:
        return bool(self.params.get("skip"))

    def run(self, mixer: "mixers.Mixer"):
        raise NotImplementedError(f"{self.__class__.__name__}.run not implemented")

    def python_trace(self, mixer: "mixers.Mixer"):
        """
        Store in the mixer the python code that reproduces this step
        """
        raise NotImplementedError(f"{self.__class__.__name__}.run not implemented")

    @classmethod
    def compile_args(cls, step_config: "flavours.StepConfig", args: Kwargs) -> Dict[str, Any]:
        """
        Compute the set of arguments for this step, based on flavour
        information and arguments defined in the recipe
        """
        # take args
        res = dict(args)

        # add missing bits from step_config
        for k, v in step_config.options.items():
            res.setdefault(k, v)

        # add missing bits from class config
        if cls.defaults is not None:
            for k, v in cls.defaults.items():
                res.setdefault(k, v)

        return res

    @classmethod
    def get_input_names(cls, step_config: "flavours.StepConfig", args: Kwargs) -> Set[str]:
        """
        Return the list of input names used by this step
        """
        return set()


class MagicsMacro(Step):
    """
    Run a Magics macro with optional default arguments
    """
    macro_name: str

    def run(self, mixer: "mixers.Mixer"):
        params = self.params.get("params", {})
        mixer.parts.append(getattr(mixer.macro, self.macro_name)(**params))

    def python_trace(self, mixer: "mixers.Mixer"):
        params = self.params.get("params", {})
        mixer.py_lines.append(f"parts.append(macro.{self.macro_name}(**{params!r}))")


class AddBasemap(MagicsMacro):
    """
    Add a base map
    """
    macro_name = "mmap"


class AddCoastlinesBg(MagicsMacro):
    """
    Add background coastlines
    """
    macro_name = "mcoast"
    defaults = {
        "params": {
            "map_coastline_general_style": "background",
        },
    }


class AddSymbols(MagicsMacro):
    """
    Add symbols settings
    """
    macro_name = "msymb"
    defaults = {
        "params": {
            "symbol_type": "marker",
            "symbol_marker_index": 15,
            "legend": "off",
            "symbol_colour": "black",
            "symbol_height": 0.28,
        },
    }


class AddContour(MagicsMacro):
    """
    Add contouring of the previous data
    """
    macro_name = "mcont"
    defaults: {
        "params": {
            "contour_automatic_setting": "ecmwf",
        },
    }


class AddWind(MagicsMacro):
    """
    Add wind flag rendering of the previous data
    """
    macro_name = "mwind"


class AddGrid(MagicsMacro):
    """
    Add a coordinates grid
    """
    macro_name = "mcoast"
    defaults: {
        "params": {
            "map_coastline_general_style": "grid",
        },
    }


class AddCoastlinesFg(Step):
    """
    Add foreground coastlines
    """
    defaults: {
        "params": {
            "map_coastline_sea_shade_colour": "#f2f2f2",
            "map_grid": "off",
            "map_coastline_sea_shade": "off",
            "map_label": "off",
            "map_coastline_colour": "#000000",
            "map_coastline_resolution": "medium",
        },
    }

    def run(self, mixer: "mixers.Mixer"):
        params = self.params.get("params", {})
        mixer.parts.append(mixer.macro.mcoast(map_coastline_general_style="foreground"))
        mixer.parts.append(mixer.macro.mcoast(**params))

    def python_trace(self, mixer: "mixers.Mixer"):
        params = self.params.get("params", {})
        mixer.py_lines.append(f"parts.append(macro.mcoast(map_coastline_general_style='foreground'))")
        mixer.py_lines.append(f"parts.append(macro.mcoast(**{params!r}))")


class AddBoundaries(Step):
    """
    Add political boundaries
    """
    defaults: {
        "params": {
            'map_boundaries': "on",
            'map_boundaries_colour': "#504040",
            'map_administrative_boundaries_countries_list': ["ITA"],
            'map_administrative_boundaries_colour': "#504040",
            'map_administrative_boundaries_style': "solid",
            'map_administrative_boundaries': "on",
        },
    }

    def run(self, mixer: "mixers.Mixer"):
        params = self.params.get("params", {})
        mixer.parts.append(
            mixer.macro.mcoast(map_coastline_general_style="boundaries"),
        )
        mixer.parts.append(mixer.macro.mcoast(**params))

    def python_trace(self, mixer: "mixers.Mixer"):
        params = self.params.get("params", {})
        mixer.py_lines.append(f"parts.append(macro.mcoast(map_coastline_general_style='boundaries'))")
        mixer.py_lines.append(f"parts.append(macro.mcoast(**{params!r}))")


class AddGrib(Step):
    """
    Add a grib file
    """
    def __init__(self,
                 step: str,
                 step_config: "flavours.StepConfig",
                 params: Optional[Kwargs],
                 sources: Dict[str, inputs.InputFile]):
        super().__init__(step, step_config, params, sources)
        input_name = self.params.get("grib")
        inp = sources.get(input_name)
        if inp is None:
            raise KeyError(f"{self.name}: input {input_name} not found. Available: {', '.join(sources.keys())}")
        self.grib_input = inp

        if self.grib_input.info.mgrib:
            params = self.params.get("params")
            if params is None:
                self.params["params"] = params = {}
            for k, v in self.grib_input.info.mgrib.items():
                params.setdefault(k, v)

    def run(self, mixer: "mixers.Mixer"):
        params = dict(self.params.get("mgrib", {}))
        params.update(self.params.get("params", {}))
        mixer.parts.append(mixer.macro.mgrib(grib_input_file_name=self.grib_input.pathname, **params))

    def python_trace(self, mixer: "mixers.Mixer"):
        params = dict(self.params.get("mgrib", {}))
        params.update(self.params.get("params", {}))
        mixer.py_lines.append(
                f"parts.append(macro.mgrib(grib_input_file_name={self.grib_input.pathname!r}, **{params!r}))")

    @classmethod
    def get_input_names(cls, step_config: "flavours.StepConfig", args: Kwargs) -> Set[str]:
        res = super().get_input_names(step_config, args)
        args = cls.compile_args(step_config, args)
        grib_name = args.get("grib")
        if grib_name is not None:
            res.add(grib_name)
        return res


class AddUserBoundaries(Step):
    """
    Add user-defined boundaries from a shapefile
    """
    def __init__(self,
                 step: str,
                 step_config: "flavours.StepConfig",
                 params: Optional[Kwargs],
                 sources: Dict[str, inputs.InputFile]):
        super().__init__(step, step_config, params, sources)
        input_name = self.params.get("shape")
        inp = sources.get(input_name)
        if inp is None:
            raise KeyError(f"{self.name}: input {input_name} not found. Available: {', '.join(sources.keys())}")
        self.shape = inp

    def _run_params(self):
        params = {
            "map_user_layer": "on",
            "map_user_layer_colour": "blue",
        }
        params.update(self.params.get("params", {}))
        params["map_user_layer_name"] = self.shape.pathname
        return params

    def run(self, mixer: "mixers.Mixer"):
        params = self._run_params()
        mixer.parts.append(mixer.macro.mcoast(**params))

    def python_trace(self, mixer: "mixers.Mixer"):
        params = self._run_params()
        mixer.py_lines.append(f"parts.append(macro.mcoast(**{params!r}))")

    @classmethod
    def get_input_names(cls, step_config: "flavours.StepConfig", args: Kwargs) -> Set[str]:
        res = super().get_input_names(step_config, args)
        args = cls.compile_args(step_config, args)
        shape = args.get("shape")
        if shape is not None:
            res.add(shape)
        return res


class AddGeopoints(Step):
    """
    Add geopoints
    """
    def __init__(self,
                 step: str,
                 step_config: "flavours.StepConfig",
                 params: Optional[Kwargs],
                 sources: Dict[str, inputs.InputFile]):
        super().__init__(step, step_config, params, sources)
        input_name = self.params.get("points")
        inp = sources.get(input_name)
        if inp is None:
            raise KeyError(f"{self.name}: input {input_name} not found. Available: {', '.join(sources.keys())}")
        self.points = inp

    def run(self, mixer: "mixers.Mixer"):
        params = dict(self.params.get("params", {}))
        params["geo_input_file_name"] = self.points.pathname
        mixer.parts.append(mixer.macro.mgeo(**params))

    def python_trace(self, mixer: "mixers.Mixer"):
        params = dict(self.params.get("params", {}))
        params["geo_input_file_name"] = self.points.pathname
        mixer.py_lines.append(f"parts.append(macro.mgeo(**{params!r}))")

    @classmethod
    def get_input_names(cls, step_config: "flavours.StepConfig", args: Kwargs) -> Set[str]:
        res = super().get_input_names(step_config, args)
        points = args.get("points")
        if points is not None:
            res.add(points)
        return res
