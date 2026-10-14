from pathlib import Path
import sys, json
import numpy as np
from build_simulation import ROOT, run_spice, read_raw, metrics

DEST=ROOT/'system'; DEST.mkdir(exist_ok=True)

def system_net(freq=22000,duty=.5,amp=4,gain=15):
    period=1/freq
    return f'''31MHz AM SYSTEM FUNCTIONAL MODEL - not a transistor-level radio
* Signal generator, AM, channel and RX RF gain are ideal functional blocks.
* The Schottky model is an engineering approximation, NOT a BAS70 vendor model.
* No prediction of antenna distance, RF power, battery current or hardware compliance.
* RF:31MHz; baseband:{freq}Hz; duty:{duty}; V1pp:{amp}V.
VCC VCC 0 9
VREF VREF 0 4.5
VINPUT V1 0 PULSE(0 {amp} 10u 20n 20n {period*duty-20e-9:.12g} {period:.12g})
VCARRIER TP2 0 SIN(0 1 31meg)
* EAM = (0.6 + 0.1*V1)*carrier; continuous analog AM, carrier never switched off.
EAM TP3 0 POLY(2) (TP2,0) (V1,0) 0 0.6 0 0 0.1
EPA TP4 0 TP3 0 1
* Voltage attenuation 0.1 = -20dB, fixed hypothetical channel.
ECHANNEL ANT_RX 0 TP4 0 0.1
ERX TP5 0 ANT_RX 0 10
RRF TP5 RF_OUT 50
C110 RF_OUT DET_RF 220p
R117 DET_RF 0 1k
D101 DET_RF TP6 SCHOTTKY_EST
R110 TP6 0 10k
C111 TP6 0 47p
C115 TP6 BB_IN 10n
R113 BB_IN VREF 100k
* Linear baseband gain with a dominant-pole bandwidth of 18MHz/gain.
EBB AMP_IDEAL VREF BB_IN VREF {gain:.12g}
RBB AMP_IDEAL V2_OP 1k
CBB V2_OP 0 {gain/(2*np.pi*18e6*1000):.12g}
R116 V2_OP V2 100
RLOAD V2 0 1meg
.model SCHOTTKY_EST D(Is=20n N=1.06 Rs=2 Cjo=2p M=0.33 Vj=0.35 Bv=70 Ibv=10u)
.options plotwinsize=0 reltol=0.001
.save V(V1) V(TP2) V(TP3) V(TP5) V(TP6) V(V2)
.tran 2n 5m 4.8m 2n
.end
'''

def sim(freq,duty,amp):
    p=DEST/f'AM_{freq//1000}k_D{round(100*duty):02}_A{amp}V.cir'
    p.write_text(system_net(freq,duty,amp),encoding='ascii')
    run_spice(p); data=read_raw(p.with_suffix('.raw'))
    result={'frequency_set_hz':freq,'duty_set':duty,'v1_set_vpp':amp,
            'v1':metrics(data,'v(v1)',.00485),'v2':metrics(data,'v(v2)',.00485)}
    print(json.dumps(result),flush=True)
    return p,data,result

if __name__=='__main__':
    sim(22000,.5,4)
