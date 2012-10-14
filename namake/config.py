import imp
import os
import errno

class ConfigAttribute(object):
    """Makes an attribute forward to the config"""

    def __init__(self, name, get_converter=None):
        self.__name__ = name
        self.get_converter = get_converter

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        rv = obj.config[self.__name__]
        if self.get_converter is not None:
            rv = self.get_converter(rv)
        return rv

    def __set__(self, obj, value):
        obj.config[self.__name__] = value


class Config(dict):
    """Works exactly like a dict but provides ways to fill it from files
    or special dictionaries.  There are two common patterns to populate the
    config.

    Either you can fill the config from a config file::

        app.config.from_pyfile('yourconfig.cfg')

    Or alternatively you can define the configuration options in the
    module that calls :meth:`from_object` or provide an import path to
    a module that should be loaded.  It is also possible to tell it to
    use the same module and with that provide the configuration values
    just before the call::

        DEBUG = True
        SECRET_KEY = 'development key'
        app.config.from_object(__name__)

    In both cases (loading from any Python file or loading from modules),
    only uppercase keys are added to the config.  This makes it possible to use
    lowercase values in the config file for temporary values that are not added
    to the config or to define the config keys in the same file that implements
    the application.

    Probably the most interesting way to load configurations is from an
    environment variable pointing to a file::

        app.config.from_envvar('YOURAPPLICATION_SETTINGS')

    In this case before launching the application you have to set this
    environment variable to the file you want to use.  On Linux and OS X
    use the export statement::

        export YOURAPPLICATION_SETTINGS='/path/to/config/file'

    On windows use `set` instead.

    :param defaults: an optional dictionary of default values
    """

    def __init__(self, defaults=None):
        dict.__init__(self, defaults or {})

    def from_envvar(self, variable_name, silent=False):
        """Loads a configuration from an environment variable pointing to
        a configuration file.  This is basically just a shortcut with nicer
        error messages for this line of code::

            app.config.from_pyfile(os.environ['YOURAPPLICATION_SETTINGS'])

        :param variable_name: name of the environment variable
        :param silent: set to `True` if you want silent failure for missing
                       files.
        :return: bool. `True` if able to load config, `False` otherwise.
        """
        rv = os.environ.get(variable_name)
        if not rv:
            if silent:
                return False
            raise RuntimeError('The environment variable %r is not set '
                               'and as such configuration could not be '
                               'loaded.  Set this variable and make it '
                               'point to a configuration file' %
                               variable_name)
        return self.from_pyfile(rv, silent=silent)

    def from_pyfile(self, filename, silent=False):
        """Updates the values in the config from a Python file.  This function
        behaves as if the file was imported as module with the
        :meth:`from_object` function.

        :param filename: the absolute filename of the config.
        :param silent: set to `True` if you want silent failure for missing
                       files.

        .. versionadded:: 0.7
           `silent` parameter.
        """
        d = imp.new_module('config')
        d.__file__ = filename
        try:
            execfile(filename, d.__dict__)
        except IOError, e:
            if silent and e.errno in (errno.ENOENT, errno.EISDIR):
                return False
            e.strerror = 'Unable to load configuration file (%s)' % e.strerror
            raise
        self.from_object(d)
        return True

    def from_object(self, obj):
        """Updates the values from the given object.  An object can be of one
        of the following two types:

        -   a string: in this case the object with that name will be imported
        -   an actual object reference: that object is used directly

        Objects are usually either modules or classes.

        Just the uppercase variables in that object are stored in the config.
        Example usage::

            app.config.from_object('yourapplication.default_config')
            from yourapplication import default_config
            app.config.from_object(default_config)

        You should not use this function to load the actual configuration but
        rather configuration defaults.  The actual config should be loaded
        with :meth:`from_pyfile` and ideally from a location not within the
        package because the package might be installed system wide.

        :param obj: an import name or object
        """
        if isinstance(obj, basestring):
            from .utils import import_string
            obj = import_string(obj)
        for key in dir(obj):
            if key.isupper():
                self[key] = getattr(obj, key)

    def from_inifile(self, filename, silent=False):
        """
        Reads settings from an ini file.
        Settings are added to the configuration dictionary in
        the following form. All section and option keys are
        changed to uppercase.

        <SECTION_NAME>_<OPTION_NAME>

        However, all options in the special section "namake"
        are added to the dictionary without the section name 
        as follows.

        <OPTION_NAME>
        """
        from ConfigParser import SafeConfigParser
        config = SafeConfigParser()
        with open(filename, 'rb') as cfgfile:
            config.readfp(cfgfile)
        for section in config.sections():
            for option in config.options(section):
                # Try to coerce the value from the ini file into
                # native python objects automatically.
                for method in ['getint', 'getfloat', 'getboolean', 'get']:
                    try:
                        value = getattr(config, method)(section, option)
                        if section.upper() == 'NAMAKE':
                            self[option.upper()] = value
                        else:
                            self[section.upper() + '_' + option.upper()] = value
                        break
                    except ValueError:
                        pass

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dict.__repr__(self))
