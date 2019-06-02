#!/usr/bin/env python

import datetime, glob, math, os, unicodedata
from fontTools.ttLib import TTFont
from subprocess import run, DEVNULL

SRC = 'src'
DIST = 'dist'
FAMILY = 'Illusion'


# copy nohint, make hinted
def do_preprocess(src, nohint, hinted, ctrl):
    run(['cp', f'{SRC}/{src}', f'{DIST}/{nohint}'], stdout=DEVNULL)
    run(['ttfautohint',
         '--hinting-range-min=6',
         '--hinting-range-max=48',
         '--increase-x-height=0',
         '--x-height-snapping-exceptions=',
         '--fallback-stem-width=64',
         '--default-script=latn',
         '--fallback-script=none',
         '--stem-width-mode=qqq',
         '--windows-compatibility',
         f'--control-file={SRC}/{ctrl}',
         '--no-info',
        f'{DIST}/{nohint}',
        f'{DIST}/{hinted}',
    ], stdout=DEVNULL)


def do_build(opt):
    font = TTFont(opt['src'])
    glyph_map = {}
    fwid = font['GSUB'].table.LookupList.Lookup[0].SubTable[0].mapping
    hwid = font['GSUB'].table.LookupList.Lookup[1].SubTable[0].mapping
    for code, name in font.getBestCmap().items():
        pos = 0 if code < 0xF0000 else 1 if code < 0x100000 else 2
        code &= 0xFFFF
        if code not in glyph_map:
            glyph_map[code] = [ None, None, None, None, None, None ]
            # 0 : src half normal
            # 1 : src half italic
            # 2 : src full normal
        glyph_map[code][pos] = name
    for code, row in glyph_map.items():
        eaw = unicodedata.east_asian_width(chr(code))
        norm = row[0] or row[1]
        ital = row[1] or row[0]
        full = row[2]
        if norm and full:
            fwid[norm] = full
            hwid[full] = norm
        if eaw in ('H', 'Na') or 0xE000 <= code < 0xF900:
            row[:] = norm, ital, norm, ital, norm, ital
        elif eaw in ('F', 'W'):
            row[:] = full, full, full, full, full, full
        elif eaw == 'N':
            row[:] = norm, ital, norm, ital, full, full
        elif eaw == 'A':
            row[:] = norm, ital, full, full, full, full
    maps = [{code:row[x] for code, row in glyph_map.items() if row[x]}
            for x in range(6)]
    font['OS/2'].xAvgCharWidth = 1024
    font['OS/2'].panose.bProportion = 9
    font['OS/2'].ulCodePageRange1 |= 0x00020000
    font['OS/2'].ulCodePageRange1 ^= 0x00000004
    font['OS/2'].ulCodePageRange2 ^= 0x00020000
    font['OS/2'].ulUnicodeRange3 ^= 0x04C00000
    font['post'].isFixedPitch = 1
    del font['FFTM']
    del font['GPOS']
    for i in range(6):
        i_map = maps[i]
        i_opt = opt['font'][i]
        full_table = font['cmap'].getcmap(3, 10)
        full_cmap = full_table.cmap
        full_cmap.clear()
        base_table = font['cmap'].getcmap(3, 1)
        base_cmap = base_table.cmap
        base_cmap.clear()
        for code, name in i_map.items():
            full_cmap[code] = name
            if code <= 0xFFFF:
                base_cmap[code] = name
        font['head'].macStyle = i_opt['macStyle']
        font['post'].italicAngle = i_opt['italicAngle']
        font['OS/2'].fsSelection = i_opt['fsSelection']
        font['OS/2'].usWeightClass = i_opt['usWeightClass']
        font['OS/2'].panose.bWeight = i_opt['panoseWeight']
        font['OS/2'].panose.bLetterForm = i_opt['panoseLetterForm']
        for record in font['name'].names:
            if record.nameID in i_opt:
                record.string = i_opt[record.nameID]
        font.save(opt['ttf'][i])
    command = ['otf2otc', '-o', opt['dst']] + opt['ttf']
    run(command, stdout=DEVNULL)


def o(family_name, style):
    style_for_full = ('', ' Italic', ' Bold', ' BoldItalic')
    itan = - math.atan(0.1875) * 180 / math.pi
    full_name = f'{family_name}{style_for_full[style]}'
    build_date = datetime.date.today().isoformat()
    return {
        1: family_name,
        2: ('Regular', 'Italic', 'Bold', 'Bold Italic')[style],
        3: f'Google:{full_name}:{build_date}',
        4: full_name,
        6: full_name.replace(' ', '-'),
        'fsSelection':      (0x40, 0x01, 0x20, 0x21)[style],
        'italicAngle':      ( 0.0, itan,  0.0, itan)[style],
        'macStyle':         (   0,    2,    1,    3)[style],
        'panoseWeight':     (   6,    6,    8,    8)[style],
        'panoseLetterForm': (   4,   11,    4,   11)[style],
        'usWeightClass':    ( 400,  400,  700,  700)[style],
    }


def main():
    run(['mkdir', '-p', f'{DIST}/nohint'], stdout=DEVNULL)
    run(['mkdir', '-p', f'{DIST}/hinted'], stdout=DEVNULL)
    do_preprocess(
        f'{FAMILY}-Regular.ttf',
        f'{FAMILY}-Regular-nohint.ttf',
        f'{FAMILY}-Regular-hinted.ttf',
        f'{FAMILY}-Regular-ctrl.txt',
    )
    do_preprocess(
        f'{FAMILY}-Bold.ttf',
        f'{FAMILY}-Bold-nohint.ttf',
        f'{FAMILY}-Bold-hinted.ttf',
        f'{FAMILY}-Bold-ctrl.txt',
    )
    options = {
        'src':  f'{DIST}/{FAMILY}-Regular-nohint.ttf',
        'dst':  f'{DIST}/nohint/{FAMILY}-Regular.ttc',
        'ttf':  [f'{DIST}/i-{x}.ttf' for x in range(6)],
        'font': (
            o(f'{FAMILY} N', 0),
            o(f'{FAMILY} N', 1),
            o(f'{FAMILY} W', 0),
            o(f'{FAMILY} W', 1),
            o(f'{FAMILY} Z', 0),
            o(f'{FAMILY} Z', 1),
        ),
    }
    do_build(options)
    options.update({
        'src':  f'{DIST}/{FAMILY}-Regular-hinted.ttf',
        'dst':  f'{DIST}/hinted/{FAMILY}-Regular.ttc',
    })
    do_build(options)
    options = {
        'src':  f'{DIST}/{FAMILY}-Bold-nohint.ttf',
        'dst':  f'{DIST}/nohint/{FAMILY}-Bold.ttc',
        'ttf':  [f'{DIST}/i-{x}.ttf' for x in range(6)],
        'font': (
            o(f'{FAMILY} N', 2),
            o(f'{FAMILY} N', 3),
            o(f'{FAMILY} W', 2),
            o(f'{FAMILY} W', 3),
            o(f'{FAMILY} Z', 2),
            o(f'{FAMILY} Z', 3),
        ),
    }
    do_build(options)
    options.update({
        'src':  f'{DIST}/{FAMILY}-Bold-hinted.ttf',
        'dst':  f'{DIST}/hinted/{FAMILY}-Bold.ttc',
    })
    do_build(options)
    for x in glob.glob(f'{DIST}/*.ttf'):
        os.remove(x)


if __name__ == '__main__':
    main()

