from .utils import TrueTrue, no_type_cast, csv_string_to_list_strip, parse_range
from modules import shared
import json


def create_axes(xyz_grid):
    class OverrideSetting(xyz_grid.AxisOption):
        def __init__(self, int_mode):
            self.label = '[Addon] Override Setting (int)' if int_mode else '[Addon] Override Setting'
            self.type = no_type_cast
            self.confirm = None
            self.cost = 0.0
            self.choices = None
            self.is_img2img = TrueTrue()
            self.int_mode = int_mode

        def prepare(self, vals):
            setting_key, sep, values = vals.partition(':')
            if not sep:
                assert False, f'No key found in: {vals}'
            setting_key = setting_key.strip()
            try:
                setting_value = getattr(shared.opts, setting_key)
            except Exception:
                assert False, f'Invalid setting key: {setting_key}'

            valslist = csv_string_to_list_strip(values)
            if isinstance(setting_value, (bool, list, dict)):
                valslist = map(json.dumps, valslist)
            elif isinstance(setting_value, (float, int)):
                valslist = map(int if self.int_mode else float, parse_range(xyz_grid, valslist, self.int_mode))

            return list(map(lambda v: (setting_key, v), valslist))

        @staticmethod
        def apply(p, x, xs):
            key, value = x
            p.override_settings[key] = value

        @staticmethod
        def format_value(p, opt, x):
            key, value = x
            return f'{key}: {str(value)}'

    return [
        OverrideSetting(False),
        OverrideSetting(True),
    ]
