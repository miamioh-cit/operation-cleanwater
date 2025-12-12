const $=(id)=>document.getElementById(id);
const cellSelect=$("cellSelect"),clockEl=$("clock"),gwUpdated=$("gwUpdated"),errorsBox=$("errorsBox");
function makeRing(n=60){return{arr:Array(n).fill(null),i:0,push(v){this.arr[this.i]=v;this.i=(this.i+1)%this.arr.length;}}}
const trendFlow=makeRing(60),trendPress=makeRing(60);
function clearCanvas(ctx){ctx.clearRect(0,0,ctx.canvas.width,ctx.canvas.height);}
function drawText(ctx,text,x,y,size=12,color="#9aa7b7",align="center"){ctx.save();ctx.fillStyle=color;ctx.font=`${size}px ui-sans-serif, system-ui`;ctx.textAlign=align;ctx.fillText(text,x,y);ctx.restore();}
function drawGauge(canvasId,value,min,max,label,unit){const c=$(canvasId),ctx=c.getContext("2d");clearCanvas(ctx);const w=c.width,h=c.height,cx=w/2,cy=h*0.95,r=Math.min(w,h)*0.75;
ctx.lineWidth=12;ctx.strokeStyle="#1a1f27";ctx.beginPath();ctx.arc(cx,cy,r,Math.PI,0,false);ctx.stroke();
const t=Math.max(0,Math.min(1,(value-min)/(max-min||1)));ctx.strokeStyle="#f1c40f";ctx.shadowColor="rgba(241,196,15,.35)";ctx.shadowBlur=10;
ctx.beginPath();ctx.arc(cx,cy,r,Math.PI,Math.PI+t*Math.PI,false);ctx.stroke();ctx.shadowBlur=0;
ctx.lineWidth=2;ctx.strokeStyle="#2b3240";
for(let i=0;i<=10;i++){const a=Math.PI+(i/10)*Math.PI;const x1=cx+Math.cos(a)*(r-18),y1=cy+Math.sin(a)*(r-18),x2=cx+Math.cos(a)*(r-4),y2=cy+Math.sin(a)*(r-4);
ctx.beginPath();ctx.moveTo(x1,y1);ctx.lineTo(x2,y2);ctx.stroke();}
drawText(ctx,`${label}`,cx,16,11,"#9aa7b7");drawText(ctx,`${min}`,18,h-6,10,"#9aa7b7","left");drawText(ctx,`${max}`,w-18,h-6,10,"#9aa7b7","right");if(unit)drawText(ctx,unit,cx,h-6,10,"#9aa7b7");}
function drawTrend(canvasId,ring,min,max){const c=$(canvasId),ctx=c.getContext("2d");clearCanvas(ctx);const w=c.width,h=c.height;
ctx.strokeStyle="#1a1f27";ctx.lineWidth=1;for(let i=0;i<=4;i++){const y=(i/4)*h;ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}
const vals=ring.arr.slice(ring.i).concat(ring.arr.slice(0,ring.i)).filter(v=>v!==null);if(vals.length<2)return;
ctx.strokeStyle="#f1c40f";ctx.shadowColor="rgba(241,196,15,.35)";ctx.shadowBlur=10;ctx.lineWidth=2;ctx.beginPath();
vals.forEach((v,idx)=>{const t=vals.length===1?0:idx/(vals.length-1);const x=t*w;const yy=h-((v-min)/(max-min||1))*h;const y=Math.max(0,Math.min(h,yy));if(idx===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);});
ctx.stroke();ctx.shadowBlur=0;}
function setDot(id,mode){const el=$(id);el.classList.remove("good","warn");if(mode==="good")el.classList.add("good");else if(mode==="warn")el.classList.add("warn");}
function fmtTemp(x10){if(x10===null||x10===undefined)return"--";return`${(x10/10).toFixed(1)} C`;}
function fmtNum(n){if(n===null||n===undefined)return"--";return`${n}`;}
function initCells(){for(let i=1;i<=10;i++){const id=`cell${String(i).padStart(2,"0")}`;const opt=document.createElement("option");opt.value=id;opt.textContent=id.toUpperCase();cellSelect.appendChild(opt);}cellSelect.value="cell01";}
function updateClock(){clockEl.textContent=new Date().toLocaleString();}setInterval(updateClock,1000);updateClock();
async function fetchCell(cellId){const res=await fetch(`/api/cells/${cellId}`);if(!res.ok)throw new Error(`HTTP ${res.status}`);return await res.json();}
function render(cell){const p1=(cell.pumps&&cell.pumps.pump1)?cell.pumps.pump1:{run:false,speed:0,temp_c_x10:0,kpa:0};
const p2=(cell.pumps&&cell.pumps.pump2)?cell.pumps.pump2:{run:false,speed:0,temp_c_x10:0,kpa:0};
const pr=cell.process||{flow_rate:0,pressure_in:0,pressure_out:0,dirty_filters:false,control_valves:true};
const hasErrors=(cell.errors&&cell.errors.length>0);
setDot("st-conn",hasErrors?"warn":"good");setDot("st-p1",p1.run?"good":"");setDot("st-p2",p2.run?"good":"");setDot("st-flow",pr.flow_rate>0?"good":"");setDot("st-filters",pr.dirty_filters?"warn":"good");setDot("st-valves",pr.control_valves?"good":"warn");
errorsBox.textContent=hasErrors?`Errors: ${JSON.stringify(cell.errors)}`:"";
$("p1-temp").textContent=fmtTemp(p1.temp_c_x10);$("p1-kpa").textContent=fmtNum(p1.kpa);$("p2-temp").textContent=fmtTemp(p2.temp_c_x10);$("p2-kpa").textContent=fmtNum(p2.kpa);
$("p1-speed").textContent=fmtNum(p1.speed);$("p2-speed").textContent=fmtNum(p2.speed);
$("flow").textContent=fmtNum(pr.flow_rate);$("pin").textContent=fmtNum(pr.pressure_in);$("pout").textContent=fmtNum(pr.pressure_out);
drawGauge("g1",p1.speed,0,100,"Speed","%");drawGauge("g2",p2.speed,0,100,"Speed","%");drawGauge("gFlow",pr.flow_rate,0,50,"Flow","");drawGauge("gPin",pr.pressure_in,0,4000,"kPa In","kPa");drawGauge("gPout",pr.pressure_out,0,5000,"kPa Out","kPa");
trendFlow.push(pr.flow_rate);trendPress.push(pr.pressure_out);drawTrend("cFlow",trendFlow,0,50);drawTrend("cPress",trendPress,0,5000);}
async function loop(){const cellId=cellSelect.value;try{const data=await fetchCell(cellId);render(data);gwUpdated.textContent=new Date().toLocaleTimeString();}catch(e){setDot("st-conn","warn");errorsBox.textContent=`Gateway error: ${e}`;}}
cellSelect.addEventListener("change",()=>{trendFlow.arr.fill(null);trendFlow.i=0;trendPress.arr.fill(null);trendPress.i=0;loop();});
initCells();loop();setInterval(loop,1000);
