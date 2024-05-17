from . import extra_network_weight, prompt_sr, multi_axis, override_setting
from modules import scripts


def add_axes():
    xyz_grid = [x for x in scripts.scripts_data if x.script_class.__module__ == "xyz_grid.py"][0].module
    xyz_grid.axis_options.extend(extra_network_weight.create_axes(xyz_grid))
    xyz_grid.axis_options.extend(multi_axis.create_axes(xyz_grid))
    xyz_grid.axis_options.extend(prompt_sr.create_axes(xyz_grid))
    xyz_grid.axis_options.extend(override_setting.create_axes(xyz_grid))
