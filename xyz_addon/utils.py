from io import StringIO
import numpy as np
import itertools
import csv


class TrueTrue:
    def __eq__(self, other):
        return True


def no_type_cast(x):
    return x


def csv_string_to_list_strip(csv_str, delimiter=',', quotechar='"'):
    """parse a csv string to a list of striped str"""
    return list(map(str.strip, itertools.chain.from_iterable(csv.reader(StringIO(csv_str), delimiter=delimiter, quotechar=quotechar, skipinitialspace=True))))


def parse_range(xyz_grid, valslist, int_mode=False):
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



