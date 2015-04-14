# vim:fileencoding=utf-8:noet

import sys
import codecs

try:
	import vim
except ImportError:
	vim = {}

if hasattr(vim, 'bindeval'):
	def vim_get_func(f, rettype=None):
		'''Return a vim function binding.'''
		try:
			func = vim.bindeval('function("' + f + '")')
			if sys.version_info >= (3,) and rettype is str:
				return (lambda *args, **kwargs: func(*args, **kwargs).decode('utf-8', errors='replace'))
			return func
		except vim.error:
			return None
else:
	import json

	class VimFunc(object):
		'''Evaluate a vim function using vim.eval().

		This is a fallback class for older vim versions.
		'''
		__slots__ = ('f', 'rettype')

		def __init__(self, f, rettype=None):
			self.f = f
			self.rettype = rettype

		def __call__(self, *args):
			r = vim.eval(self.f + '(' + json.dumps(args)[1:-1] + ')')
			if self.rettype:
				return self.rettype(r)
			return r

	vim_get_func = VimFunc


# It may crash on some old vim versions and I do not remember in which patch 
# I fixed this crash.
if hasattr(vim, 'vars') and vim.vvars['version'] > 703:
	_vim_to_python_types = {
		vim.Dictionary: lambda value: dict(((key, _vim_to_python(value[key])) for key in value.keys())),
		vim.List: lambda value: [_vim_to_python(item) for item in value],
		vim.Function: lambda _: None,
	}

	_id = lambda value: value

	def _vim_to_python(value):
		return _vim_to_python_types.get(type(value), _id)(value)

	def vim_getvar(varname):
		return _vim_to_python(vim.vars[str(varname)])
else:
	_vim_exists = vim_get_func('exists', rettype=int)

	def vim_getvar(varname):  # NOQA
		varname = 'g:' + varname
		if _vim_exists(varname):
			return vim.eval(varname)
		else:
			raise KeyError(varname)

if hasattr(vim, 'vars') and vim.vvars['version'] > 703:
	def bufvar_exists(buffer, varname):
		buffer = buffer or vim.current.buffer
		return varname in buffer.vars
else:
	def bufvar_exists(buffer, varname):  # NOQA
		if not buffer or buffer.number == vim.current.buffer.number:
			return vim.eval('exists("b:{0}")'.format(varname))
		else:
			return vim.eval('has_key(getbufvar({0}, ""), {1})'
							.format(buffer.number, varname))

if hasattr(vim, 'options'):
	def vim_getbufoption(info, option):
		return info['buffer'].options[option]
else:
	def vim_getbufoption(info, option):  # NOQA
		return getbufvar(info['bufnr'], '&' + option)


if sys.version_info < (3,) or not hasattr(vim, 'bindeval'):
	getbufvar = vim_get_func('getbufvar')
else:
	_getbufvar = vim_get_func('getbufvar')

	def getbufvar(*args):
		r = _getbufvar(*args)
		if type(r) is bytes:
			return r.decode('utf-8')
		return r


class VimEnviron(object):
	@staticmethod
	def __getitem__(key):
		return vim.eval('$' + key)

	@staticmethod
	def get(key, default=None):
		return vim.eval('$' + key) or default

	@staticmethod
	def __setitem__(key, value):
		return vim.command('let $' + key + '="'
					+ value.replace('"', '\\"').replace('\\', '\\\\').replace('\n', '\\n').replace('\0', '')
					+ '"')


if sys.version_info < (3,):
	def buffer_name(buf):
		return buf.name
else:
	vim_bufname = vim_get_func('bufname')
	def buffer_name(buf):  # NOQA
		try:
			name = buf.name
		except UnicodeDecodeError:
			return vim_bufname(buf.number)
		else:
			return name.encode('utf-8') if name else None


vim_strtrans = vim_get_func('strtrans')


def powerline_vim_strtrans_error(e):
	if not isinstance(e, UnicodeDecodeError):
		raise NotImplementedError
	# Assuming &encoding is utf-8 strtrans should not return anything but ASCII 
	# under current circumstances
	text = vim_strtrans(e.object[e.start:e.end]).decode()
	return (text, e.end)


codecs.register_error('powerline_vim_strtrans_error', powerline_vim_strtrans_error)


environ = VimEnviron()
