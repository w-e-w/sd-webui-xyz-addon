from modules import scripts, extra_networks, shared
from io import StringIO
import numpy as np
import itertools
import json
import csv
xyz_grid = [x for x in scripts.scripts_data if x.script_class.__module__ == "xyz_grid.py"][0].module


def csv_string_to_list_strip(csv_str, delimiter=',', quotechar='"'):
    """parse a csv string to a list of striped str"""
    return list(map(str.strip, itertools.chain.from_iterable(csv.reader(StringIO(csv_str), delimiter=delimiter, quotechar=quotechar))))


def cast_str_list_to_type(values: list, cast_func):
    return list(map(cast_func, values))


def no_type_cast(x):
    return x


def format_placeholder(p, opt, x):
    return str(x[1])


def prepare_sr_placeholder(vals):
    valslist = xyz_grid.csv_string_to_list_strip(vals)
    placeholder = valslist[0]
    output = []
    for v in valslist[1:]:
        output.append((placeholder, v))
    return output


def apply_replace_placeholder(p, x, xs, axis_name='[Addon]'):
    """Similar functionality to the built-in Prompt S/R, but the first item will be replaced with <blank>"""
    placeholder, replacement = x
    if placeholder not in p.prompt and placeholder not in p.negative_prompt:
        raise RuntimeError(f'{axis_name}: {placeholder}" was not found in prompt or negative prompt.')
    p.prompt = p.prompt.replace(placeholder, replacement)
    p.negative_prompt = p.negative_prompt.replace(placeholder, replacement)


def combinatorics(vals, function):
    placeholder, *replacement_list = csv_string_to_list_strip(vals)
    placeholder, _, length = placeholder.partition(':')
    r1, r2 = None, None
    if length := length.strip():
        r1, _, r2 = length.partition('-')
        if r2 := r2.strip():
            r2 = int(r2)
        r1 = int(r1.strip())

    if not r1:
        r1 = 1
        r2 = len(replacement_list)
    if not r2:
        r2 = r1

    if r1 > r2:
        r1, r2 = r2, r1

    valslist = []
    for r in range(r1, r2+1):
        for c in function(replacement_list, r):
            valslist.append((placeholder, ', '.join(c)))
    return valslist


def combinations(s):
    return combinatorics(s, itertools.combinations)


def permutations(s):
    return combinatorics(s, itertools.permutations)


def get_axis(name, axis_type=None):
    """Find an axis of axis_type by name, case-sensitive -> case-insensitive"""
    for option in xyz_grid.axis_options:
        if option.label.lower() == name:
            if axis_type is None or ((option_axis_type := getattr(option, 'is_img2img', None)) is None or axis_type == option_axis_type):
                return option
    for option in xyz_grid.axis_options:
        if option.label.lower() == name.lower():
            if axis_type is None or ((option_axis_type := getattr(option, 'is_img2img', None)) is None or axis_type == option_axis_type):
                return option
    raise RuntimeError(f'[Addon] Multi axis: could not find axis named "{name}"')


step_changer = [get_axis(n) for n in ['Steps', 'Hires steps']]


def parse_range(valslist, int_mode=True):
    """Parse range string to range list, extracted from xyz_grid.Script.run.process_axis()
    """
    valslist_ext = []
    if int_mode:
        for val in valslist:
            if val.strip() == '':
                continue
            m = xyz_grid.re_range.fullmatch(val)
            mc = xyz_grid.re_range_count.fullmatch(val)
            if m is not None:
                start = int(m.group(1))
                end = int(m.group(2)) + 1
                step = int(m.group(3)) if m.group(3) is not None else 1

                valslist_ext += list(range(start, end, step))
            elif mc is not None:
                start = int(mc.group(1))
                end = int(mc.group(2))
                num = int(mc.group(3)) if mc.group(3) is not None else 1

                valslist_ext += [int(x) for x in np.linspace(start=start, stop=end, num=num).tolist()]
            else:
                valslist_ext.append(val)
    else:
        for val in valslist:
            if val.strip() == '':
                continue
            m = xyz_grid.re_range_float.fullmatch(val)
            mc = xyz_grid.re_range_count_float.fullmatch(val)
            if m is not None:
                start = float(m.group(1))
                end = float(m.group(2))
                step = float(m.group(3)) if m.group(3) is not None else 1

                valslist_ext += np.arange(start, end + step, step).tolist()
            elif mc is not None:
                start = float(mc.group(1))
                end = float(mc.group(2))
                num = int(mc.group(3)) if mc.group(3) is not None else 1

                valslist_ext += np.linspace(start=start, stop=end, num=num).tolist()
            else:
                valslist_ext.append(val)
    return valslist_ext


