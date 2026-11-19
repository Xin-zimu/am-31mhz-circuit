"""What-if: a 27 MHz loaded whip (1.3 m) retracted to <=1 m — where does it resonate?

NOT a measurement and NOT a model of the actual product. The product's internal
loading coil is unknown; this inverts the problem: size a coil that resonates a
1.3 m whip at 27 MHz, then ask what the same coil does at shorter extension.
"""
import json, math
import nec_support as nec

ROOT = __import__('pathlib').Path(__file__).resolve().parent
nec.EXE = ROOT.parent / 'stage_am_alt3_1_20261116/tools/nec2c.exe'
W = 2*math.pi*31e6


def cards(length, f_MHz, n=60, radius=.0015, sigma=1.4e6, soil=(13, .005)):
    h = .83
    c = [nec.gw(1, n, (0, 0, h), (0, 0, h+length), radius)]
    for k in range(8):
        a = 2*math.pi*k/8
        c.append(nec.gw(k+2, round(n*.5/length), (0, 0, h), (.5*math.cos(a), .5*math.sin(a), h)))
    c += ['GE 0']
    if soil: c += ['GN 2 0 0 0 %g %g' % soil]
    c += ['LD 5 1 0 0 %g' % sigma]
    for tag in range(2, 10): c += ['LD 5 %d 0 0 5.8e7' % tag]
    c += ['FR 0 1 0 0 %g' % f_MHz, 'EX 0 1 1 0 1 0', 'RP 0 19 73 1000 0 0 5 5']
    return c


def macro(d):
    """Series R-Lant-Cant fit from three nearby frequencies (same method as model_whip)."""
    f = d['f_MHz']*1e6
    lo = nec.solve(f'{d["name"]}_lo', cards(d['length_m'], d['f_MHz']-.1))
    hi = nec.solve(f'{d["name"]}_hi', cards(d['length_m'], d['f_MHz']+.1))
    w = 2*math.pi*f
    slope = (hi['X']-lo['X'])/(2*math.pi*.2e6)
    la = (slope + d['X']/w)/2
    ca = 1/(w*(w*la - d['X']))
    return dict(R=d['R'], Lant=la, Cant=ca, X=d['X'])


def main():
    # Step 1: the 1.3 m element at 27 MHz (full extension of the 27 MHz product).
    full = nec.solve('whip13_27', cards(1.3, 27))
    full.update(length_m=1.3, f_MHz=27, name='whip13_27')
    m13 = macro(full)
    f27 = 27e6
    # Series resonance at 27 MHz with full extension: L_coil = 1/(w^2 C) - L_ant
    L_coil = 1/((2*math.pi*f27)**2 * m13['Cant']) - m13['Lant']
    print('1.3m @27MHz: R=%.2f Lant=%.4fuH Cant=%.3fpF  -> implied internal coil L=%.3fuH'
          % (m13['R'], m13['Lant']*1e6, m13['Cant']*1e12, L_coil*1e6), flush=True)

    # Step 2: retract to the four study lengths, same coil, ask for f_res.
    ants = json.loads((ROOT/'antenna_nominal.json').read_text(encoding='utf-8'))
    print()
    print('retracted  Lant_uH  Cant_pF   f_res_MHz   X_at_31MHz_ohm')
    for d in ants:
        Lt = d['Lant_H'] + L_coil
        Ct = d['Cant_F']
        fr = 1/(2*math.pi*math.sqrt(Lt*Ct))
        w = W
        X31 = w*Lt - 1/(w*Ct)
        print('%6d cm  %8.4f %8.3f %11.2f %14.1f'
              % (round(d['length_m']*100), d['Lant_H']*1e6, d['Cant_F']*1e12, fr/1e6, X31), flush=True)

    out = dict(note='Screening estimate only; the real product internal coil is unknown.',
               full_1p3m_27MHz=dict(R=m13['R'], Lant_H=m13['Lant'], Cant_F=m13['Cant'],
                                    implied_coil_H=L_coil),
               rows=[dict(length_cm=round(d['length_m']*100),
                          f_res_Hz=1/(2*math.pi*math.sqrt((d['Lant_H']+L_coil)*d['Cant_F'])),
                          X31_ohm=W*(d['Lant_H']+L_coil) - 1/(W*d['Cant_F']))
                     for d in ants])
    (ROOT/'whatif_27MHz_loaded_whip.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
    print('written whatif_27MHz_loaded_whip.json')


if __name__ == '__main__':
    main()
