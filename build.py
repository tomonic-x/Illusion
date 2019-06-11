#!/usr/bin/env python

import datetime, glob, math, os, unicodedata, sys
from tqdm import tqdm
from fontTools.ttLib import TTFont
from subprocess import run, DEVNULL
import argparse

SRC = 'src'
DIST = 'dist'
FAMILY = 'Illusion'
PBAR = None

class ValidateException(Exception):
    pass

def PBAR_desc(task, path=""):
    if path and len(path):
        PBAR.set_description(f'{task:8s}: {os.path.basename(path):27s}')

def do_validate(regular, bold):
    errmsg = []
    font_r = TTFont(f'{SRC}/{regular}')
    font_b = TTFont(f'{SRC}/{bold}')
    cmap_r = font_r.getBestCmap()
    cmap_b = font_b.getBestCmap()
    mask_h = ~1024
    mask_f = ~2048
    for font, cmap, src in ((font_r, cmap_r, regular), (font_b, cmap_b, bold)):
        PBAR_desc('validate', src)
        for code, name in cmap.items():
            if code < 0x100000 and font['hmtx'][name][0] & mask_h:
                errmsg.append(f'U+{code:04X}: not hwid ({font["hmtx"][name][0]}) at {src}')
            elif 0x100000 <= code and font['hmtx'][name][0] & mask_f:
                errmsg.append(f'U+{code:04X}: not fwid ({font["hmtx"][name][0]}) at {src}')
        if errmsg:
            raise ValidateException("\n".join(['Invalid advance width'] + errmsg))
        for code, name in cmap.items():
            if code < 0x10000 and 0xF0000 + code not in cmap and not ((0x2500 <= code < 0x25A0) or (0xE000 <= code < 0xF900) or font['glyf'][name].numberOfContours == 0):
                errmsg.append(f'U+{code:04X}: no italic at {src}')
            elif (0xF0000 <= code < 0x100000) and code & 0xFFFF not in cmap:
                errmsg.append(f'U+{code:04X}: no normal at {src}')
            elif 0x100000 <= code and code & 0xFFFF not in cmap:
                errmsg.append(f'U+{code:04X}: no hwid at {src}')
            elif 0x10000 <= code < 0xF0000:
                errmsg.append(f'U+{code:04X}: mistakes code {src}')
        if errmsg:
            raise ValidateException("\n".join(['Code point validation error'] + errmsg))
        PBAR.update(1)
    PBAR_desc('compare', 'Regular / Bold')
    for code, name in cmap_r.items():
        if code not in cmap_b:
            errmsg.append(f'U+{code:04X}: not in bold')
    for code, name in cmap_b.items():
        if code not in cmap_r:
            errmsg.append(f'U+{code:04X}: not in regular')
    if errmsg:
        raise ValidateException("\n".join(['Comparison error'] + errmsg))
    PBAR.update(1)


# copy nohint, make hinted
def do_preprocess(src):
    nohint = f'{src}-nohint.ttf'
    hinted = f'{src}-hinted.ttf'
    ctrl = f'{src}-ctrl.txt'
    PBAR_desc('hinting', hinted)
    run(['cp', f'{SRC}/{src}.ttf', f'{DIST}/{nohint}'], stdout=DEVNULL)
    run(['ttfautohint',
         '--hinting-range-min=10',
         '--hinting-range-max=32',
         '--increase-x-height=0',
         '--x-height-snapping-exceptions=',
         '--fallback-stem-width=64',
         '--default-script=latn',
         '--fallback-script=none',
         '--stem-width-mode=nnn',
         '--windows-compatibility',
         f'--control-file={SRC}/{ctrl}',
         '--no-info',
        f'{SRC}/{src}.ttf',
        f'{DIST}/{hinted}',
    ], stdout=DEVNULL)
    PBAR.update(1)
    PBAR_desc('dehint', hinted)
    font = TTFont(f'{DIST}/{hinted}')
    cmap = font.getBestCmap()
    glyf = font['glyf']
    for x in range(0x2500, 0x25A0):
        glyf[cmap[x]].removeHinting()
    for x in range(0x102500, 0x1025A0):
        glyf[cmap[x]].removeHinting()
    font.save(f'{DIST}/{hinted}')
    PBAR.update(1)


def do_build(opt):
    PBAR_desc('prepare', opt['dst'])
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
        if eaw in ('H', 'Na'):
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
    PBAR.update(1)
    for i in range(6):
        PBAR_desc('generate', f'{i}.ttf')
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
        PBAR.update(1)
    PBAR_desc('otf2otc', opt['dst'])
    command = ['otf2otc', '-o', opt['dst']] + opt['ttf']
    run(command, stdout=DEVNULL)
    PBAR.update(1)


