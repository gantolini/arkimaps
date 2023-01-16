# from __future__ import annotations
import asyncio
import contextlib
import io
import json
import logging
import os
import subprocess
import sys
from typing import (TYPE_CHECKING, Dict, Generator, Iterable, List, Optional,
                    Sequence)

from .orders import Output
from .pygen import PyGen

if TYPE_CHECKING:
    from .orders import Order

if TYPE_CHECKING:
    import tarfile

log = logging.getLogger("render")


@contextlib.contextmanager
def override_env(**kw):
    old = {}
    for k, v in kw.items():
        old[k] = os.environ.get(k)
        os.environ[k] = v
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                del os.environ[k]
            else:
                os.environ[k] = v


def groups(orders: Iterable["Order"], count: int) -> Generator[List["Order"], None, None]:
    """
    Given an iterable of orders, generate groups of maximum count items
    """
    group = []
    for order in orders:
        group.append(order)
        if len(group) == count:
            yield group
            group = []
    if group:
        yield group


class Renderer:
    def __init__(self, workdir: str, styles_dir: str = None):
        self.workdir = workdir
        if styles_dir is None:
            styles_dir = "/usr/share/magics/styles/ecmwf"
        self.styles_dir = styles_dir
        self.env_overrides = {
            # Tell magics where it should take its default styles from
            "MAGICS_STYLE_PATH": styles_dir,
            # Tell magics not to print noisy banners
            "MAGPLUS_QUIET": "1",
        }
        self.orders_by_name: Dict[str, Order] = {}

    @contextlib.contextmanager
    def override_env(self):
        with override_env(**self.env_overrides):
            yield

    def worker_init(self):
        for k, v in self.env_overrides.items():
            os.environ[k] = v

    def print_python_preamble(self, gen: PyGen):
        """
        Print the preamble of the Python rendering script
        """
        for k, v in self.env_overrides.items():
            gen.line(f"os.environ[{k!r}] = {v!r}")

        with gen.timed("import_magics") as sub:
            sub.line("from Magics import macro")

    def make_python_renderer(self, orders: Sequence['Order'], formatted: bool = False) -> str:
        """
        Render one order to a Python trace file.

        Return the name of the file written
        """
        with io.StringIO() as code:
            gen = PyGen(code)
            self.print_python_preamble(gen)
            for idx, order in enumerate(orders):
                name = f"order{idx}"
                self.orders_by_name[name] = order
                with gen.render_function(name) as sub:
                    order.print_python_function(name, sub)
            for idx, order in enumerate(orders):
                gen.line(f"order{idx}({self.workdir!r})")
            gen.line("print(json.dumps({'timings': timings, 'outputs': outputs}))")
            unformatted = code.getvalue()

        if formatted:
            try:
                from yapf.yapflib import yapf_api
                formatted, changed = yapf_api.FormatCode(unformatted)
                return formatted
            except ModuleNotFoundError:
                return unformatted
        else:
            return unformatted

    def render(self, orders: Iterable['Order'], tarout: "tarfile.TarFile") -> List["Order"]:
        """
        Render the given order list, adding results to the tar file.

        Return the list of orders that have been rendered
        """
        # TODO: hardcoded, make customizable
        orders_per_script = 16
        log.debug("%d orders to dispatch in groups of %d", len(orders), orders_per_script)

        queue: Dict[str, List["Order"]] = {}
        for group in groups(orders, orders_per_script):
            script_file = self.write_render_script(group, formatted=False)
            queue[script_file] = group

        if hasattr(asyncio, "run"):
            return asyncio.run(self.render_asyncio(queue, tarout))
        else:
            # Python 3.6
            loop = asyncio.get_event_loop()
            res = loop.run_until_complete(self.render_asyncio(queue, tarout))
            loop.close()
            return res

    async def render_asyncio(self, queue: Dict[str, List["Order"]], tarout: "tarfile.TarFile") -> List["Order"]:
        # TODO: hardcoded default to os.cpu_count, can be configurable
        max_tasks = os.cpu_count()
        pending = set()
        log.debug("%d render scripts to run on %d parallel tasks", len(queue), max_tasks)

        rendered: List["Order"] = []
        while queue or pending:
            # Polyfill for Python 3.6
            if hasattr(asyncio, "create_task"):
                create_task = asyncio.create_task
            else:
                loop = asyncio.get_event_loop()

                def create_task(*args, **kw):
                    return loop.create_task(*args)

            # Refill the queue
            while queue and len(pending) < max_tasks:
                script_file, orders = queue.popitem()
                pending.add(create_task(self.run_render_script(script_file, orders), name=script_file))

            # Execute the queue
            log.debug("Waiting for %d tasks", len(pending))
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            log.debug("%d tasks done, %d tasks pending", len(done), len(pending))

            # Notify results
            for task in done:
                # Python 3.6 compat
                if hasattr(task, "get_name"):
                    log.debug("%s: task done", task.get_name())
                try:
                    orders = task.result()
                except Exception as e:
                    log.warning("Task execution failed: %s", e, exc_info=e)
                    continue

                for order in orders:
                    for output in order.outputs:
                        log.info("Rendered %s to %s %s: %s", order, output.relpath)

                        # Move the generated image to the output tar
                        tarout.add(
                            os.path.join(self.workdir, output.relpath),
                            output.relpath)
                        os.unlink(output.relpath)

                    rendered.append(order)

        return rendered

    async def run_render_script(self, script_file: str, orders: List["Order"]) -> List["Order"]:
        proc = await asyncio.create_subprocess_exec(
                sys.executable, script_file, stdout=asyncio.subprocess.PIPE)

        stdout, stderr = await proc.communicate()
        render_info = json.loads(stdout)
        timings = render_info["timings"]
        outputs = [Output(*o) for o in render_info["outputs"]]
        for output in outputs:
            # Set render information in the order
            order = self.orders_by_name[output.name]
            order.outputs.append(output)
            order.render_time_ns += timings[output.name]

        return orders

    def render_one(self, order: 'Order') -> Optional['Order']:
        script_file = self.write_render_script([order], formatted=True)

        # Run the render script
        res = subprocess.run([sys.executable, script_file], check=True, stdout=subprocess.PIPE)
        render_info = json.loads(res.stdout)
        timings = render_info["timings"]
        outputs = [Output(*o) for o in render_info["outputs"]]
        # Set render information in the order
        output = outputs[0]
        order = self.orders_by_name[output.name]
        order.outputs.append(output)
        order.render_time_ns += timings[output.name]
        return order

    def write_render_script(self, orders: Sequence['Order'], formatted: bool = False) -> str:
        python_code = self.make_python_renderer(orders, formatted=formatted)

        # Write the python renderer code
        script_file: Optional[str] = None
        for order in orders:
            os.makedirs(os.path.dirname(order.render_script), exist_ok=True)

            # Remove the destination file to break possibly existing links from
            # an old workdir
            try:
                os.unlink(order.render_script)
            except FileNotFoundError:
                pass

            if script_file is None:
                script_file = order.render_script
                with open(script_file, "wt") as fd:
                    fd.write(python_code)
            else:
                os.link(script_file, order.render_script)

        return script_file
