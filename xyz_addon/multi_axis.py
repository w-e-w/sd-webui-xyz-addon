from .utils import no_type_cast, csv_string_to_list_strip, parse_range, TrueTrue
import itertools


def create_axes(xyz_grid):
    def get_axis(name, axis_type=None):
        """Find an axis of axis_type by name, case-sensitive -> case-insensitive"""
        for option in xyz_grid.axis_options:
            print(option.label)
            if option.label == name:
                if axis_type is None or ((option_axis_type := getattr(option, 'is_img2img', None)) is None or axis_type == option_axis_type):
                    return option
        name_lower = name.lower()
        for option in xyz_grid.axis_options:
            if option.label.lower() == name_lower:
                if axis_type is None or ((option_axis_type := getattr(option, 'is_img2img', None)) is None or axis_type == option_axis_type):
                    return option
        raise RuntimeError(f'[Addon] Multi axis: could not find axis named "{name}"')

    step_changer = [get_axis(n) for n in ['Steps', 'Hires steps']]

    class MultiAxis(xyz_grid.AxisOption):
        def __init__(self):
            self.label = '[Addon] Multi axis'
            self.type = no_type_cast
            self.cost = 0.0
            self.choices = None
            self.is_img2img = TrueTrue()

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

            if opt.type == int:
                valslist = parse_range(xyz_grid, valslist, True)
            elif opt.type == float:
                valslist = parse_range(xyz_grid, valslist)
            elif opt.type == xyz_grid.str_permutations:
                valslist = list(itertools.permutations(valslist))

            valslist = [opt.type(x) for x in valslist]

            # can't perform opt.confirm as we don't have access to p, perform it in self.confirm

            return valslist

        @staticmethod
        def confirm(p, valslist):
            for i, multi_axis in enumerate(valslist):
                for axis, value in multi_axis:
                    if axis.confirm:
                        axis.confirm(p, value)

        def format_value(self, p, opt, x):
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

    return [MultiAxis()]
