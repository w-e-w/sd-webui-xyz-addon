from .utils import TrueTrue, no_type_cast, csv_string_to_list_strip, parse_range
from modules import extra_networks


def create_axes(xyz_grid):
    class ExtraNetworkWeight(xyz_grid.AxisOption):
        def __init__(self):
            self.label = '[Addon] Extra Network Weight'
            self.type = no_type_cast
            self.confirm = None
            self.cost = 0.0
            self.choices = None
            self.is_img2img = TrueTrue()

        @staticmethod
        def prepare(vals):
            network_name, sep, weights = vals.partition(':')
            if not sep:
                assert False, f'Network name not found "{vals}"'
            if not (valslist := parse_range(xyz_grid, csv_string_to_list_strip(weights))):
                assert False, f'No weights found for network "{network_name}"'
            network_name = network_name.strip()
            return list(map(lambda v: (network_name, v), valslist))

        @staticmethod
        def apply(p, x, xs):
            p.prompt = ExtraNetworkWeight.change_extra_network_weight(p.prompt, *x)

        @staticmethod
        def change_extra_network_weight(prompt, network_name, weight):
            for i in extra_networks.re_extra_net.finditer(prompt):
                e = i.group(2).split(':')
                if e[0] == network_name:
                    if len(e) > 1:
                        e[1] = weight
                        prompt = prompt[:i.start()] + f'<{i.group(1)}:{":".join(e)}>' + prompt[i.end():]
                    return prompt

        @staticmethod
        def format_value(p, opt, x):
            return ': '.join(x)

    return [ExtraNetworkWeight()]
