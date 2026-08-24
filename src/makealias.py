#!/usr/bin/env python3

import os
import re
import sys
import argparse
from collections import OrderedDict

# cat fontconfig/fontconfig.h | grep '^Fc[^ ]* *(' | sed -e 's/ *(.*$//'

def extract(fname, excluded = ['FcCacheDir', 'FcCacheSubdir']):
    with open(fname, 'r', encoding='utf-8') as f:
        for l in f.readlines():
            l = l.rstrip()
            m = re.match(r'^(Fc[^ ]*)[\s\w]*\(.*', l)

            if m and m.group(1) not in excluded:
                yield m.group(1)

def make_export_file(input_headers, output_file):
    with open(output_file, 'w') as export_file:
        names = []
        for header in input_headers:
            names.extend([name for name in extract(header, excluded = [])])

        print(*sorted(set(names)), sep='\n', file=export_file) # set to remove potential duplicates

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--make-export-file', required=False, action='store_true')
    parser.add_argument('srcdir')
    parser.add_argument('head')
    parser.add_argument('tail')
    parser.add_argument('headers', nargs='+')

    args = parser.parse_args()

    definitions = {}

    for fname in os.listdir(args.srcdir):
        define_name, ext = os.path.splitext(fname)
        if ext != '.c':
            continue

        define_name = '__%s__' % os.path.basename(define_name)

        for definition in extract(os.path.join(args.srcdir, fname)):
            definitions[definition] = define_name

    if args.make_export_file:
        make_export_file([args.tail, *args.headers], args.head)
        sys.exit(0)

    declarations = OrderedDict()

    for fname in args.headers:
        for declaration in extract(fname):
            try:
                define_name = definitions[declaration]
            except KeyError:
                print ('error: could not locate %s in src/*.c' % declaration)
                sys.exit(1)

            declarations[declaration] = define_name

    with open(args.head, 'w') as head:
        with open(args.tail, 'w') as tail:
            tail.write('#if HAVE_GNUC_ATTRIBUTE\n')
            last = None
            for name, define_name in declarations.items():
                alias = 'IA__%s' % name
                hattr = 'FC_ATTRIBUTE_VISIBILITY_HIDDEN'
                head.write('extern __typeof (%s) %s %s;\n' % (name, alias, hattr))
                head.write('#define %s %s\n' % (name, alias))
                if define_name != last:
                    if last is not None:
                        tail.write('#endif /* %s */\n' % last)
                    tail.write('#ifdef %s\n' % define_name)
                    last = define_name
                tail.write('# undef %s\n' % name)
                cattr = '__attribute((alias("%s"))) FC_ATTRIBUTE_VISIBILITY_EXPORT' % alias
                tail.write('extern __typeof (%s) %s %s;\n' % (name, name, cattr))
            tail.write('#endif /* %s */\n' % last)
            tail.write('#endif /* HAVE_GNUC_ATTRIBUTE */\n')
