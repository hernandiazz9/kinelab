import glob, numpy as np, onnxruntime as ort
from PIL import Image
base='${KINELAB_BENCH_DIR:-./banco/}'
im=Image.open(base+'frame.png').convert('RGB')
W,H=im.size
# letterbox to 3:4 (192x256) around full frame, like a loose bbox
side_h=H; side_w=int(H*192/256)
left=(W-side_w)//2
crop=im.crop((left,0,left+side_w,H)).resize((192,256),Image.BILINEAR)
arr=np.asarray(crop).astype(np.float32)
mean=np.array([123.675,116.28,103.53]); std=np.array([58.395,57.12,57.375])
arr=(arr-mean)/std
x=arr.transpose(2,0,1)[None].astype(np.float32)
def simcc_max(sx,sy):
    N,K,Wx=sx.shape
    xl=sx.reshape(N*K,-1).argmax(1); yl=sy.reshape(N*K,-1).argmax(1)
    vx=sx.reshape(N*K,-1).max(1); vy=sy.reshape(N*K,-1).max(1)
    loc=np.stack([xl,yl],-1).astype(np.float32); sc=np.minimum(vx,vy)
    loc[sc<=0.]=-1
    return loc.reshape(N,K,2)/2.0, sc.reshape(N,K)
for key in ['rtmpose-s','rtmpose-m','rtmpose-x']:
    p=[q for q in glob.glob(base+'models/**/end2end.onnx',recursive=True) if key in q][0]
    isz=(288,384) if 'rtmpose-x' in key else (192,256)
    if isz!=(192,256):
        c2=im.crop((left,0,left+side_w,H)).resize(isz,Image.BILINEAR)
        a2=(np.asarray(c2).astype(np.float32)-mean)/std
        xx=a2.transpose(2,0,1)[None].astype(np.float32)
    else: xx=x
    out={}
    for prov in ['CPUExecutionProvider','CoreMLExecutionProvider']:
        so=ort.SessionOptions(); so.log_severity_level=3
        s=ort.InferenceSession(p,so,providers=[prov]); n=s.get_inputs()[0].name
        o=s.run(None,{n:xx}); out[prov]=simcc_max(o[0],o[1])
    (kc,sc),(km,sm)=out['CPUExecutionProvider'],out['CoreMLExecutionProvider']
    d=np.linalg.norm(kc-km,axis=-1)[0]
    conf=sc[0]>0.3
    print(f"{key}: kpts={kc.shape[1]} conf>0.3 -> {conf.sum()}  |dkpt| in model-input px: mean={d.mean():.2f} max={d.max():.2f} | on confident kpts mean={d[conf].mean() if conf.any() else float('nan'):.2f} max={d[conf].max() if conf.any() else float('nan'):.2f}")
    print(f"   score mean CPU={sc[0].mean():.3f} CoreML={sm[0].mean():.3f}  max|dscore|={np.abs(sc-sm).max():.3f}")
