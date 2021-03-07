# from __future__ import annotations
from arkimapslib.unittest import add_recipe_test_cases


class MCCMixin:
    def test_dispatch(self):
        with self.kitchen_class() as kitchen:
            self.fill_pantry(kitchen)

            orders = self.make_orders(kitchen)
            self.assertEqual(len(orders), 1)

            self.assertRenders(kitchen, orders[0])

            mgrib_args = self.get_debug_trace(orders[0], "add_grib")
            expected_mgrib_args = {
                "cosmo": {'grib_automatic_scaling': False, 'grib_scaling_factor': 0.08},
                "ifs": {'grib_automatic_scaling': False, 'grib_scaling_factor': 8},
            }
            self.assertEqual(mgrib_args, expected_mgrib_args[self.model_name])


add_recipe_test_cases(__name__, "mcc")
