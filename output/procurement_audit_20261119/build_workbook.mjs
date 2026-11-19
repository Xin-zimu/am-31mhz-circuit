import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const dir=path.dirname(fileURLToPath(import.meta.url));
const data=JSON.parse(await fs.readFile(path.join(dir,'audit_data.json'),'utf8'));
const wb=Workbook.create();
function col(i){let s='';for(i++;i;i=Math.floor((i-1)/26))s=String.fromCharCode(65+(i-1)%26)+s;return s;}
function make(name,title,note,headers,rows,widths){
 const s=wb.worksheets.add(name);s.showGridLines=false;
 const last=col(headers.length-1);s.getRange(`A1:${last}${rows.length+8}`).format.font={name:'Microsoft YaHei',size:10,color:'#172D41'};
 s.getRange('A2').values=[[title]];s.getRange('A2').format.font={size:15,bold:true,color:'#172D41'};
 s.getRange('A4').values=[[note]];s.getRange('A4').format.font={size:10,color:'#607486'};
 s.getRange(`A7:${last}7`).values=[headers];s.getRange(`A7:${last}7`).format={fill:'#173B55',font:{bold:true,color:'#FFFFFF'},rowHeight:32,verticalAlignment:'center'};
 if(rows.length)s.getRange(`A8:${last}${rows.length+7}`).values=rows;
 s.getRange(`A8:${last}${rows.length+7}`).format={rowHeight:45,wrapText:true,verticalAlignment:'center'};
 widths.forEach((w,i)=>s.getRange(`${col(i)}7:${col(i)}${rows.length+7}`).format.columnWidth=w);
 s.freezePanes.freezeRows(7);
 for(let i=0;i<rows.length;i++)if(i%2===1)s.getRange(`A${8+i}:${last}${8+i}`).format.fill='#F2F6F9';
 s.tables.add(`A7:${last}${rows.length+7}`,true,name.replace(/[^a-zA-Z0-9]/g,'')+'Table'+wb.worksheets.items.length);
 return s;
}
const rows=data.rows.map((g,i)=>[i+1,g.category,g.name,g.need,g.stock??null,g.cart,null,g.status,g.refs,g.note,g.source]);
const main=make('合并采购核对','一套发射机和一套接收机采购核对','明确补列2.4 pF；天线1改2。104用户确认足够。购物车未付款，不计在手。',['序号','类别','采购规格','整套需要','在手或确认','车内折算只数','车外数量缺口','处理结论','实际位号','说明','来源行号'],rows,[7,11,37,11,22,15,16,29,57,78,45]);
for(let i=0;i<rows.length;i++){
 const r=i+8;main.getRange(`G${r}`).formulas=[[`=IF(ISNUMBER(E${r}),MAX(D${r}-E${r}-F${r},0),IF(E${r}="足够（用户确认）",0,"待盘点"))`]];
}
main.getRange(`D8:G${rows.length+7}`).setNumberFormat('0');
main.getRange(`G8:G${rows.length+7}`).conditionalFormats.add('cellIs',{operator:'greaterThan',formula:0,format:{fill:'#FFF0DB',font:{bold:true,color:'#9C4500'}}});
main.getRange('A5').values=[['天线与SMA接口、1812贴片转接和耗材需核对；TX电池转5 V尚未定型，当前核对为5 V实验供电版。']];
const actions=new Map([
 [4,['可删或备用','当前图CVREF与去耦用10 µF；库存10 µF已覆盖。100 µF不是同一值。']],
 [5,['对照备用','390 kΩ为40倍对照；主方案装430 kΩ。']],
 [7,['可减为1份','1份5个足够；当前只缺幅度用20 kΩ，频率位可用已有100 kΩ。']],
 [8,['可删或备用','占空比10 kΩ已有5只。']],
 [15,['可删或测试备用','51 Ω不是接收机必焊电阻；测试源50 Ω内阻不额外重复焊。']],
 [16,['核对厂牌/脚序后保留','原BU5只、整机9只；新购50只量够，但不能自动认定同厂牌和RF性能。']],
 [19,['对照备用','68 pF是332加载电感对照搭配，不是392主用必需。']],
 [24,['夹具备用','953 Ω仅独立LC夹具用，未装到收发机主板。']],
 [25,['数量改为2份','用户确认两端各一根；商品31 MHz适用性、内置加载及SMA需核对。']],
 [26,['机械备用','成品鞭是否还需扶正拉线按安装决定，不恢复已取消的自制铜杆路线。']],
 [29,['可删','0.1%10 Ω共10只已覆盖RMRG和RSENSE；此1%包重复。']],
 [32,['保留；1片主用其余备用','SOIC-8逐脚直通核对；换反馈电阻不需要再换一块运放板。']],
 [34,['微调备用','不能用于2.4 pF的CK；CCW12已覆盖三处常规微调。']],
 [35,['对照备用','1812CS-332为对照，不是392主用必需。']],
 [37,['可删','与LHY-A重复；普通OPA197不要求散热焊盘。']]
]);
const cartRows=data.cart.map(r=>[r.id,r.name,r.spec,r.packs,...(actions.get(r.id)??['保留（未付款）',r.id===28?'共需3只，1份10只足够；图纸Vishay按当前CCW12替代实测。':r.id===30?'2只主用，车中5只含筛选/备用。':r.id===2?'2.2 kΩ实际用3只，1份100只足够。':r.note??'主方案或调试所需。'])]);
make('购物车逐项处理','现有37项购物车逐项处理','本表只核对记录，没有修改实际购物车；天线数量按用户确认改为两根。',['车内序号','商品','原选项/每份数量','原份数','建议处理','理由'],cartRows,[11,39,62,10,32,85]);
make('逐位号用料','两张完整原理图逐位号用料','TX 74条、RX 56条中，剔除天线/连接口后共125个电气元件；端点按图纸记录。',['端别','位号','原图值/型号','归并采购规格','节点'],data.details,[8,14,49,49,72]);
make('问题与版本','必须补列、版本更正与辅料','来源：今天元器件总表、TX R3与RX R1端点表、本轮用户确认。',['处理类别','项目','结论或动作','依据及限制'],data.issues,[19,34,81,107]);
const issue=wb.worksheets.getItem('问题与版本');
const sourcerow=data.issues.length+10;
issue.getRange(`A${sourcerow}`).values=[['厂家核实来源']];issue.getRange(`B${sourcerow}`).values=[['https://www.vishay.com/docs/85513/bat85s.pdf']];
main.tabColor='#173B55';
wb.recalculate();
// Verify formula behavior using the known, unambiguous CK shortage.
const ck=data.rows.findIndex(g=>g.name==='2.4 pF')+8;
console.log((await wb.inspect({kind:'table',range:`合并采购核对!A${ck}:H${ck}`,include:'values,formulas',tableMaxRows:2,tableMaxCols:8,maxChars:1500})).ndjson);
const range=main.getRange(`F${ck}`);const before=range.values;range.values=[[10]];wb.recalculate();
console.log('CK after adding 10 cart pieces:',main.getRange(`G${ck}`).values);range.values=before;wb.recalculate();
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!',options:{useRegex:true,maxResults:10},maxChars:1200})).ndjson);
await (await SpreadsheetFile.exportXlsx(wb)).save(path.join(dir,'收发机一次补购核对_20261119.xlsx'));
for(const [name,range] of [['合并采购核对','A1:H16'],['购物车逐项处理','A1:F12'],['逐位号用料','A1:E12'],['问题与版本','A1:D12']]){
 const b=await wb.render({sheetName:name,range,scale:1,format:'png'});await fs.writeFile(path.join(dir,`preview_${name}.png`),new Uint8Array(await b.arrayBuffer()));
}
console.log('saved workbook');
