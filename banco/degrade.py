import glob, numpy as np, onnxruntime as ort
from PIL import Image, ImageFilter
base='${KINELAB_BENCH_DIR:-./banco/}'
mean=np.array([123.675,116.28,103.53]); std=np.array([58.395,57.12,57.375])
def simcc_max(sx,sy):
    N,K,_=sx.shape
    xl=sx.reshape(N*K,-1).argmax(1); yl=sy.reshape(N*K,-1).argmax(1)
    vx=sx.reshape(N*K,-1).max(1); vy=sy.reshape(N*K,-1).max(1)
    return np.stack([xl,yl],-1).astype(np.float32).reshape(N,K,2)/2.0, np.minimum(vx,vy).reshape(N,K)
def infer(S,pil):
    s,n,isz=S
    a=(np.asarray(pil.resize(isz,Image.BILINEAR).convert('RGB')).astype(np.float32)-mean)/std
    o=s.run(None,{n:a.transpose(2,0,1)[None].astype(np.float32)})
    k,sc=simcc_max(o[0],o[1]); return k[0]/np.array(isz), sc[0]
def ang(a,b,c):
    v1=a-b; v2=c-b
    return np.degrees(np.arccos(np.clip((v1@v2)/(np.linalg.norm(v1)*np.linalg.norm(v2)+1e-9),-1,1)))
def mkblur(pil,k,vert=False):
    a=np.asarray(pil).astype(np.float32); out=np.zeros_like(a)
    for i in range(k):
        sh=i-k//2
        out+= np.roll(a, sh, axis=0 if vert else 1)
    return Image.fromarray((out/k).astype(np.uint8))
im=Image.open(base+'frame.png').convert('RGB'); W,H=im.size
S={}
for key,isz in [('rtmpose-s',(192,256)),('rtmpose-m',(192,256))]:
    p=[q for q in glob.glob(base+'models/**/end2end.onnx',recursive=True) if key in q][0]
    so=ort.SessionOptions(); so.log_severity_level=3
    ss=ort.InferenceSession(p,so,providers=['CPUExecutionProvider']); S[key]=(ss,ss.get_inputs()[0].name,isz)
# person bbox from earlier run
k,sc=infer(S['rtmpose-m'], im.crop(((W-int(H*0.75))//2,0,(W-int(H*0.75))//2+int(H*0.75),H)))
sw=int(H*0.75); left=(W-sw)//2
px=k*np.array([sw,H])+np.array([left,0]); g=sc>0.4
x0,y0=px[g].min(0); x1,y1=px[g].max(0); bh=y1-y0; cx=(x0+x1)/2; cy=(y0+y1)/2
def cropbox(pad=0.25,dx=0.0,dy=0.0,scale=1.0):
    h=(bh+2*pad*bh)*scale; w=h*0.75
    return im.crop((int(cx-w/2+dx*bh),int(cy-h/2+dy*bh),int(cx+w/2+dx*bh),int(cy+h/2+dy*bh)))
for key in S:
    ref=cropbox(); kr,scr=infer(S[key],ref); L0=ang(kr[5],kr[7],kr[9]); R0=ang(kr[6],kr[8],kr[10])
    print(f"=== {key}  ref Lelbow={L0:.1f} Relbow={R0:.1f} (body {bh:.0f}px) ===")
    for label,img in [('blur h 5px',mkblur(ref,5)),('blur h 11px',mkblur(ref,11)),('blur h 21px',mkblur(ref,21)),
                      ('blur v 11px',mkblur(ref,11,vert=True)),('gauss r=3',ref.filter(ImageFilter.GaussianBlur(3)))]:
        k2,s2=infer(S[key],img); L=ang(k2[5],k2[7],k2[9]); R=ang(k2[6],k2[8],k2[10])
        d=np.linalg.norm(k2-kr,axis=1)*bh
        print(f"  {label:14s} conf={s2.mean():.2f} Lelbow={L:6.1f} ({L-L0:+6.1f})  Relbow={R:6.1f} ({R-R0:+6.1f})  kptshift mean={d.mean():4.1f}px max={d.max():5.1f}px")
    for label,img in [('bbox dx=+0.15',cropbox(dx=0.15)),('bbox dy=-0.15',cropbox(dy=-0.15)),
                      ('bbox tight 0.0 pad',cropbox(pad=0.0)),('bbox scale 0.7 (truncated)',cropbox(scale=0.7)),
                      ('bbox scale 2.0 (loose)',cropbox(scale=2.0))]:
        k2,s2=infer(S[key],img); L=ang(k2[5],k2[7],k2[9]); R=ang(k2[6],k2[8],k2[10])
        print(f"  {label:26s} conf={s2.mean():.2f} Lelbow={L:6.1f} ({L-L0:+6.1f})  Relbow={R:6.1f} ({R-R0:+6.1f})")
