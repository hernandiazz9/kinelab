import glob, numpy as np, onnxruntime as ort
base='${KINELAB_BENCH_DIR:-./banco/}models/'
p=[q for q in glob.glob(base+'**/end2end.onnx',recursive=True) if 'rtmpose-s' in q][0]
def S(prov,**kw):
    so=ort.SessionOptions(); so.log_severity_level=3
    return ort.InferenceSession(p,so,providers=[prov],**kw)
i=S('CPUExecutionProvider').get_inputs()[0]
sh=[1,3,256,192]
for name,x in [('raw0-255',(np.random.rand(*sh)*255).astype(np.float32)),
               ('imagenet-norm',((np.random.rand(*sh)*255-123.675)/58.4).astype(np.float32))]:
    a=S('CPUExecutionProvider').run(None,{i.name:x})
    b=S('CoreMLExecutionProvider'); o1=b.run(None,{i.name:x}); o2=b.run(None,{i.name:x})
    for j in range(len(a)):
        u=a[j]; v=o1[j]
        print(f"[{name}] out{j}: CPU nan={np.isnan(u).sum()} min/max={u.min():.3g}/{u.max():.3g} | CoreML nan={np.isnan(v).sum()} inf={np.isinf(v).sum()} min/max={np.nanmin(v):.3g}/{np.nanmax(v):.3g}")
        m=~(np.isnan(u)|np.isnan(v))
        if m.any(): print(f"   finite maxabsdiff={np.abs(u[m]-v[m]).max():.4g}  argmax CPU={u.argmax(-1).ravel()[:6]} CoreML={np.nan_to_num(v,nan=-1e9).argmax(-1).ravel()[:6]}")
    print(f"[{name}] CoreML determinism run1==run2: {all(np.array_equal(x1,x2) for x1,x2 in zip(o1,o2))}")
