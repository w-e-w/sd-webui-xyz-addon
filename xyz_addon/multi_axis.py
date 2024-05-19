from .utils import no_type_cast, csv_string_to_list_strip, parse_range
import itertools


class Label(str):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.extra = set()

    def __eq__(self, other):
        return other in self.extra or super().__eq__(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(super().__str__())

    def add_extra(self, extra):
        self.extra.add(extra)

    def clear_extra(self):
        self.extra.clear()


def is_axis_type(axis, img2img):
    return img2img is None or ((option_axis_type := getattr(axis, 'is_img2img', None)) is None or img2img == option_axis_type)


def create_axes(xyz_grid):
    def get_axis(name, axis_type=None):
        """Find an axis of axis_type by name, case-sensitive -> case-insensitive"""
        for option in xyz_grid.axis_options:
            if is_axis_type(option, axis_type) and str(option.label) == name:
                return option
        name_lower = name.lower()
        for option in xyz_grid.axis_options:
            if is_axis_type(option, axis_type) and option.label.lower() == name_lower:
                return option
        raise RuntimeError(f'[Addon] Multi axis: could not find axis named "{name}"')

    step_changer = [get_axis(n) for n in ['Steps', 'Hires steps']]

    class MultiAxisValue(list):
        """A hack for changing the step total count by modifying the sum() function"""

        def __new__(cls, *args):
            return super().__new__(cls, args)

        def __radd__(self, other):
            return other + sum(sum(value) if isinstance(axis, MultiAxis) else int(value[0] if axis in step_changer else 0) for axis, value in self)

    class MultiAxis(xyz_grid.AxisOption):
        def __init__(self, is_img2img):
            self.label = Label('[Addon] Multi axis')
            self.type = no_type_cast
            self.cost = 0.0
            self.choices = None
            self.is_img2img = is_img2img

        def prepare(self, vals):
            self.cost = 0.0  # reset axis cost
            axes, valuse = [], []

            # pares vars
            for param in csv_string_to_list_strip(vals, delimiter='|', quotechar="'"):
                param = param.strip()
                axis_name, _, value = param.partition(':')
                axis = get_axis(axis_name.strip(), self.is_img2img)
                axes.append(axis)
                self.cost += axis.cost  # sum cost of individual axis
                valuse.append(self.process_multi_axis(axis, value.strip()))

            # hack for changing the step total count
            for step_changer_axis in step_changer:
                if step_changer_axis in axes:
                    self.label.add_extra(step_changer_axis.label)
                    break

            # combination products
            return list(map(lambda r: MultiAxisValue(map((lambda x: tuple([x[0], [x[1]]])), zip(axes, r))), itertools.product(*valuse)))

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
                valslist = csv_string_to_list_strip(vals)

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
            self.label.clear_extra()  # restore hack for changing the step total count
            return ' | '.join(lables)

    return [MultiAxis(False), MultiAxis(True)]
