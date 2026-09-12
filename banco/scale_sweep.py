import glob, numpy as np, onnxruntime as ort
from PIL import Image
base='${KINELAB_BENCH_DIR:-./banco/}'
mean=np.array([123.675,116.28,103.53]); std=np.array([58.395,57.12,57.375])
def simcc_max(sx,sy):
    N,K,_=sx.shape
    xl=sx.reshape(N*K,-1).argmax(1); yl=sy.reshape(N*K,-1).argmax(1)
    vx=sx.reshape(N*K,-1).max(1); vy=sy.reshape(N*K,-1).max(1)
    return np.stack([xl,yl],-1).astype(np.float32).reshape(N,K,2)/2.0, np.minimum(vx,vy).reshape(N,K)
def infer(sess,name,pil,isz):
    a=(np.asarray(pil.resize(isz,Image.BILINEAR).convert('RGB')).astype(np.float32)-mean)/std
    o=sess.run(None,{name:a.transpose(2,0,1)[None].astype(np.float32)})
    k,s=simcc_max(o[0],o[1])
    return k[0]/np.array(isz), s[0]      # normalized 0..1 coords
def ang(a,b,c):
    v1=a-b; v2=c-b
    cs=(v1@v2)/(np.linalg.norm(v1)*np.linalg.norm(v2)+1e-9)
    return np.degrees(np.arccos(np.clip(cs,-1,1)))
im=Image.open(base+'frame.png').convert('RGB'); W,H=im.size
sessions={}
for key,isz in [('rtmpose-s',(192,256)),('rtmpose-m',(192,256)),('rtmpose-x',(288,384))]:
    p=[q for q in glob.glob(base+'models/**/end2end.onnx',recursive=True) if key in q][0]
    so=ort.SessionOptions(); so.log_severity_level=3
    s=ort.InferenceSession(p,so,providers=['CPUExecutionProvider'])
    sessions[key]=(s,s.get_inputs()[0].name,isz)
# 1) locate person on full frame with rtmpose-x
s,n,isz=sessions['rtmpose-x']
sw=int(H*isz[0]/isz[1]); left=(W-sw)//2
box=(left,0,left+sw,H)
k,sc=infer(s,n,im.crop(box),isz)
px=k*np.array([sw,H])+np.array([left,0])
good=sc>0.4
x0,y0=px[good].min(0); x1,y1=px[good].max(0)
bh=y1-y0
print(f"frame {W}x{H}; detected person bbox {x1-x0:.0f}x{bh:.0f}px -> body height = {100*bh/H:.1f}% of frame height; kpts conf>0.4: {good.sum()}/26")
# expand to a square-ish 3:4 crop with 25% padding
pad=0.25*bh; cx=(x0+x1)/2; cy=(y0+y1)/2; h=bh+2*pad; w=h*0.75
crop=im.crop((int(cx-w/2),int(cy-h/2),int(cx+w/2),int(cy+h/2)))
print(f"crop {crop.size}, person occupies ~{bh/crop.size[1]*100:.0f}% of crop height")
# 2) sweep: render crop at decreasing body pixel heights, then feed model
heights=[512,320,240,180,135,116,90,70,50,35]
for key in ['rtmpose-s','rtmpose-m','rtmpose-x']:
    s,n,isz=sessions[key]
    ref=None
    print(f"--- {key} (input {isz[0]}x{isz[1]}) ---")
    for bpx in heights:
        ch=int(bpx*crop.size[1]/bh); cw=max(8,int(ch*0.75))
        small=crop.resize((cw,ch),Image.LANCZOS)      # simulate the subject filming that small
        k,sc=infer(s,n,small,isz)
        # elbow angles (halpe26: 5 Lsho 6 Rsho 7 Lelb 8 Relb 9 Lwri 10 Rwri, 11 Lhip 12 Rhip)
        kp=k*np.array([1.0,1.0])
        le=ang(kp[5],kp[7],kp[9]); re=ang(kp[6],kp[8],kp[10])
        if ref is None: ref=(kp.copy(),le,re)
        d=np.linalg.norm((kp-ref[0]),axis=1)*bpx   # displacement expressed in body-height px
        print(f"  body_h={bpx:4d}px  mean_conf={sc.mean():.2f}  Lelbow={le:6.1f} (d={le-ref[1]:+6.1f})  Relbow={re:6.1f} (d={re-ref[2]:+6.1f})  kpt shift vs 512px ref: mean={d.mean():5.1f}px max={d.max():5.1f}px")
