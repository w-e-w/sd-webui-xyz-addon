from modules import scripts
from io import StringIO
import numpy as np
import itertools
import csv
xyz_grid = [x for x in scripts.scripts_data if x.script_class.__module__ == "xyz_grid.py"][0].module


def csv_string_to_list_strip(csv_str, delimiter=',', quotechar='"'):
    """parse a csv string to a list of striped str"""
    return list(map(str.strip, itertools.chain.from_iterable(csv.reader(StringIO(csv_str), delimiter=delimiter, quotechar=quotechar))))


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


class MultiAxis(xyz_grid.AxisOption):
    label_name = '[Addon] Multi axis'

    def __init__(self, is_img2img):
        super().__init__(MultiAxis.label_name, self.type, self.apply_multi_axis, self.format_multi_axis, prepare=self.prepare_multi_axis)
        self.is_img2img = is_img2img
        self.update_total_step = 0

    def prepare_multi_axis(self, vals):
        self.cost = 0.0  # reset axis cost
        axes, valuse, multiaxis_values = [], [], []

        # pares vars
        for param in csv_string_to_list_strip(vals, delimiter='|', quotechar="'"):
            param = param.strip()
            axis_name, _, value = param.partition(':')
            axis = get_axis(axis_name.strip())
            axes.append(axis)
            self.cost += axis.cost  # sum cost of individual axis
            valuse.append(self.multi_axis_process_axis(axis, value.strip()))

        # combination products
        for c in itertools.combinations(valuse, len(valuse)):
            for res in itertools.product(*c):
                xss = MultiAxis.MultiAxisValue()
                for axis, value in zip(axes, res):
                    xss.append((axis, value))
                multiaxis_values.append(xss)

        # hack for changing the step total count
        for step_changer_axis in step_changer:
            if step_changer_axis in axes:
                self.label = step_changer_axis.label
                break

        return multiaxis_values

    @staticmethod
    def apply_multi_axis(p, x, xs):
        for index, (axis, xi) in enumerate(x):
            xsi = [x[index][1] for x in xs]
            axis.apply(p, xi, xsi)

    @staticmethod
    def multi_axis_process_axis(opt, vals):
        """A modified version of xyz_grid.Script.run.process_axis()"""
        if opt.label == 'Nothing':
            return [0]

        #  no not CSV mode checks as multi_axis input is always in CSV
        if opt.prepare is not None:
            valslist = opt.prepare(vals)
        else:
            valslist = xyz_grid.csv_string_to_list_strip(vals)

        if opt.type == int:
            valslist_ext = []

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

            valslist = valslist_ext
        elif opt.type == float:
            valslist_ext = []

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

            valslist = valslist_ext
        elif opt.type == xyz_grid.str_permutations:
            valslist = list(itertools.permutations(valslist))

        valslist = [opt.type(x) for x in valslist]

        # can't perform opt.confirm as we don't have access to p here

        return valslist

    def format_multi_axis(self, p, opt, x):
        lables = []
        for axis, val in x:
            lables.append(f'{axis.label}: {val}')
        self.label = MultiAxis.label_name  # restore hack for changing the step total count
        return ' | '.join(lables)

    @staticmethod
    def type(x):
        return x

    class MultiAxisValue(list):
        """A hack for changing the step total count by modifying the sum() function"""
        def __new__(cls, *args):
            return super().__new__(cls, args)

        def __radd__(self, other):
            val = 0
            for axis, value in self:
                if axis in step_changer:
                    val += int(value)
            return other + val


axis_sr_placeholder_name = '[Addon] Prompt S/R Placeholder'
axis_sr_placeholder = xyz_grid.AxisOption(axis_sr_placeholder_name, no_type_cast, lambda *arg, **kwargs: apply_replace_placeholder(*arg, **kwargs, axis_name=axis_sr_placeholder_name), format_placeholder, prepare=prepare_sr_placeholder)
axis_combination_name = '[Addon] Prompt S/R Combinations'
axis_combination = xyz_grid.AxisOption(axis_combination_name, no_type_cast, lambda *arg, **kwargs: apply_replace_placeholder(*arg, **kwargs, axis_name=axis_combination_name), format_placeholder, prepare=lambda s: combinatorics(s, itertools.combinations))
axis_permutations_name = '[Addon] Prompt S/R Permutations'
axis_permutation = xyz_grid.AxisOption(axis_permutations_name, no_type_cast, lambda *arg, **kwargs: apply_replace_placeholder(*arg, **kwargs, axis_name=axis_permutations_name), format_placeholder, prepare=lambda s: combinatorics(s, itertools.permutations))


xyz_grid.axis_options.extend([
    axis_sr_placeholder,
    axis_combination,
    axis_permutation,
    MultiAxis(False),
    MultiAxis(True),
])
