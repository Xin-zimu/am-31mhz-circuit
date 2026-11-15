"""Hole-addressed assembly and wire schedules, derived from physical_parts.json.
All long/crossing links are insulated point-to-point wires; crossings are NOT joints.
Mechanical fit is conditional on the explicitly stated package and adapter checks.
"""
from build_drawings import *

PLACEMENTS={
 'LC':{
  'CSEL':[(6,8),(7,8)], 'CK':[(10,7),(11,7)], 'COUT':[(15,8),(16,8)],
  'LSEL1':[(7,7),(4,5)], 'LSEL2':[(14,7),(16,4)],
  'CFIX1':[(8,8),(8,9)], 'CFIX2':[(12,8),(12,9)],
  'CT1':[(9,10),(9,12)], 'CT2':[(14,10),(14,12)],
  'RPORT':[(17,8),(17,11)],'JRF':[(3,8),(3,9)],
  'RMEAS':[(18,8),(18,11)],'CEXT':[(19,8),(19,9)],
 },
 'RF':{},
 'BB':{
  'RVT':[(4,3),(4,6)],'RVB':[(4,7),(4,10)],'CVREF':[(6,7),(6,9)],
  'CCOUP':[(6,12),(8,12)],'RBIAS':[(9,8),(9,11)],'RG':[(11,7),(11,10)],
  'RFB':[(17,5),(14,5)],'ROUT':[(19,8),(22,8)],
  'U1':{'1':(13,6),'2':(13,7),'3':(13,8),'4':(13,9),'5':(16,9),'6':(16,8),'7':(16,7),'8':(16,6)},
  'CDU1':[(17,7),(17,8)],'CPWR':[(4,1),(4,2)],
  'JPOWER':[(2,1),(2,2)],'JOUT':[(24,8),(24,9)]
 }
}
for i,x in [(1,7),(2,19)]:
    PLACEMENTS['RF'].update({f'Q{i}':{'1':(x,7),'2':(x+1,7),'3':(x+2,7)},
       f'RBT{i}':[(x+1,2),(x+1,5)],f'RBB{i}':[(x+3,9),(x+3,12)],
       f'RC{i}':[(x+3,2),(x+3,5)],f'REU{i}':[(x-1,7),(x-3,7)],
       f'REB{i}':[(x-3,8),(x-3,11)],f'CEB{i}':[(x-2,8),(x-2,9)],
       f'CDQ{i}':[(x+3,3),(x+4,3)]})
PLACEMENTS['RF'].update({
 'CIN1':[(5,6),(6,6)],'CIN2':[(13,7),(14,7)],
 'CBUF':[(25,7),(26,7)],'QBUF':{'1':(31,7),'2':(32,7),'3':(33,7)},
 'RBTB':[(31,2),(31,5)],'RBBB':[(32,9),(32,12)],'REBUF':[(30,9),(30,12)],
 'COBUF':[(31,10),(32,10)],'RRF':[(33,11),(33,14)],'RCONNECT':[(33,10),(34,10)],
 'DDET':{'2':(35,10),'1':(37,10)},'RDET':[(37,11),(37,14)],'CDET':[(38,11),(38,12)],
 'RFILT':[(39,10),(42,10)],'CFILT':[(42,11),(42,12)],'CDBUF':[(33,3),(34,3)]})

# Connector/test pads are board-side terminals, not additional circuit components.
PADS={
 'LC':{'PORT':('port',(16,8)),'GPORT':('0',(16,9))},
 'RF':{'PORT_IN':('port',(3,6)),'GPORT':('0',(3,5)), 'VCC':('vcc',(2,2)),'GND':('0',(2,3)),
       'BB_OUT':('out',(43,10)),'GOUT':('0',(43,11)), 'TP_C1':('c1',(11,6)), 'TP_C2':('c2',(23,6)),
       'TP_RF':('rf',(33,10)),'TP_DET':('det',(37,10))},
 'BB':{'DET_IN':('out',(4,12)),'GIN':('0',(4,13)),'TP_REF':('ref',(6,6)),
       'TP_BBIN':('bbin',(12,8)),'TP_BBO':('bbo',(18,8)),'RF_9V':('vcc',(2,4)),'RF_GND':('0',(2,5))}
}
CONFIG={'LC':(24,16,34,1700,1200),'RF':(44,17,28,2200,1200),'BB':(27,16,34,1850,1200)}
fixture_parts={
 'RMEAS':dict(ref='RMEAS',value='953 / REMOVE',pins={'1':'port','2':'0'},package='可拆测量夹具；1%电阻'),
 'CEXT':dict(ref='CEXT',value='TBD / REMOVE',pins={'1':'port','2':'0'},package='可拆C0G；数值按总14pF预算，待核实')}