class MultiAxis(xyz_grid.AxisOption):
    label_name = '[Addon] Multi axis'

    def __init__(self, is_img2img):
        super().__init__(MultiAxis.label_name, no_type_cast, self.apply, self.format, self.confirm, prepare=self.prepare)
        self.is_img2img = is_img2img
        self.update_total_step = 0

    def prepare(self, vals):
        self.cost = 0.0  # reset axis cost
        axes, valuse, multiaxis_values = [], [], []

        # pares vars
        for param in csv_string_to_list_strip(vals, delimiter='|', quotechar="'"):
            param = param.strip()
            axis_name, _, value = param.partition(':')
            axis = get_axis(axis_name.strip())
            axes.append(axis)
            self.cost += axis.cost  # sum cost of individual axis
            valuse.append(self.process_multi_axis(axis, value.strip()))

        # combination products
        for c in itertools.combinations(valuse, len(valuse)):
            for res in itertools.product(*c):
                xss = MultiAxis.MultiAxisValue()
                for axis, value in zip(axes, res):
                    xss.append((axis, [value]))
                multiaxis_values.append(xss)

        # hack for changing the step total count
        for step_changer_axis in step_changer:
            if step_changer_axis in axes:
                self.label = step_changer_axis.label
                break

        return multiaxis_values

    @staticmethod
    def apply(p, x, xs):
        for index, (axis, xi) in enumerate(x):
            xsi = [x[index][1][0] for x in xs]
            axis.apply(p, xi[0], xsi)

    @staticmethod
    def process_multi_axis(opt, vals):
        """A modified version of xyz_grid.Script.run.process_axis()"""
        if opt.label == 'Nothing':
            return [0]

        #  no not CSV mode checks as multi_axis input is always in CSV
        if opt.prepare is not None:
            valslist = opt.prepare(vals)
        else:
            valslist = xyz_grid.csv_string_to_list_strip(vals)

        if opt.type in (int, float):
            valslist = parse_range(valslist, isinstance(opt.type, int))
        elif opt.type == xyz_grid.str_permutations:
            valslist = list(itertools.permutations(valslist))

        valslist = [opt.type(x) for x in valslist]

        # can't perform opt.confirm as we don't have access to p, perform it in self.confirm

        return valslist

    def confirm(self, p, valslist):
        for i, multi_axis in enumerate(valslist):
            for axis, value in multi_axis:
                if axis.confirm:
                    axis.confirm(p, value)

    def format(self, p, opt, x):
        lables = []
        for axis, val in x:
            lables.append(axis.format_value(p, axis, val[0]))
        self.label = MultiAxis.label_name  # restore hack for changing the step total count
        return ' | '.join(lables)

    class MultiAxisValue(list):
        """A hack for changing the step total count by modifying the sum() function"""
        def __new__(cls, *args):
            return super().__new__(cls, args)

        def __radd__(self, other):
            val = 0
            for axis, value in self:
                if axis in step_changer:
                    val += int(value[0])
            return other + val


class ExtraNetworkWeight(xyz_grid.AxisOption):
    def __init__(self, is_img2img):
        super().__init__('[Addon] Extra Network Weight', no_type_cast, self.apply, self.format, prepare=self.prepare)
        self.is_img2img = is_img2img
        self.network_name = None

    def prepare(self, vals):
        network_name, sep, weights = vals.partition(':')
        if not sep:
            assert False, f'Network name not found "{vals}"'
        if not (valslist := parse_range(xyz_grid.csv_string_to_list_strip(weights), False)):
            assert False, f'No weights found for network "{self.network_name}"'
        self.network_name = network_name.strip()
        return [(self.network_name, str(weight)) for weight in valslist]

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
    def format(p, opt, x):
        return ': '.join(x)


class OverrideSetting(xyz_grid.AxisOption):
    def __init__(self, is_img2img, int_mode):
        label = '[Addon] Override Setting (int)' if int_mode else '[Addon] Override Setting'
        super().__init__(label, no_type_cast, self.apply, self.format, prepare=self.prepare)
        self.is_img2img = is_img2img
        self.int_mode = int_mode
        self.setting_key = None

    def prepare(self, vals):
        setting_key, sep, values = vals.partition(':')
        if not sep:
            assert False, f'No key found in: {vals}'
        self.setting_key = setting_key.strip()
        try:
            setting_value = getattr(shared.opts, self.setting_key)
        except Exception:
            assert False, f'Invalid setting key: {self.setting_key}'

        valslist = csv_string_to_list_strip(values)
        if isinstance(setting_value, (float, int)):
            valslist = parse_range(valslist, self.int_mode)
            self.type = no_type_cast
        elif isinstance(setting_value, (bool, list, dict)):
            self.type = json.loads
        else:
            self.type = no_type_cast

        return [(self.setting_key, value) for value in valslist]

    @staticmethod
    def apply(p, x, xs):
        key, value = x
        p.override_settings[key] = value

    @staticmethod
    def format(p, opt, x):
        key, value = x
        return f'{key}: {str(value)}'


axis_sr_placeholder_name = '[Addon] Prompt S/R Placeholder'
axis_sr_placeholder = xyz_grid.AxisOption(
    axis_sr_placeholder_name,
    no_type_cast,
    lambda *arg, **kwargs: apply_replace_placeholder(*arg, **kwargs, axis_name=axis_sr_placeholder_name),
    format_placeholder,
    prepare=prepare_sr_placeholder)
axis_combination_name = '[Addon] Prompt S/R Combinations'
axis_combination = xyz_grid.AxisOption(
    axis_combination_name,
    no_type_cast,
    lambda *arg, **kwargs: apply_replace_placeholder(*arg, **kwargs, axis_name=axis_combination_name),
    format_placeholder,
    prepare=lambda s: combinatorics(s, itertools.combinations)
)
axis_permutations_name = '[Addon] Prompt S/R Permutations'
axis_permutation = xyz_grid.AxisOption(
    axis_permutations_name,
    no_type_cast,
    lambda *arg, **kwargs: apply_replace_placeholder(*arg, **kwargs, axis_name=axis_permutations_name),
    format_placeholder,
    prepare=lambda s: combinatorics(s, itertools.permutations)
)


xyz_grid.axis_options.extend([
    axis_sr_placeholder,
    axis_combination,
    axis_permutation,
    ExtraNetworkWeight(False),
    ExtraNetworkWeight(True),
    MultiAxis(False),
    MultiAxis(True),
    OverrideSetting(False, False),
    OverrideSetting(False, True),
    OverrideSetting(True, False),
    OverrideSetting(True, True),
])
