from modules import shared


def add_settings():
    section = ('xyz_addon', 'XYZ Addon')
    shared.opts.add_option('xyz_addon_restore_placeholder', shared.OptionInfo(True, 'Restore placeholder grid infotext', section=section).info('disabled if conflict with other prompt operations'))