def out_webfont(src, files):
    for num, head in files.items():
        PBAR_desc('convert', f'{head}.ttf')
        run(['pyftsubset',
            f'{DIST}/hinted/{src}',
            f'--font-number={num}',
            f'--output-file={DIST}/{head}.ttf',
            '--unicodes=*',
            '--layout-features=*',
            '--notdef-glyph',
            '--notdef-outline',
            '--recommended-glyphs',
            ], stdout=DEVNULL)
        PBAR.update(1)
        PBAR_desc('convert', f'{head}.woff')
        run(['pyftsubset',
            f'{DIST}/{head}.ttf',
            f'--font-number={num}',
            '--flavor=woff',
            '--with-zopfli',
            f'--output-file={DIST}/{head}.woff',
            '--unicodes=*',
            '--layout-features=*',
            '--notdef-glyph',
            '--notdef-outline',
            '--recommended-glyphs',
            ], stdout=DEVNULL)
        PBAR.update(1)
        PBAR_desc('convert', f'{head}.woff2')
        run(['pyftsubset',
            f'{DIST}/{head}.ttf',
            f'--font-number={num}',
            '--flavor=woff2',
            f'--output-file={DIST}/{head}.woff2',
            '--unicodes=*',
            '--layout-features=*',
            '--notdef-glyph',
            '--notdef-outline',
            '--recommended-glyphs',
            ], stdout=DEVNULL)
        PBAR.update(1)


def o(family_name, style):
    style_full = ('', ' Italic', ' Bold', ' Bold Italic')
    style_ps = ('Regular', 'Italic', 'Bold', 'BoldItalic')
    itan = - math.atan(0.1875) * 180 / math.pi
    full_name = f'{family_name}{style_full[style]}'
    ps_name = f'{family_name.replace(" ", "-")}-{style_ps[style]}'
    build_date = datetime.date.today().isoformat()
    return {
        1: family_name,
        2: ('Regular', 'Italic', 'Bold', 'Bold Italic')[style],
        3: f'Google:{full_name}:{build_date}',
        4: full_name,
        6: ps_name,
        'fsSelection':      (0x40, 0x01, 0x20, 0x21)[style],
        'italicAngle':      ( 0.0, itan,  0.0, itan)[style],
        'macStyle':         (   0,    2,    1,    3)[style],
        'panoseWeight':     (   6,    6,    8,    8)[style],
        'panoseLetterForm': (   4,   11,    4,   11)[style],
        'usWeightClass':    ( 400,  400,  700,  700)[style],
    }


def main():
    global PBAR, args
    parser = argparse.ArgumentParser()
    parser.add_argument('--release', action='store_true', help='Build webfont')
    args = parser.parse_args()
    total = 75 if args.release else 39
    PBAR = tqdm(total=total, leave=False, bar_format="{desc} {percentage:3.0f}%|{bar}|{n_fmt}/{total_fmt}")
    try:
        do_validate(
            f'{FAMILY}-Regular.ttf',
            f'{FAMILY}-Bold.ttf',
        )
        run(['mkdir', '-p', f'{DIST}/nohint'], stdout=DEVNULL)
        run(['mkdir', '-p', f'{DIST}/hinted'], stdout=DEVNULL)
        run(['mkdir', '-p', f'{DIST}/webfont'], stdout=DEVNULL)
        do_preprocess(f'{FAMILY}-Regular')
        do_preprocess(f'{FAMILY}-Bold')
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
        if args.release:
            out_webfont(f'{FAMILY}-Regular.ttc', {
                0: f'webfont/{FAMILY}-N-Regular',
                1: f'webfont/{FAMILY}-N-Italic',
                2: f'webfont/{FAMILY}-W-Regular',
                3: f'webfont/{FAMILY}-W-Italic',
                4: f'webfont/{FAMILY}-Z-Regular',
                5: f'webfont/{FAMILY}-Z-Italic',
            })
            out_webfont(f'{FAMILY}-Bold.ttc', {
                0: f'webfont/{FAMILY}-N-Bold',
                1: f'webfont/{FAMILY}-N-BoldItalic',
                2: f'webfont/{FAMILY}-W-Bold',
                3: f'webfont/{FAMILY}-W-BoldItalic',
                4: f'webfont/{FAMILY}-Z-Bold',
                5: f'webfont/{FAMILY}-Z-BoldItalic',
            })
        for x in glob.glob(f'{DIST}/*.ttf'):
            os.remove(x)
    except ValidateException:
        PBAR.close()
        print(sys.exc_info()[1])
    else:
        PBAR.close()


if __name__ == '__main__':
    main()

