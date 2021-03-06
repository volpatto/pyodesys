# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function)

import copy
import os
import sys

from ..util import import_
from ._base import _NativeCodeBase, _NativeSysBase, _compile_kwargs

_config, get_include = import_('pycvodes', '_config', 'get_include')

if sys.version_info < (3, 6, 0):
    class ModuleNotFoundError(ImportError):
        pass


class NativeCvodeCode(_NativeCodeBase):
    wrapper_name = '_cvode_wrapper'

    try:
        _realtype = _config.env.get('REAL_TYPE', 'double')
        _indextype = _config.env.get('INDEX_TYPE', 'int')
    except ModuleNotFoundError:
        _realtype = 'double'
        _indextype = 'int'

    namespace = {
        'p_includes': ['"odesys_anyode_iterative.hpp"'],
        'p_support_recoverable_error': True,
        'p_jacobian_set_to_zero_by_solver': True,
        'p_baseclass': 'OdeSysIterativeBase',
        'p_realtype': _realtype,
        'p_indextype': _indextype
    }
    _support_roots = True

    def __init__(self, *args, **kwargs):
        self.compile_kwargs = copy.deepcopy(_compile_kwargs)
        self.compile_kwargs['define'] = ['PYCVODES_NO_KLU={}'.format(_config.env.get('NO_KLU', '0')),
                                         'PYCVODES_NO_LAPACK={}'.format(_config.env.get('NO_LAPACK', '0')),
                                         'ANYODE_NO_LAPACK={}'.format(_config.env.get('NO_LAPACK', '0'))]
        self.compile_kwargs['include_dirs'].append(get_include())
        self.compile_kwargs['libraries'].extend(_config.env['SUNDIALS_LIBS'].split(','))
        self.compile_kwargs['libraries'].extend(os.environ.get(
            'PYODESYS_LAPACK', [l for l in _config.env['LAPACK'].split(',') if l not in ('', '0')]))
        super(NativeCvodeCode, self).__init__(*args, **kwargs)


class NativeCvodeSys(_NativeSysBase):
    _NativeCode = NativeCvodeCode
    _native_name = 'cvode'

    def as_standalone(self, out_file=None, compile_kwargs=None):
        from pycompilation.compilation import src2obj, link
        from pycodeexport.util import render_mako_template_to
        compile_kwargs = compile_kwargs or {}
        impl_src = open([f for f in self._native._written_files if f.endswith('.cpp')][0], 'rt').read()
        f = render_mako_template_to(
            os.path.join(os.path.dirname(__file__), 'sources/standalone_template.cpp'),
            '%s.cpp' % out_file, {'p_odesys': self, 'p_odesys_impl': impl_src})
        kw = copy.deepcopy(self._native.compile_kwargs)
        kw.update(compile_kwargs)
        objf = src2obj(f, **kw)
        kw['libraries'].append('boost_program_options')
        return link([objf], out_file, **kw)