original_refs=set(parts)
parts.update(fixture_parts)
def addr(p):return f'{chr(64+p[1])}{p[0]:02}'
def assignment(board):
    out={}
    for r,ps in PLACEMENTS[board].items():
        if isinstance(ps,dict):out[r]={str(k):tuple(v) for k,v in ps.items()}
        else:out[r]={'1':ps[0],'2':ps[1]}
    return out

allplacements={};wire_rows=[];pad_rows=[]
def make_board(board):
    cols,rows,step,w,h=CONFIG[board];assign=assignment(board);allplacements[board]=assign
    nets=defaultdict(set);ownership=defaultdict(set);owner_ref=defaultdict(list)
    for ref,ps in assign.items():
        for pin,pt in ps.items():
            net=parts[ref]['pins'][pin];owner_ref[pt].append(nref(ref)+'.'+pin)
            ownership[pt].add(net if net!='NC' else ref+'.'+pin)
            if net!='NC':nets[net].add(pt)
            pad_rows.append({'板':board,'图纸位号':nref(ref),'原位号':ref,'实际脚':pin,'孔坐标':addr(pt),'节点':net,'说明':parts[ref]['package']})
    for label,(net,pt) in PADS[board].items():
        ownership[pt].add(net);owner_ref[pt].append(label);nets[net].add(pt)
        pad_rows.append({'板':board,'图纸位号':label,'原位号':'接口/测试焊点','实际脚':'焊点','孔坐标':addr(pt),'节点':net,'说明':'RF点不装长针；端点为元件侧坐标'})
    conflicts={addr(p):list(n) for p,n in ownership.items() if len(n)>1}
    assert not conflicts,(board,conflicts)
    # Explicit ground mesh on the RF board: two narrow copper rows and four
    # joining columns. No existing signal pad lies on these copper strips.
    ground_links=[]
    if board=='RF':
        def onbus(pt):return (pt[1] in (4,13) and 2<=pt[0]<=44) or (pt[0] in (2,15,27,44) and 4<=pt[1]<=13)
        assert all(ns=={'0'} for pt,ns in ownership.items() if onbus(pt)), 'Signal pad on ground copper'
        taps={(x,y) for x in (2,15,27,44) for y in (4,13)}
        for pt in list(nets['0']):
            options=[(pt[0],4),(pt[0],13)]
            if 4<=pt[1]<=13:options += [(x,pt[1]) for x in (2,15,27,44)]
            tap=min(options,key=lambda v:math.dist(pt,v));taps.add(tap)
            if tap!=pt:ground_links.append((pt,tap,False))
        for y in (4,13):
            line=sorted(p for p in taps if p[1]==y)
            ground_links += [(a,b,True) for a,b in zip(line,line[1:])]
        for x in (2,15,27,44):
            line=sorted((p for p in taps if p[0]==x and 4<=p[1]<=13),key=lambda p:p[1])
            ground_links += [(a,b,True) for a,b in zip(line,line[1:])]
        for i,pt in enumerate(sorted(taps),1):
            ownership[pt].add('0');nets['0'].add(pt)
            name=f'GB{i:02}';PADS[board][name]=('0',pt)
            pad_rows.append({'板':board,'图纸位号':name,'原位号':'地铜带接点','实际脚':'焊点','孔坐标':addr(pt),'节点':'0','说明':'RF背面D/M行及2/15/27/44列(D至M)为地铜带，跨过的其他跳线须绝缘'})
    links=[]
    copper_ids=set()
    def add_link(n,a,b,copper=False):
        idx=f'{board}-W{len(links)+1:03}';links.append((idx,n,a,b))
        if copper:copper_ids.add(idx)
        wire_rows.append({'线号':idx,'板':board,'节点':n,'端A':addr(a),'端B':addr(b),'直线跨度mm':round(math.dist(a,b)*2.54,2),'工艺':'指定地铜带段；覆盖孔均为GND；其余跨线需绝缘' if copper else '绝缘短线，仅两端焊接；跨线/跨孔不相连。地支线短接到最近铜带。'})
    for n,ps in sorted(nets.items()):
        if n=='0' and board=='RF':
            for a,b,copper in ground_links:add_link(n,a,b,copper)
            continue
        done=[sorted(ps)[0]];rest=set(ps)-set(done)
        while rest:
            _,a,b=min((math.dist(a,b),a,b) for a in done for b in rest)
            add_link(n,a,b);done.append(b);rest.remove(b)
    # All wire endpoint connectivity is represented explicitly and checked later.
    for side in ['top','bottom']:
        name={'LC':'03','RF':'05','BB':'07'}[board] if side=='top' else {'LC':'04','RF':'06','BB':'08'}[board]
        title=f'{board} 独立孔洞洞板 / '+('元件面与孔位' if side=='top' else '焊接面镜像与跳线')
        sc=Scene(name+'_'+board+'_'+side,w,h,title,'放大示意，非1:1钻孔模板。2.54 mm孔距；坐标以元件面为准，焊接面已左右镜像；孔与孔默认绝缘。')
        ox,oy=85,210
        def xy(p):return (ox+((p[0]-1) if side=='top' else (cols-p[0]))*step,oy+(p[1]-1)*step)
        sc.rect(ox-24,oy-24,(cols-1)*step+48,(rows-1)*step+48,'#f8f2df','#b7a985')
        if board=='RF':
            for a,b in [((2,4),(44,4)),((2,13),(44,13))]+[((x,4),(x,13)) for x in (2,15,27,44)]:
                sc.path([xy(a),xy(b)],'#b8c3c4',11 if side=='bottom' else 6,'4,3' if side=='top' else '')
        for c in range(1,cols+1):
            x,_=xy((c,1));sc.text(x,oy-36,str(c),12,anchor='middle',native=False)
        for r in range(1,rows+1):
            _,y=xy((1,r));sc.text(ox-40,y+4,chr(64+r),13,native=False)
            for c in range(1,cols+1):
                x,_=xy((c,r));sc.circle(x,y,3,'#a2a3a1')
        if side=='bottom':
            palette=['#267db5','#a648a5','#bc7624','#168c80','#704fc4','#526f25','#bd3f65']
            colors={n:('#b63531' if n=='vcc' else '#34414b' if n=='0' else palette[i%len(palette)]) for i,n in enumerate(sorted(nets))}
            for idx,n,a,b in links:
                ax,ay=xy(a);bx,by=xy(b)
                # White casing makes projected wire crossings visually non-connecting.
                sc.path([(ax,ay),(bx,by)],'#fff',6)
                sc.path([(ax,ay),(bx,by)],colors[n],5 if idx in copper_ids else 2.8)
                sc.text((ax+bx)/2+4,(ay+by)/2-5,idx.split('W')[1],9,colors[n],native=False)
            for p,ns in ownership.items():
                x,y=xy(p);sc.circle(x,y,5,'#fff');sc.circle(x,y,2.5,'#252d31')
        else:
            for i,(ref,ps) in enumerate(assign.items(),1):
                coords=[xy(pt) for pt in ps.values()];xs=[v[0] for v in coords];ys=[v[1] for v in coords]
                if len(coords)>2:
                    sc.rect(min(xs)-12,min(ys)-13,max(xs)-min(xs)+24,max(ys)-min(ys)+26,'#e9edf2','#253c50')
                else:
                    sc.path(coords,'#243f54',6)
                    if ref.startswith('CT'):sc.rect(min(xs)-step,min(ys)-9,step*2,max(ys)-min(ys)+18,'none','#9b6326')
                    if ref.startswith('LSEL'):sc.path(coords,'#8c4ca5',13)
                for pin,pt in ps.items():
                    x,y=xy(pt);sc.circle(x,y,5,'#fff');sc.circle(x,y,2.5,'#233844');sc.text(x+6,y+12,pin,10,native=False)
                mx,my=(sum(xs)/len(xs),sum(ys)/len(ys));sc.text(mx,my-14,f'{i:02}',13,'#183b62',anchor='middle',native=False)
        for label,(n,pt) in PADS[board].items():
            if label.startswith('GB'):continue
            x,y=xy(pt);sc.circle(x,y,6,'#fff');sc.circle(x,y,3,'#a33630');sc.text(x+8,y-8,label,10,'#99372f',native=False)
        lx=ox+(cols-1)*step+95;ly=170
        sc.text(lx,ly,'位号索引 / 端点见逐脚孔位表',19,native=False)
        for i,(ref,ps) in enumerate(assign.items(),1):
            yy=ly+28+i*20
            sc.text(lx,yy,f'{i:02}  {nref(ref):10} {parts[ref]["value"]}',12,native=False)
        notes={
          'LC':[
           'LSEL1/LSEL2粗线只表示安装区和引出落点，不是实际外形。',
           '132-17L两脚约7.37×3.96 mm；不是2.54 mm整网格。',
           '按手册用短引线落到图示焊盘，或核实后增开孔。',
           '不要强拉线圈来凑孔；线圈本体尺寸约9.65×5.84 mm。',
           'CT1/CT2脚距5.08 mm；S为图纸1，R为图纸2接地。',
           '微调端子孔约Ø1.2；板孔/端子/视角到货核实后再扩孔。',
           '固定pF电容与CK优先置焊接面；短接、留清洁绝缘间隙。',
           '可拆953Ω/CEXT夹具紧贴PORT；实际CEXT和探头待核实。',
           '两线圈初始轴向近似正交；无保证互感k的几何尺寸。',
           'LC与RF板相邻：PORT到CIN1用最短接线，接入后重核加载。'],
          'RF':[
           'Q1/Q2/QBUF：1=E、2=B、3=C；依实际onsemi封装核实。',
           '2.54 mm落点是短引脚成形方案；不得以图猜其他厂牌脚序。',
           '小RF电容可装焊接面；电阻按小型轴向件预留。',
           'RCONNECT1为短连线；DDET1的1脚K/色环在J37。',
           'CDQ1/CDQ2/CDBUF1是本地100n电源旁路。',
           '背面D/M行、2/15/27/44列(D至M)铺约1.2mm窄地铜带。',
           '这些铜带覆盖孔均接地；其他所有跨带信号线保持绝缘。',
           '地回流应贴着对应信号通路；输入与c2/输出不要并行靠近。',
           'TP_C1/TP_C2只保留小焊点；探头加载另行评估。',
           'TP_RF在COBUF之后；禁止套用旧6.81 dB一阶估算修正。',
           '本图是未实测布线起点；寄生、振荡和器件资格尚待核实。'],
          'BB':[
           'U1为SOIC-8装到逐脚直通DIP-8转接板；缺口朝A行。',
           'U1左列自上而下1/2/3/4；右列自上而下8/7/6/5。',
           '1/5/8悬空；4接地；7接9 V；SOIC本体不是DIP器件。',
           'CDU1必须优先焊在转接板SOIC 7/4脚附近。',
           '图示CDU1外部孔为接口落点，不能替代芯片脚边去耦。',
           'RFB1：U1.6→210k→U1.2；反馈不能取ROUT1之后。',
           'CVREF1正端ref、负端GND；CPWR1正端9 V、负端GND。',
           'ref是3 V偏置，不能与GND桥接。CCOUP1是无极性100n。',
           '具体转接板是否保持同号脚、焊盘间距和NC须逐脚测通断。']
        }[board]
        ny=max(oy+rows*step+55,750)
        for i,t in enumerate(notes):sc.text(65,ny+i*23,t,15,'#923c31' if i<2 else '#293c48',native=False)
        sc.text(65,130,'元件体上的数字对应右侧索引；所有孔名以元件面A行/1列定义。',16,native=False)
        sc.text(65,157,'指定灰色铜带为GND；其他跳线仅在线端焊接，跨线处必须保留绝缘。' if board=='RF' else '跳线图仅在线端圆点焊接；跨线处即使相交也不相连，必须保留绝缘。',16,'#a33d36',native=False)
        # LC has 10 notes; its taller lower note area needs a slightly taller page.
        if ny+len(notes)*23>h-45:
            sc.h=ny+len(notes)*23+65
        sc.save(native=False)
    return nets,links

if __name__=='__main__':
    data={}
    for b in CONFIG:
        nets,links=make_board(b);data[b]={'placements':allplacements[b],'pads':PADS[b],'nets':{n:sorted(ps) for n,ps in nets.items()},'links':links}
    assert set(r for a in allplacements.values() for r in a)==set(parts),set(parts)-set(r for a in allplacements.values() for r in a)
    table('逐脚洞洞板孔位表.csv',pad_rows);table('逐根跳线表.csv',wire_rows)
    dump(OUT/'qa/perfboard_graph.json',data)
    dump(OUT/'qa/fixture_parts.json',fixture_parts)
    print('boards',len(data),'pin/pad rows',len(pad_rows),'wire rows',len(wire_rows))
