# Copyright (C) 2025 fontconfig Authors
# SPDX-License-Identifier: HPND

from pathlib import Path
from tempfile import TemporaryDirectory, NamedTemporaryFile
from typing import Iterator
import os
import shutil
import subprocess


class FcTest:

    def __init__(self):
        self._env = os.environ.copy()
        self._fontdir = TemporaryDirectory(prefix='fontconfig.',
                                           suffix='.fontdir')
        self._cachedir = TemporaryDirectory(prefix='fontconfig.',
                                            suffix='.cachedir')
        self._conffile = NamedTemporaryFile(prefix='fontconfig.',
                                            suffix='.conf',
                                            mode='w',
                                            delete_on_close=False)
        self._builddir = self._env.get('builddir', 'build')
        self._srcdir = self._env.get('srcdir', '.')
        exeext = self._env.get('EXEEXT', '')
        self._exewrapper = self._env.get('EXEWRAPPER', None)
        self._fccache = Path(self.builddir) / 'fc-cache' / ('fc-cache' + exeext)
        if not self._fccache.exists():
            raise RuntimeError('No fc-cache binary. builddir might be wrong:'
                               f' {self._fccache}')
        self._fccat = Path(self.builddir) / 'fc-cat' / ('fc-cat' + exeext)
        if not self._fccat.exists():
            raise RuntimeError('No fc-cat binary. builddir might be wrong:'
                               f' {self._fccat}')
        self._fclist = Path(self.builddir) / 'fc-list' / ('fc-list' + exeext)
        if not self._fclist.exists():
            raise RuntimeError('No fc-list binary. builddir might be wrong:'
                               f' {self._fclist}')
        self._fcmatch = Path(self.builddir) / 'fc-match' / ('fc-match' + exeext)
        if not self._fcmatch.exists():
            raise RuntimeError('No fc-match binary. builddir might be wrong:'
                               f' {self._fcmatch}')
        self._fcpattern = Path(self.builddir) / 'fc-pattern' / ('fc-pattern' + exeext)
        if not self._fcpattern.exists():
            raise RuntimeError('No fc-pattern binary. builddir might be wrong:'
                               f' {self._fcpattern}')
        self._fcquery = Path(self.builddir) / 'fc-query' / ('fc-query' + exeext)
        if not self._fcquery.exists():
            raise RuntimeError('No fc-query binary. builddir might be wrong:'
                               f' {self._fcquery}')
        self._fcscan = Path(self.builddir) / 'fc-scan' / ('fc-scan' + exeext)
        if not self._fcscan.exists():
            raise RuntimeError('No fc-scan binary. builddir might be wrong:'
                               f' {self._fcscan}')
        self._fcvalidate = Path(self.builddir) / 'fc-validate' / ('fc-validate' + exeext)
        if not self._fcvalidate.exists():
            raise RuntimeError('No fc-validate binary. builddir might be wrong:'
                               f' {self._fcvalidate}')
        self._extra = ''
        self.__conf_templ = '''
        <fontconfig>
          {extra}
          <dir>{fontdir}</dir>
          <cachedir>{cachedir}</cachedir>
        </fontconfig>
        '''

    def __del__(self):
        del self._conffile
        del self._fontdir
        del self._cachedir

    @property
    def builddir(self):
        return self._builddir

    @property
    def srcdir(self):
        return self._srcdir

    @property
    def fontdir(self):
        return self._fontdir

    @property
    def cachedir(self):
        return self._cachedir

    @property
    def extra(self):
        return self._extra

    @property
    def config(self):
        return self.__conf_templ.format(fontdir=self.fontdir.name,
                                        cachedir=self.cachedir.name,
                                        extra=self.extra)

    def setup(self):
        self._conffile.write(self.config)
        self._conffile.close()
        self._env['FONTCONFIG_FILE'] = self._conffile.name

    def install_font(self, files, dest):
        if not isinstance(files, list):
            files = [files]
        time = self._env.get('SOURCE_DATE_EPOCH', None)

        for f in files:
            fn = Path(f).name
            dname = Path(self.fontdir.name) / dest / fn
            shutil.copy2(f, dname)
            if time:
                os.utime(str(dname), (time, time))

        if time:
            os.utime(self.fontdir.name, (time, time))

    def run(self, binary, args) -> Iterator[[int, str, str]]:
        cmd = []
        if self._exewrapper:
            cmd += self._exewrapper
        cmd += [str(binary)]
        cmd += args
        res = subprocess.run(cmd, check=True, capture_output=True,
                             env=self._env)
        yield res.returncode, res.stdout.decode('utf-8'), res.stderr.decode('utf-8')

    def run_cache(self, args) -> Iterator[[int, str, str]]:
        return self.run(self._fccache, args)

    def run_cat(self, args) -> Iterator[[int, str, str]]:
        return self.run(self._fccat, args)

    def run_list(self, args) -> Iterator[[int, str, str]]:
        return self.run(self._fclist, args)

    def run_match(self, args) -> Iterator[[int, str, str]]:
        return self.run(self._fcmatch, args)

    def run_pattern(self, args) -> Iterator[[int, str, str]]:
        return self.run(self._fcpattern, args)

    def run_query(self, args) -> Iterator[[int, str, str]]:
        return self.run(self._fcquery, args)

    def run_scan(self, args) -> Iterator[[int, str, str]]:
        return self.run(self._fcscan, args)

    def run_validate(self, args) -> Iterator[[int, str, str]]:
        return self.run(self._fcvalidate, args)


if __name__ == '__main__':
    f = FcTest()
    print(f.fontdir.name)
    print(f.cachedir.name)
    print(f._conffile.name)
    print(f.config)
    f.setup()
