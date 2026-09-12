import glob, time, numpy as np, onnxruntime as ort
base='${KINELAB_BENCH_DIR:-./banco/}models/'
ms={k:[p for p in glob.glob(base+'**/end2end.onnx',recursive=True) if k in p][0] for k in ['rtmpose-s','rtmpose-m','rtmpose-x','rtmw-dw-x-l']}
def sess(m,prov,threads=None):
    so=ort.SessionOptions(); so.log_severity_level=3
    if threads: so.intra_op_num_threads=threads
    return ort.InferenceSession(m,so,providers=[prov])
# 1) 1-thread CPU baseline (comparable with the published i7-11700 numbers)
for k in ['rtmpose-s','rtmpose-m']:
    s=sess(ms[k],'CPUExecutionProvider',1); i=s.get_inputs()[0]
    sh=[1 if not isinstance(d,int) or d<=0 else d for d in i.shape]
    x=(np.random.rand(*sh)*255).astype(np.float32)
    for _ in range(5): s.run(None,{i.name:x})
    t=[]
    for _ in range(30):
        a=time.perf_counter(); s.run(None,{i.name:x}); t.append((time.perf_counter()-a)*1000)
    print(f"{k} CPU 1-thread mean={np.mean(t):.2f}ms")
# 2) numerical agreement CPU vs CoreML, and run-to-run determinism
for k in ['rtmpose-s','rtmpose-m']:
    i0=sess(ms[k],'CPUExecutionProvider').get_inputs()[0]
    sh=[1 if not isinstance(d,int) or d<=0 else d for d in i0.shape]
    x=(np.random.rand(*sh)*255).astype(np.float32)
    a=sess(ms[k],'CPUExecutionProvider'); b=sess(ms[k],'CoreMLExecutionProvider')
    oa=a.run(None,{i0.name:x}); ob=b.run(None,{i0.name:x}); ob2=b.run(None,{i0.name:x})
    for j,(u,v) in enumerate(zip(oa,ob)):
        u=np.asarray(u,dtype=np.float64); v=np.asarray(v,dtype=np.float64)
        # simcc argmax = the decoded keypoint bin
        am_u=u.argmax(-1); am_v=v.argmax(-1)
        print(f"{k} out{j} shape={u.shape} maxabsdiff={np.abs(u-v).max():.4g} argmax_bins_differ={(am_u!=am_v).sum()}/{am_u.size} max_bin_shift={np.abs(am_u-am_v).max()}")
    print(f"{k} CoreML run-to-run identical: {all(np.array_equal(p,q) for p,q in zip(ob,ob2))}")
